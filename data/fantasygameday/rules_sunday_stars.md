# Sunday Stars — game rules

Source: "How to Play Sunday Stars" from the FantasyGameday app, rules valid from
1 August 2025, transcribed by the league owner on 2026-09-07. The app notes rules can
change without notice; per-contest specifics live behind the 'i' symbol in the lobby.

## Lineup (8 players, within the game budget)

- 1 Captain — **non-QB only, earns 2x points**
- 1 QB
- 2 RB
- 2 WR
- 1 TE
- 1 FLEX (RB/WR/TE)

Each player once per lineup. Unlimited changes until the deadline. Max 5 entries per
game; incomplete lineups are not accepted or charged.

## Scoring (full PPR)

| Stat | Points |
|------|--------|
| Passing yards | 0.04/yd (25 yds = 1) |
| Passing TD | 4 |
| Interception thrown | -2 |
| Rushing yards | 0.1/yd |
| Rushing TD | 6 |
| Reception | 1 |
| Receiving yards | 0.1/yd |
| Receiving TD | 6 |
| Fumble lost | -2 |
| Two-point conversion (pass/rush/rec) | 2 |
| Fumble recovery TD | 6 |

## Prizes

20% commission; 80% of entries forms the prize pool, paid to roughly the top 19%:

| Entries | Tiers (% of pool) |
|---------|-------------------|
| 15–100 | 1st: 25% · next 4%: 25% · next 15%: 50% |
| 101–300 | 1st: 15% · next 4%: 35% · next 15%: 50% |
| 301–700 | 1st: 7.5% · next 2%: 27.5% · next 2%: 15% · next 15%: 50% |
| 701–1200 | 1st: 5% · next 2%: 30% · next 2%: 20% · next 5%: 20% · next 10%: 25% |
| 1201+ | 1st: 4% · next 1%: 16% · next 1%: 13% · next 2%: 20% · next 5%: 22% · next 10%: 25% |

Ties across a tier boundary combine the affected tiers' pools and split equally.
Worked example given in-app: 250 entries × £10 → £2,000 pool; 1st £300, next 10 players
£70 each, next 38 players ~£26.32 each (their "38" implies round-half-up on 37.5, the
rounding assumed in `scripts/sunday_stars.py`). The table starts at 15 entries — no
published structure below that.

## Game issues

Postponed-before-kickoff NFL games void affected entries with refunds. Suspended games
count points scored up to the stoppage as final.
