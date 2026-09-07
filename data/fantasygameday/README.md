# FantasyGameday player-price data

Weekly player salary sheets from [FantasyGameday.app](https://fantasygameday.app/) (UK NFL
daily fantasy app), collected from the site's public downloads. Refresh with:

```shell
python3 scripts/fetch_fgd_salaries.py         # download + rebuild combined CSV
python3 scripts/fetch_fgd_salaries.py --no-fetch   # rebuild only
```

Run it once a week during the season: the current-week export lives at a single URL that
is overwritten every week (`wp-content/uploads/custom-data/site-data.csv`), so each run
saves a dated snapshot under `raw/current/` before it disappears.

## What's here

| Season | Slates | Source | Notes |
|--------|--------|--------|-------|
| 2024 | weeks 6–18 + wildcard, divisional, championship, superbowl | WordPress media library (`FG_*_exportin.csv`) | weeks 1–5 were never posted |
| 2025 | weeks 1–3 | media library (`FG_week*_2025_export*`) | week 1 is xlsx; weeks 4+ were only ever at the overwritten site-data.csv URL |
| 2026 | week 1 onward | dated snapshots of `site-data.csv` | run the script weekly to keep collecting |

`salaries_combined.csv` merges everything, one row per player per slate:

`season, week_num, week_label, position, first_name, last_name, team, team_raw, salary, game, weekday, gameday, in_slate, source_file`

`week_num` runs 1–18 for the regular season, then 19=wildcard, 20=divisional,
21=championship, 22=superbowl. `weekday`/`gameday` come from the
[nflverse](https://github.com/nflverse/nfldata) schedule (cached in
`raw/nfl_games_2024plus.csv`) and tell you when that player's team plays that week —
empty means no game (bye week, or an eliminated team's stale row in a playoff file).
**Sunday Stars contests cover Sunday games only**, so filter `weekday == "Sunday"`
for that contest's player pool.

## Gotchas when analysing

- **Playoff files are cumulative.** Each playoff export still contains all 541 players;
  only rows whose `Game` matches that round's matchups were in the live pool. Filter on
  `in_slate = 1` (wildcard 293, divisional 177, championship 98, superbowl 54). Salaries
  on `in_slate = 0` rows may be stale carry-overs from earlier weeks.
- **Team codes drifted** across seasons (`JAC`→`JAX`, `LA`→`LAR`, `WSH`→`WAS`). The
  `team` column is normalized to nflverse-style codes; `team_raw` keeps the original.
- **Salary scales differ by season** (2024 tops out ~8,200; 2025 reached 9,200; 2026
  week 1 tops at 8,000). Compare prices within a season, or as share of budget.
- **Early 2024 exports are partial**: week 6 covers only 21 teams, growing to the full
  32 by week 13. That's how they were published, not a collection error.
- **2025 week 3 was uploaded twice**: a 912-row full pool and a later 522-row trimmed
  pool. The trimmed upload is treated as canonical in the combined file; both sit in
  `raw/`.
- **Monday games are largely excluded from current-week exports**: the 2026 week 1
  file has zero Broncos and only two stray Chiefs rows (DEN@KC is Monday night), while
  Wednesday/Thursday teams are included. Treat the export as the Wed-Sun pool.

## Contest history

`contests_sunday_stars_2025.csv` — entry counts for the £25 Sunday Stars contest
(Sunday-only slates), 2025 season, reported from the app by the league owner (the app is
the only source; there is no public contest API). The 14 counts were reported as
"week 1–15", so one week may be missing — treated as weeks 1–14 until confirmed. The
payout columns (`first_prize_gbp`, tier sizes/amounts, `places_paid`) are computed by
`scripts/sunday_stars.py` from the official tier table in `rules_sunday_stars.md`
(20% rake, 25%/25%/50% tiers for 15–100 entries, tier sizes rounded half-up per the
app's own worked example). The model is verified against the completed
2025 week-1 contest (see below): tier sizes round up, and everyone within a tier
shares its pool equally regardless of order.

`leaderboards/sunday_stars_2025_w01.csv` — the full final leaderboard of the 2025
week-1 £25 Sunday Stars (43 entries, 29 distinct players), transcribed from an in-app
screen recording: rank, username, prize, score. Rank 16 is a genuine tie (both shown
16th, rank 17 skipped); the 43rd score was cut off in the recording.

## Missing weeks and how to recover them

2024 weeks 1–5 were never published. 2025 weeks 4–18 and playoffs existed only at the
overwritten `site-data.csv` URL; if the Wayback Machine captured any, they can be pulled
from
[web.archive.org snapshots of that URL](https://web.archive.org/web/2025*/https://fantasygameday.app/wp-content/uploads/custom-data/site-data.csv)
(archive.org is unreachable from some networks — check from a normal browser). Save any
recovered file as `raw/current/site-data_YYYY-MM-DD.csv` using the snapshot date and add
that season's week-1 Thursday to `SEASON_WEEK1` in the script; the rebuild picks it up.
