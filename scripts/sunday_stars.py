#!/usr/bin/env python3
"""FantasyGameday Sunday Stars scoring and payout model.

Rules source: data/fantasygameday/rules_sunday_stars.md (app rules valid from
1 Aug 2025). Run as a script to print payout breakdowns for the recorded 2025
contests and refresh the payout columns in contests_sunday_stars_2025.csv.
"""
import csv
import math
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "fantasygameday"
CONTESTS_CSV = DATA_DIR / "contests_sunday_stars_2025.csv"

RAKE = 0.20

SCORING = {
    "pass_yd": 0.04,
    "pass_td": 4,
    "interception": -2,
    "rush_yd": 0.1,
    "rush_td": 6,
    "reception": 1,
    "rec_yd": 0.1,
    "rec_td": 6,
    "fumble_lost": -2,
    "two_pt": 2,
    "fumble_rec_td": 6,
}

# (min_entries, tiers) — each tier is (share_of_pool, fraction_of_field);
# fraction None marks the first-place tier. Fields below 15 have no published
# structure.
PAYOUT_BANDS = [
    (1201, [(0.04, None), (0.16, 0.01), (0.13, 0.01), (0.20, 0.02), (0.22, 0.05), (0.25, 0.10)]),
    (701, [(0.05, None), (0.30, 0.02), (0.20, 0.02), (0.20, 0.05), (0.25, 0.10)]),
    (301, [(0.075, None), (0.275, 0.02), (0.15, 0.02), (0.50, 0.15)]),
    (101, [(0.15, None), (0.35, 0.04), (0.50, 0.15)]),
    (15, [(0.25, None), (0.25, 0.04), (0.50, 0.15)]),
]


def score(stats, captain=False):
    """Fantasy points for a stat line dict keyed like SCORING. Captains double."""
    pts = sum(SCORING[k] * v for k, v in stats.items())
    return pts * 2 if captain else pts


def payouts(entries, fee):
    """Per-tier payouts: list of (players_in_tier, gbp_each). Tier sizes round UP
    (the completed 2025 week-1 contest paid 7 players in the 15% tier from 43
    entries: ceil(6.45)), and everyone in a tier shares its pool equally
    regardless of order within the tier (2nd and 3rd both won £107.50 there)."""
    if entries < 15:
        raise ValueError("no published payout structure below 15 entries")
    pool = entries * fee * (1 - RAKE)
    tiers = next(t for floor, t in PAYOUT_BANDS if entries >= floor)
    out = []
    for share, frac in tiers:
        # round(..., 9) guards float noise like 250*0.04 = 10.000000000000002
        n = 1 if frac is None else math.ceil(round(entries * frac, 9))
        if n > 0:
            out.append((n, round(pool * share / n, 2)))
    return out


def _self_check():
    # in-app worked example: 250 entries at £10
    assert payouts(250, 10) == [(1, 300.0), (10, 70.0), (38, 26.32)], payouts(250, 10)
    # observed payouts from the completed 2025 week-1 leaderboard (43 x £25)
    assert payouts(43, 25) == [(1, 215.0), (2, 107.5), (7, 61.43)], payouts(43, 25)


def main():
    _self_check()
    rows = list(csv.DictReader(open(CONTESTS_CSV)))
    fields = [
        "season", "week", "entries", "entry_fee_gbp", "prize_pool_gbp",
        "first_prize_gbp", "tier2_n", "tier2_each_gbp", "tier3_n", "tier3_each_gbp",
        "places_paid",
    ]
    print(f"{'wk':>3} {'entries':>7} {'pool':>7} {'1st':>7} {'tier2':>10} {'tier3':>11} {'paid':>5}")
    for row in rows:
        n, fee = int(row["entries"]), int(row["entry_fee_gbp"])
        tiers = payouts(n, fee)
        (t1n, t1), (t2n, t2), (t3n, t3) = (tiers + [(0, 0.0)] * 3)[:3]
        row.pop("places_paid_est", None)
        row.update(
            prize_pool_gbp=round(n * fee * (1 - RAKE), 2),
            first_prize_gbp=t1,
            tier2_n=t2n, tier2_each_gbp=t2,
            tier3_n=t3n, tier3_each_gbp=t3,
            places_paid=t1n + t2n + t3n,
        )
        print(f"{row['week']:>3} {n:>7} {row['prize_pool_gbp']:>7} {t1:>7} "
              f"{t2n:>2} x {t2:>5} {t3n:>2} x {t3:>6} {row['places_paid']:>5}")
    with open(CONTESTS_CSV, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"updated {CONTESTS_CSV.name}")


if __name__ == "__main__":
    main()
