#!/usr/bin/env python3
"""Fetch FantasyGameday.app weekly player-price exports and build one combined CSV.

FantasyGameday (UK NFL daily fantasy app) publishes its weekly salary sheet in two
places, both public:
  - historical uploads in the site's WordPress media library
    (wp-content/uploads/<yyyy>/<mm>/FG_*.csv)
  - the current week only, overwritten in place at
    wp-content/uploads/custom-data/site-data.csv

This script downloads every known historical export, snapshots the current-week
file (named by its Last-Modified date, so repeated runs archive each new week
instead of overwriting), and rebuilds data/fantasygameday/salaries_combined.csv.

Usage:
    python scripts/fetch_fgd_salaries.py             # fetch everything, then rebuild
    python scripts/fetch_fgd_salaries.py --no-fetch  # rebuild from files already on disk
"""
import argparse
import csv
import datetime as dt
import email.utils
import io
import re
import sys
from pathlib import Path

import requests

BASE = "https://fantasygameday.app/wp-content/uploads"
CURRENT_URL = f"{BASE}/custom-data/site-data.csv"
MEDIA_API = "https://fantasygameday.app/wp-json/wp/v2/media?per_page=100&_fields=date,source_url,mime_type"

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "fantasygameday"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOT_DIR = RAW_DIR / "current"
COMBINED_CSV = DATA_DIR / "salaries_combined.csv"

# Known historical exports: (wp path, season, week_num, week_label).
# week_num extends past the regular season: 19=wildcard 20=divisional
# 21=championship 22=superbowl.
KNOWN_FILES = [
    ("2024/10/FG_week6_exportin.csv", 2024, 6, "week6"),
    ("2024/10/FG_week7_exportin.csv", 2024, 7, "week7"),
    ("2024/10/FG_week8_exportin.csv", 2024, 8, "week8"),
    ("2024/10/FG_week9_exportin.csv", 2024, 9, "week9"),
    ("2024/11/FG_week10_exportin.csv", 2024, 10, "week10"),
    ("2024/11/FG_week11_exportin.csv", 2024, 11, "week11"),
    ("2024/11/FG_week12_exportin.csv", 2024, 12, "week12"),
    ("2024/11/FG_week13_exportin.csv", 2024, 13, "week13"),
    ("2024/12/FG_week14_exportin.csv", 2024, 14, "week14"),
    ("2024/12/FG_week15_exportin.csv", 2024, 15, "week15"),
    ("2024/12/FG_week16_exportin.csv", 2024, 16, "week16"),
    ("2024/12/FG_week17_exportin.csv", 2024, 17, "week17"),
    ("2025/01/FG_week18_exportin.csv", 2024, 18, "week18"),
    ("2025/01/FG_wildcard_exportin.csv", 2024, 19, "wildcard"),
    ("2025/01/FG_divisional_exportin.csv", 2024, 20, "divisional"),
    ("2025/01/FG_championship_exportin.csv", 2024, 21, "championship"),
    ("2025/02/FG_superbowl_exportin.csv", 2024, 22, "superbowl"),
    ("2025/09/FG_week1_2025_export.xlsx", 2025, 1, "week1"),
    ("2025/09/FG_week2_2025_exportSheet1-1.csv", 2025, 2, "week2"),
    # week3 was uploaded twice; the later "-1" upload is a trimmed player pool
    # (522 rows vs 912) and is treated as canonical. The full pool is still
    # downloaded to raw/ for reference but excluded from the combined build.
    ("2025/09/FG_week3_2025_exportSheet1.csv", None, None, None),
    ("2025/09/FG_week3_2025_exportSheet1-1.csv", 2025, 3, "week3"),
]

# The playoff exports are cumulative 541-row sheets: only rows whose Game value
# is one of that round's matchups were in the live contest pool; the rest carry
# stale matchups (and possibly stale salaries) from earlier weeks.
PLAYOFF_SLATES = {
    "FG_wildcard_exportin.csv": {"LAC@HOU", "PIT@BAL", "DEN@BUF", "GB@PHI", "WAS@TB", "MIN@LA"},
    "FG_divisional_exportin.csv": {"HOU@KC", "WAS@DET", "LA@PHI", "BAL@BUF"},
    "FG_championship_exportin.csv": {"WAS@PHI", "BUF@KC"},
    "FG_superbowl_exportin.csv": {"KC@PHI"},
}

# FGD's team codes drifted between seasons (JAC->JAX, LA->LAR, WSH/WAS).
# Normalize to nflverse-style codes so seasons join cleanly.
TEAM_FIX = {"JAC": "JAX", "LA": "LAR", "WSH": "WAS"}

# Thursday kickoff of week 1, used to map a current-week snapshot date to an
# NFL week. Snapshots appear from the Saturday before kickoff.
SEASON_WEEK1 = {2026: dt.date(2026, 9, 10)}


def fetch_known(session):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for path, *_ in KNOWN_FILES:
        dest = RAW_DIR / Path(path).name
        if dest.exists():
            continue
        r = session.get(f"{BASE}/{path}", timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"fetched {dest.name} ({len(r.content)} bytes)")


def discover_new_media(session):
    """Warn if the media library holds data files this script doesn't know about."""
    try:
        items = session.get(MEDIA_API, timeout=30).json()
    except Exception as exc:  # pragma: no cover - purely informational
        print(f"media discovery skipped: {exc}")
        return
    known = {Path(p).name for p, *_ in KNOWN_FILES}
    for item in items:
        url = item.get("source_url", "")
        mime = item.get("mime_type", "")
        if ("csv" in mime or "spreadsheet" in mime) and Path(url).name not in known:
            print(f"NEW media file not in KNOWN_FILES: {url}")


def snapshot_current(session):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    r = session.get(CURRENT_URL, timeout=30)
    r.raise_for_status()
    modified = r.headers.get("Last-Modified")
    stamp = (
        email.utils.parsedate_to_datetime(modified).date().isoformat()
        if modified
        else dt.date.today().isoformat()
    )
    dest = SNAPSHOT_DIR / f"site-data_{stamp}.csv"
    if dest.exists() and dest.read_bytes() == r.content:
        print(f"snapshot unchanged ({dest.name})")
        return
    dest.write_bytes(r.content)
    print(f"snapshot saved {dest.name} ({len(r.content)} bytes)")


def snapshot_week(snap_date):
    """Map a snapshot date to (season, week_num). Snapshots go up from the
    Saturday before each week's Thursday kickoff."""
    for season, week1_thu in sorted(SEASON_WEEK1.items(), reverse=True):
        window_start = week1_thu - dt.timedelta(days=5)
        if snap_date >= window_start:
            return season, (snap_date - window_start).days // 7 + 1
    return None, None


def read_rows(path):
    if path.suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
        except ImportError:
            print(f"skipping {path.name}: pip install openpyxl to include xlsx exports")
            return None
        sheet = load_workbook(path, read_only=True).active
        data = [[("" if c is None else str(c)) for c in row] for row in sheet.iter_rows(values_only=True)]
        text = io.StringIO()
        csv.writer(text).writerows(data)
        text.seek(0)
        return list(csv.DictReader(text))
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def normalize(raw_row):
    row = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in raw_row.items() if k}
    team_raw = row.get("team", "")
    return {
        "position": row.get("position", ""),
        "first_name": row.get("first_name", ""),
        "last_name": row.get("last_name", ""),
        "team": TEAM_FIX.get(team_raw, team_raw),
        "team_raw": team_raw,
        "salary": row.get("salary", ""),
        "game": row.get("game", ""),
    }


def build_combined():
    out = []

    def add_file(path, season, week_num, week_label):
        rows = read_rows(path)
        if rows is None:
            return
        slate = PLAYOFF_SLATES.get(path.name)
        for raw_row in rows:
            row = normalize(raw_row)
            if not row["position"]:
                continue
            row.update(
                season=season,
                week_num=week_num,
                week_label=week_label,
                in_slate=1 if slate is None or row["game"] in slate else 0,
                source_file=path.name,
            )
            out.append(row)

    for path, season, week_num, week_label in KNOWN_FILES:
        if season is None:
            continue
        full = RAW_DIR / Path(path).name
        if full.exists():
            add_file(full, season, week_num, week_label)

    for snap in sorted(SNAPSHOT_DIR.glob("site-data_*.csv")):
        snap_date = dt.date.fromisoformat(re.search(r"(\d{4}-\d{2}-\d{2})", snap.name).group(1))
        season, week_num = snapshot_week(snap_date)
        if season is None:
            print(f"skipping {snap.name}: date not covered by SEASON_WEEK1")
            continue
        add_file(snap, season, week_num, f"week{week_num}")

    out.sort(key=lambda r: (r["season"], r["week_num"], -int(r["salary"] or 0), r["last_name"]))
    fields = [
        "season", "week_num", "week_label", "position", "first_name", "last_name",
        "team", "team_raw", "salary", "game", "in_slate", "source_file",
    ]
    COMBINED_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(COMBINED_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)
    weeks = len({(r["season"], r["week_num"]) for r in out})
    print(f"wrote {COMBINED_CSV.relative_to(REPO_ROOT)}: {len(out)} rows across {weeks} slates")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-fetch", action="store_true", help="rebuild combined CSV without downloading")
    args = parser.parse_args()
    if not args.no_fetch:
        session = requests.Session()
        session.headers["User-Agent"] = "fantasy-scraper/fgd-salaries (personal analysis)"
        fetch_known(session)
        snapshot_current(session)
        discover_new_media(session)
    build_combined()
    return 0


if __name__ == "__main__":
    sys.exit(main())
