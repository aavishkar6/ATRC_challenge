# Plan 3. The model plan

This file replaces `plan_2.md`. It keeps every number and every rule from that file in fewer words.
`plan.md` holds the deadline and the deliverables.

Order of work: clean, then features, then train, then test, then the simulator.

## Words this file uses

| Term | Meaning here |
|---|---|
| market | one hotel nationality, or the departure country that matches it |
| P2P | a point-to-point passenger. That passenger ends the trip at Abu Dhabi. |
| guest night | one guest, one bed, one night. The `Guests` column counts these. |
| capture rate | hotel arrivals of a market, divided by P2P arrivals of that market |
| elasticity | the slope of `log(guest nights)` against `log(P2P)` |
| WMAPE | the sum of absolute errors, divided by the sum of actual values |

---

## 1. The five questions

| # | Question | What the model must hold to answer it |
|---|---|---|
| 1 | A new route opens from a country that never flew here | A way to score a market with **no flight history**. A per-market coefficient cannot do this. We need a similarity prior. |
| 2 | An airline flies more or fewer flights per week | Weekly frequency as an explicit input, decoded correctly |
| 3 | Airlines add seats, by larger aircraft or extra flights | Frequency and seats per aircraft as **two** inputs. 3 x 180 seats must not equal 2 x 270 seats. |
| 4 | A larger or smaller share of seats gets filled | Load factor as its own input |
| 5 | The market mix moves with the season | Per-market elasticity, and a market x month term |

Three facts follow. They decide the design.

1. Questions 2, 3 and 4 are arithmetic. We checked two identities in all 117,608 rows.
   `Load Factor = Total PAX / Total Seats`. `Total PAX = Total P2P + Total Transfer + Total Transit`.
   Seats, frequency, load factor and transfer share therefore give arriving P2P with no estimation
   error.
2. One link stays uncertain. Arriving P2P must become guest nights. That link holds the transfer
   passengers who leave, the arrivals who stay with family, and residents and workers. The model
   must learn that one ratio, per market and per season.
3. Question 1 needs extrapolation. Step B5 answers it.

## 2. The design

```
 STAGE 1  identity, no error          STAGE 2  learned, the uncertain step
 ------------------------------       ----------------------------------------
 frequency  --\                       rolling P2P by market --\
 seats/aircraft -> seats              market identity        --+-> guest nights
 load factor --/     |                season and events      --|
 transfer share -----+-> arriving     domestic movement      --|
                        P2P           trend                  --/
```

Every lever in questions 2, 3 and 4 acts in Stage 1. The sliders therefore always respond. A reader
can check the arithmetic. Stage 2 never learns what a seat is.

---

## 3. What we measured

Scripts must reproduce each result below.

**3.1 The aviation signal survives seasonality removal.** We regressed `log(guest nights)` on
`log(P2P)` at market-month level, 2023-01 to 2025-07, with market x month-of-year fixed effects. The
elasticity is **0.586** and the correlation is 0.656. Per market, after we remove that market's own
month-of-year mean, **all 33 elasticities are positive**, median **0.63**.

| Elastic market | Elasticity | Weak market | Elasticity |
|---|---|---|---|
| Armenia | 1.53 | Oman | 0.02 |
| Qatar | 1.42 | Italy | 0.03 |
| United States | 1.15 | Lebanon | 0.12 |
| Spain | 1.11 | Jordan | 0.17 |
| Japan | 1.08 | Philippines | 0.22 |
| United Kingdom | 0.91 | Poland | 0.27 |

That median is the non-linearity the brief asks about. It means diminishing returns. 10% more
passengers buys about 6% more guest nights.

**3.2 Guest nights follow arrivals by about a week.** Correlation of daily guest nights with a
trailing P2P sum:

| Window | 1 day | 3 day | 5 day | **7 day** | 10 day | 14 day | 21 day |
|---|---|---|---|---|---|---|---|
| Correlation | 0.717 | 0.759 | 0.786 | **0.792** | 0.774 | 0.760 | 0.724 |

The 7-day window wins, which matches the measured stay of about 3.7 nights. Same-day flights are
the wrong feature. Use trailing sums.

**3.3 International demand peaks in fall and winter.** To remove the growth trend, we indexed each
year against its own mean, then averaged the two complete years, 2023 and 2024.

| | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| International | 1.00 | 1.01 | 1.01 | 1.01 | 0.96 | **0.76** | 0.87 | 1.00 | 0.87 | 1.14 | 1.15 | **1.24** |
| Domestic | 1.00 | 0.96 | 0.92 | 0.98 | 0.99 | 1.01 | 1.08 | **1.09** | 0.96 | 0.99 | 0.97 | 1.07 |

December is the strongest international month. June is the weakest. Domestic peaks in August.

**3.4 Flights carry most of the signal. Domestic adds a little.** Daily aggregate, log scale,
R-squared: month and weekday alone 0.246, trailing flights alone 0.629, both together 0.789, plus
domestic 0.804. Domestic alone explains 0.011.

The two seasonal shapes above correlate at **0.035**. International is a winter market and domestic
is a summer market. Domestic therefore enters as a control, because it carries variance the
international season term cannot. We will report that its contribution is small.

---

## 4. Plan A. Clean the data, build the features

Target: one table. One row per date and market. 2023-01-01 onward.

Every step below uses the same four lines, so a reader can check each one.

- **We have** — what the supplied file gives us.
- **The issue** — why we cannot use it as it arrives.
- **We do** — the change we make, and the reason.
- **New variables** — the columns the step adds.

Steps A1 to A6 clean. Steps A7 to A11 add variables. A12 states two rules we will not break. A13
lists every new variable in one table.

### A1. The flight file mixes two time grains

- **We have** — flight rows from 2022-01-01 to 2026-02-28, under one `Date` column.
- **The issue** — 2022 holds 12 dates only, one per month, at about 6,077 seats per row. 2023 onward
  holds every day, at about 350 seats per row. The 2022 rows are monthly totals. One column name
  covers two grains. A daily model would read 2022 as twelve very large days.
- **We do** — tag each row. Build the model table from daily rows only. Keep 2022 for the trend chart
  alone, because it is also a COVID recovery year and would bias the levels.
- **New variables** — `grain`, with the value `monthly` or `daily`.

### A2. The frequency column is not a weekly count

- **We have** — `Average Weekly Frequency`, one value per route and day. Example values are 0.2258,
  0.4516 and 0.6774.
- **The issue** — the name says weekly, but the number is neither a weekly count nor a daily count.
  Nobody can set a frequency slider from it. The column is also empty for all 1,213 rows of 2022.
- **We do** — decode it with `flights that day = AWF x days_in_month / 7`. That gives a whole number
  in all 116,395 rows. The three example values become 1, 2 and 3 flights. Write the formula once, in
  `src/decode.py`, with a test that checks the whole-number result.
- **New variables** — `flights_per_day`, `weekly_frequency` (the sum of AWF across the month's days),
  and `seats_per_aircraft` (`Total Seats` divided by `flights_per_day`). Seats per aircraft must land
  on a real gauge. The common values are 174, 186, 230, 239, 290, 327 and 371.

### A3. Some load factors are above 1

- **We have** — `Load Factor`, which equals `Total PAX` divided by `Total Seats` exactly.
- **The issue** — 9,896 rows report more than 1, which is 8.4%. Only 72 rows exceed 1.05. The maximum
  is 1.857. A load factor above 1 means more passengers than seats, and a real flight cannot do that.
- **We do** — keep the original column untouched, and add a capped copy beside it. Report the count of
  capped rows in the cleaning log. We do not change a supplied number in place.
- **New variables** — `load_factor_clean`, capped at 1.00, and `load_factor_capped`, a true or false
  flag.

### A4. Half the arriving passengers never reach a hotel

- **We have** — `Total PAX`, and the split into `Total P2P`, `Total Transfer` and `Total Transit`.
  The three parts add to `Total PAX` exactly.
- **The issue** — transfer passengers are **49.5%** of all arrivals. They change aircraft and leave.
  A model built on `Total PAX` therefore counts about twice the real demand.
- **We do** — use `Total P2P` as the passenger base. Keep the transfer share as its own variable,
  because it runs from 0.89 for the United States to 0.00 for Armenia. A new route from a
  high-transfer market delivers fewer hotel guests per seat.
- **New variables** — `transfer_share`, which is `Total Transfer` divided by `Total PAX`.

### A5. Flight country and hotel country mean different things

- **We have** — `Departure Country Name` in the flight file, with 33 values. `Nationality` in the
  hotel file, with 45 values.
- **The issue** — one names the country the aircraft left from. The other names the passport the guest
  holds. They do not count the same people. 12 nationalities have no direct route at all: Australia,
  Brazil, Czechia, Denmark, Finland, Mexico, Morocco, Norway, Pakistan, Romania, South Africa and
  Sweden.
- **We do** — uppercase and strip both keys, then join the 33 exact matches. Write the weights to
  `reference/bridge.csv`, so a reader can check them. Keep the 12 unmatched markets in the table. They
  hold hotel history and no flight history, which makes them our test cases for question 1.
- **New variables** — `market`, one key that works in both files, and `has_direct_route`, a true or
  false flag.

### A6. Blank cells mean two different things

- **We have** — hotel rows with empty cells, and an incomplete date-by-market grid.
- **The issue** — a blank can mean zero, or it can mean unknown. The two need different treatment. A
  zero in a ratio gives a wrong answer. A missing value in a ratio gives no answer.
- **We do** — apply the rules in the table below, and record every filled cell.

| Column | Blanks | Rule and reason |
|---|---|---|
| `Same-Day Guests`, international train | 35,026 of 58,622 (59.7%) | Set to 0. A count with no row means no such guest. |
| `New Arrivals`, international train | 262 | Keep as missing. Never put a missing value in a ratio. |
| `New Arrivals`, international test | 2 | Same rule. |
| `Average Weekly Frequency`, 2022 | all 1,213 rows | Not used. A1 excludes 2022. |
| date x market grid | 238 absent cells of 58,860 | Set to 0, but only after we check that the nearby days are small. |

- **New variables** — `was_filled`, a true or false flag on every cell we filled.

### A7. Flights and guest nights do not fall on the same day

- **We have** — daily flight arrivals, and daily guest nights.
- **The issue** — a guest who lands today still holds a bed for about 3.7 nights. Same-day flights
  therefore explain today's guest nights poorly. The correlation is 0.717 for the same day, against
  **0.792** for a trailing 7-day sum.
- **We do** — build trailing sums per market. Shift nothing forward, because flights come before
  guests, never after them.
- **New variables** — `p2p_3d`, `p2p_7d`, `p2p_14d`, `p2p_28d`, `seats_7d` and `flights_7d`. Result
  3.2 shows that 7 days wins. We keep 3, 14 and 28 days so the model can choose.

### A8. The files hold no calendar and no season measure

- **We have** — a `Date` column. The brief lists an event calendar as supplied data, but the folder
  holds none.
- **The issue** — a month number cannot hold Ramadan, because Ramadan moves about 11 days earlier each
  year. The files also never state that December is the strongest international month at index 1.24,
  or that June is the weakest at 0.76.
- **We do** — write `reference/events.csv` ourselves, with a `source` column on every row, so a reader
  can check each date. Compute the season index from training data only.
- **New variables** — `month`, `day_of_week`, `week_of_year`, `season_index` (market by month, from
  3.3), `is_ramadan`, `is_eid`, `is_f1_weekend`, `is_national_day`, `is_chinese_new_year`,
  `is_diwali`, `is_uk_half_term`.

### A9. The market name tells the model nothing about a new market

- **We have** — a market name, which a model reads as a label.
- **The issue** — a label carries no meaning for a market the model never saw. Markets also differ a
  lot, from elasticity 0.02 for Oman to 1.53 for Armenia. Question 1 needs numbers, not names.
- **We do** — describe each market by numbers. The flight file holds no distance and no flight time,
  so we add two small reference files ourselves: `reference/cities.csv` with a coordinate per
  departure city (130 rows), and `reference/markets.csv` with a region per market (45 rows). Compute
  every history variable from training data only.
- **New variables** — `region`, `haul_band`, `capture_rate_hist`, `stay_length_hist`,
  `elasticity_tier`, `n_airlines`, `n_cities`, `route_is_new`, `months_since_first_flight`.

### A10. Domestic demand is large, and flights do not drive it

- **We have** — the two domestic hotel files, with daily guests and daily arrivals.
- **The issue** — domestic guests are **38.6%** of all guest nights, and they mostly travel by road.
  If we leave them out, the total is wrong by more than a third. If we drive them from flights, we
  invent a link that does not exist.
- **We do** — add them as a control, not as a driver. The two seasonal shapes correlate at **0.035**,
  so domestic carries variance the international season term cannot carry. Keep the aviation levers
  off this series.
- **New variables** — `dom_arrivals_7d` and `dom_guests_7d`.

### A11. The market grew across the window

- **We have** — four years of history.
- **The issue** — monthly seats nearly tripled, from 457,276 in January 2022 to 1,286,158 in July
  2025. A model trained flat across four years learns a level that is too low for 2026.
- **We do** — add trend variables, and prefer a share to a level where a share works.
- **New variables** — `days_since_start` and `market_share_12m`.

### A12. Two rules against leakage

1. **No lagged target in the simulator model.** `Guests` is absent from both test files, so a lag is
   not computable there. A lag would also swamp the aviation features and freeze the sliders.
2. **The test files supply `New Arrivals`.** A model that reads `New Arrivals` scores well. It cannot
   answer any of the five questions, because a new route changes arrivals. So we keep two models
   apart.
   - **Model S**, the simulator. Flights, calendar and domestic only.
   - **Model R**, the reference. Also reads the supplied `New Arrivals`.

   The gap between S and R measures how much aviation alone explains. We report both numbers.

### A13. Every variable we added, in one place

| Variable | What it is | From |
|---|---|---|
| `grain` | `monthly` or `daily`, so the 2022 rows cannot pollute a daily model | A1 |
| `flights_per_day` | the real flight count for that route and day | A2 |
| `weekly_frequency` | flights per week for that route and month. Question 2 moves this. | A2 |
| `seats_per_aircraft` | gauge of the aircraft. Question 3 moves this. | A2 |
| `load_factor_clean` | load factor, capped at 1.00. Question 4 moves this. | A3 |
| `load_factor_capped` | true where we capped the value | A3 |
| `transfer_share` | share of arrivals that change aircraft and leave | A4 |
| `market` | one key that joins the flight file to the hotel file | A5 |
| `has_direct_route` | false for the 12 markets with no direct flight | A5 |
| `was_filled` | true where we filled a blank cell | A6 |
| `p2p_3d`, `p2p_7d`, `p2p_14d`, `p2p_28d` | trailing sums of arriving P2P passengers | A7 |
| `seats_7d`, `flights_7d` | trailing sums of supply | A7 |
| `month`, `day_of_week`, `week_of_year` | plain calendar position | A8 |
| `season_index` | the market by month demand index from 3.3 | A8 |
| `is_ramadan`, `is_eid` | moving religious dates a month number cannot hold | A8 |
| `is_f1_weekend`, `is_national_day` | Abu Dhabi demand spikes | A8 |
| `is_chinese_new_year`, `is_diwali`, `is_uk_half_term` | source-market holidays | A8 |
| `region`, `haul_band` | where the market sits, and how far away | A9 |
| `capture_rate_hist` | past share of that market's arrivals that used a hotel | A9 |
| `stay_length_hist` | past nights per arrival for that market | A9 |
| `elasticity_tier` | how strongly that market answers a change in flights | A9 |
| `n_airlines`, `n_cities` | how many carriers and cities serve the market | A9 |
| `route_is_new`, `months_since_first_flight` | route age. Question 1 needs this. | A9 |
| `dom_arrivals_7d`, `dom_guests_7d` | domestic demand, as a control | A10 |
| `days_since_start`, `market_share_12m` | growth trend across the window | A11 |

Questions 2, 3 and 4 move `weekly_frequency`, `seats_per_aircraft` and `load_factor_clean`. Those
three are the Stage 1 levers from section 2.

### A14. Output

```
data/clean/flights.parquet     grain tagged, frequency decoded, load factor flagged
data/clean/hotel_intl.parquet  date x market, null rules applied
data/clean/hotel_dom.parquet   date
data/features/panel.parquet    the model table
reference/bridge.csv           origin to nationality weights
reference/events.csv           our event calendar, with sources
reference/cities.csv           a coordinate per departure city, 130 rows
reference/markets.csv          a region per market, 45 rows
reports/cleaning_log.md        every decision, its count, its reason
```

`reports/cleaning_log.md` is a deliverable, because criterion 7 asks for stated assumptions.

---

## 5. Plan B. Choose and train the model

### B1. Target and split

The target is `Guests`, which counts guest nights per date and market.

The brief asks about occupancy, but the dataset holds no room supply count, so we cannot compute an
occupancy percentage. Guest nights is the honest proxy. We will ask the DCT mentors for room supply.

| Split | Period | Use |
|---|---|---|
| Train | 2023-01-01 to 2024-12-31 | Fit |
| Tune | 2025-01-01 to 2025-07-31 | Choose the model and its settings |
| Test | 2025-08-01 to 2026-02-28 | Use once, at the end |

Use time-ordered splits only. A random split leaks the future into the past.

### B2. The candidates

| # | Model | Form | What it tests |
|---|---|---|---|
| M0 | Seasonal naive | Same month last year, scaled by trend | The floor. We must beat it. |
| M1 | Parametric chain | `seats x LF x (1-transfer) x capture x stay`, per market and month | The transparent baseline. The interface audits this. |
| M2 | Panel regression | `log(guests) ~ market FE + season + beta_market x log(p2p_7d) + controls` | A readable elasticity per market |
| M3 | LightGBM | All features. Monotone constraint on every seat and P2P feature. | Non-linearity and interaction |
| M4 | Hybrid | M3 fitted on the residual of M2 | The shape the brief recommends |

Fit in log space. Markets differ by orders of magnitude, and log space states the elasticity
directly. For the uncertainty range the brief asks for, fit LightGBM at quantiles 0.1, 0.5 and 0.9.
A measured range replaces a fixed multiplier.

### B3. The monotone constraint matters more than the score

LightGBM accepts `monotone_constraints`. Set a positive constraint on every seat, flight and P2P
feature.

Without it, a tree can learn a downward kink from noise. The simulator would then show fewer hotel
guests after an airline adds a flight. A judge finds that in one click, and a low WMAPE does not
excuse it.

### B4. Selection rule, in order

A model must pass gate 1 before its score counts.

1. **Lever gate.** Sweep seats, frequency and load factor across their plausible ranges. Predicted
   guest nights must rise in each sweep. Reject any model that fails, whatever its WMAPE.
2. **WMAPE on the tune window.**
3. **WMAPE per market.** A good total must not hide a broken market.
4. **Readability.** If two models tie within about 1 point of WMAPE, ship the simpler one.

Then run the winner once on the test window. Report the number we get, not the best number we saw.

### B5. Question 1 needs its own method

A per-market coefficient cannot score a market that never flew here.

1. Build a similarity prior. Describe each market by region, flight time band, transfer share, past
   capture rate and past stay length.
2. For a new origin, borrow the capture rate and the elasticity from the nearest markets, weighted by
   similarity.
3. **Check it with a hold-one-market-out test.** Drop one market from training. Predict it from the
   prior alone. Measure the error. Repeat for all 33 markets. That error becomes the stated
   uncertainty on every new-route answer.
4. Demonstrate on the 12 markets with no direct route. Ask what a direct route from Australia would
   add. Compare the answer against the indirect arrivals Australia already produces.

Most teams will skip step 3. It turns a guess into a measured error bar.

### B6. Sensitivity

Run this on the chosen model, not on the chain alone.

1. One-at-a-time sweep, per lever, per market tier. It feeds the planner briefing.
2. SALib Sobol indices across all levers together, to find interactions. Seats and load factor
   interact by construction, because they multiply.
3. Report the measured ranking. We expect capture rate first, then stay length, then load factor,
   then seats. We will publish the measured order even if it contradicts that.

### B7. What we report

| File | Contents |
|---|---|
| `reports/model_selection.csv` | Every model, tune WMAPE, lever gate result |
| `reports/test_results.csv` | The chosen model on the test window, with M0 and Model R beside it |
| `reports/wmape_by_market.csv` | Per market, worst first. The paper names the worst three. |
| `reports/elasticity.csv` | Per-market elasticity from M2, with a confidence interval |
| `reports/sensitivity.csv` | Lever ranking, per market tier |
| `reports/holdout_market.csv` | The hold-one-market-out error from B5 |

---

## 6. Limits we state beside the numbers

1. The flight file holds Abu Dhabi arrivals only. Dubai airport is about 90 minutes away by road, and
   we cannot see guests who land there. This is the largest single limit.
2. Aggregated data cannot separate a guest who stays with family from a tourist who avoids hotels.
   The capture rate absorbs both. We can measure the ratio, not the reason.
3. Departure country is not nationality. The bridge is an estimate.
4. Domestic guest nights are 38.6% of the total. They do not respond to aviation levers.
5. A new-route answer rests on the prior in B5. It carries the wider error bar from step 3.

## 7. Order of work and gates

| Step | Output | Gate before the next step |
|---|---|---|
| A1 to A6 | `data/clean/*.parquet` | The frequency test passes. Both identities hold. |
| A7 to A11 | `data/features/panel.parquet` | Row count and date range match expectation |
| B1, B2 | M0 and M1 scored on tune | M1 beats M0 |
| B2, B3 | M2 and M3 scored on tune | The lever gate passes |
| B4 | One chosen model, scored on test | Test WMAPE beats M0 by a clear margin |
| B5, B6 | The new-route prior, the lever ranking | We measured the hold-one-market-out error |
| Last | The simulator, above the chosen model | Not before |

The last row is the point. The simulator is a view over a tested model.
