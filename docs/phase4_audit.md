# Phase 4 audit and final results

**Audit completed 2026-11-27. Status: reviewed.** All checks below passed after the changes
listed in section 2. Every figure is a modelled **estimate** with a low–high range. Figures
refer to the stated month (latest: **May 2026**, the latest NBS fuel-price month), in nominal ₦.

**Sources:** NBS Price Watch (petrol, diesel); NERC tariff orders; Global Solar Atlas 2.0
(© The World Bank, Source: Global Solar Atlas 2.0, Solar resource data: Solargis, CC BY 4.0);
CBN exchange rates; NBS CPI; NBS NLSS 2018/19 and *Consumption Expenditure Pattern in
Nigeria 2019*; NBS MPI 2022; 2026 Nigerian solar retail and installer prices (see
`docs/parameters.md`).

**Method:** `docs/analysis_plan.md` v1.0 + amendments A1–A8 (`docs/amendments.md`). The plan
SHA-256 `ed70b3992602c0ecdf58f7ade9f28b42155d5209f116d2b2591d51acd89677f3` matches the A8 entry.

## 1. What was checked

| # | Check | Result |
|---|---|---|
| 1 | Independent recomputation of 10 random state-month-user rows × 3 cases × 6 measures (generator ₦/kWh, solar upfront cost, LCOE, monthly saving, payback, affordability) with separate code (`src/audit_recompute.py`, parameters re-entered by hand) | **180 / 180 match** (tolerance 1e-6); `data/processed/model/audit_recompute.csv`. The random sample had 8 business rows and 2 household rows; household logic is also covered by unit tests |
| 2 | Solar cost stress test against independent 2026 Nigerian sources | Household system was **below** the market range, so A8 was logged and the model recomputed. It now fits the range (section 3) |
| 3 | Edge cases: fuel-price extremes, Borno, the 7 placeholder-tariff states, Aba | Consistent; details in section 4 |
| 4 | Safe-claim review of `docs/phase3_results.md` | 3 issues found and fixed (section 2) |
| 5 | Full test suite (`tests/test_data.py`, `tests/test_model.py`) and plan hash | **45 / 45 tests pass**; hash matches A8 |

## 2. What changed

- **A5:** RQ3 is now **payback** (upfront ÷ monthly fuel + maintenance saving) plus
  **affordability** (household upfront cost in months of consumption). Crossover is kept as
  a supporting table. New input: `household_consumption_state_monthly.csv` (NBS 2019
  state expenditure, NBS CPI chained).
- **A6:** priority index G is now the monthly ₦ saving (it was the near-constant cost-gap %).
- **A7:** solar, payback, affordability and crossover start June 2023; generator costs and
  tariffs still start January 2023.
- **A8 (from the stress test):** inverter costed explicitly (household ₦120k / 175k / 300k;
  business ₦2.8m / 3.5m / 4.2m, 2026 ₦). The balance-of-system share now excludes the inverter.
- **Safe-claim fixes in `phase3_results.md`** (now marked as superseded):
  - The RQ5 table of national totals was removed (rule 4).
  - "Monthly cost" figures were labelled as central estimates (rule 1).
  - An unsourced statement about import exchange rates was replaced with CBN data (rule 2).
- **Accepted as limits (owner decision):** no business full cost (no 20 kVA diesel price
  source); the 35% plausibility limit and household size 4.5 / 5.0 / 5.5 are kept.

## 3. Solar cost stress test — final range (May 2026, ₦)

| System | Modelled low | Modelled central (state range) | Modelled high | Independent 2026 references |
|---|---|---|---|---|
| Household, about 0.6 kWp + about 1.6 kWh LFP + 1 kVA inverter | 0.45–0.50 m | **0.87–0.94 m** | 1.40–1.51 m | Smallest lithium package (1 kVA, 1–1.2 kW panels, 2.5 kWh) ₦0.90–1.35 m (solarinverterinstallation.com; afrotools.com); seller listing ₦0.94 m; installed 1–2 kVA ₦0.85–1.2 m (BusinessDay, early 2026); 3 kVA ≈ ₦1.5 m (installer quote, April 2026, Leadership/allAfrica) |
| Business, about 17.8 kWp + about 21 kWh LFP + 20 kW inverter | 7.5–9.0 m | **15.7–18.0 m** | 26.8–30.2 m | Components: 20 kW Deye inverter ₦3.50 m, 5.12 kWh LFP ₦1.14 m each, panels ≈ ₦1.05 m per 8 × 590 W (retail listings, Nov 2026), about ₦12 m before installation; "20 kVA+ with 40 kWh+" ₦12 m+ (afrotools.com) |

Before A8 the household central cost was about ₦0.73 m, below the independent range. After A8
it lies inside it. The business central cost is at or slightly above the component-based
estimate, which is conservative for solar. All sources are retail or installer pages (quality C).

## 4. Edge cases (May 2026, central)

- **Fuel-price extremes:**
  - Highest petrol: Edo, ₦1,723/L → household payback 10.0 months.
  - Lowest petrol: Adamawa, ₦1,470/L → 11.4 months.
  - Highest diesel: Nasarawa, ₦3,786/L → business payback 7.9 months.
  - Lowest diesel: Kogi, ₦2,824/L → 10.6 months.
  - Payback follows fuel price as expected.
- **Borno:** reliance and household consumption both use North-East zone averages (A2, A5),
  flagged in `dim_state` and the consumption table. Household payback 10.6 months; upfront
  cost about 4.0 months of consumption.
- **Placeholder-tariff states** (Ekiti, Enugu, Imo, Kogi, Lagos, Niger, Ondo):
  - The NERC Band A rate (₦209.50/kWh) is shown as a flagged placeholder (A1).
  - Household solar costs ₦324–331/kWh there.
  - Payback does not use tariffs, so these states' payback results are unaffected.
- **Aba:** Abia uses EEDC tariffs. Aba Power's cost-reflective tariffs (Band A ₦219.70, Band B
  ₦210.46 in Jan 2025) are noted in `dim_state` and not averaged, so the grid comparison does
  not represent Aba customers.

## 5. Final headline results (estimates)

1. **Payback, May 2026 (central; low–high across all states):**
   - **Households (2.5 kVA petrol generator, about 1.6 kWh/day):** **9.6–11.6 months**
     (2.1–39.4 months).
   - **Small businesses (20 kVA diesel, about 51 kWh/day):** **7.9–10.6 months** (2.6–22.2 months).
2. **Payback over time** (national median of state values, central):
   - Households: 14 months in June 2023, a peak of about 24 months in mid-2024 (solar costs
     rose with the naira's fall before petrol prices caught up), 17 months in January 2026,
     11 months in May 2026.
   - Businesses: 17 → 26 (Aug 2024) → 9 months.
3. **Upfront cost and affordability:** a household system costs about ₦0.9 m (central),
   equal to **1.2–6.6 months of average household consumption** depending on the state
   (median 2.4). It is least affordable in Ebonyi (6.6), Sokoto (5.6), Taraba (5.1),
   Jigawa (5.1) and Bauchi (4.1).
4. **Monthly saving from switching (household, central):** ₦77,800 (Adamawa) to ₦91,300 (Edo).
5. **Supporting crossover result:**
   - **Central case:** solar plus battery was cheaper per kWh than the generator in every
     state from June 2023 (the start of the solar series), for both users.
   - **Robust test, households:** passed from June 2023 in 24 states and August 2023 in 8
     more. In the Niger Delta it came later: Cross River in Dec 2024, Akwa Ibom in Feb 2026,
     and Bayelsa, Delta and Rivers in Mar 2026 (weakest solar resource, so larger systems).
   - **Robust test, businesses:** passed June–September 2023 in all states.
   - With solar held at 2026 naira prices instead of A4, the household robust crossover is
     Sep–Nov 2024.
6. **Grid tariffs** (price reference only; supply hours not modelled): Band A ₦209.50/kWh is
   below household solar (about ₦325/kWh central); Bands B–E (₦32–69/kWh) are far lower.
7. **Market priority, top 10** (equal weights, household saving, generator as primary
   electricity source):
   - 1 Edo, 2 Delta, 3 Abia, 4 Ondo, 5 Imo, 6 Akwa Ibom, 7 FCT, 8 Oyo, 9 Ekiti, 10 Rivers.
   - Bottom 5: Gombe, Yobe, Adamawa, Katsina, Sokoto.
   - Across all 12 variants: Abia, Edo and FCT are always in the top 10; Oyo in 11; Imo and Delta in 10.
   - States are presented as ranks and groups, not precise scores.
8. **National totals:** not published (the RQ5 range failed the consistency check with
   NMDPRA national petrol volumes).

### Payback and affordability by state (May 2026)

| State | HH payback, months (central; low–high) | HH saving ₦/month (central) | HH upfront ₦ (central) | HH upfront in months of consumption (central; range) | Business payback, months (central; low–high) | Priority rank |
|---|---|---|---|---|---|---|
| Abia | 10.5 (2.4–35.7) | 87,606 | 922,294 | 2.0 (1.0–3.6) | 9.6 (3.2–20.0) | 3 |
| Adamawa | 11.4 (2.5–38.9) | 77,800 | 886,078 | 4.0 (1.9–7.3) | 8.8 (2.9–18.4) | 35 |
| Akwa Ibom | 10.9 (2.5–36.9) | 86,265 | 938,986 | 2.3 (1.1–4.1) | 9.7 (3.3–20.3) | 6 |
| Anambra | 11.4 (2.6–38.8) | 80,441 | 915,531 | 1.5 (0.7–2.6) | 9.0 (3.0–18.8) | 23 |
| Bauchi | 9.6 (2.1–32.7) | 90,935 | 875,033 | 4.1 (1.9–7.4) | 8.9 (2.9–18.8) | 20 |
| Bayelsa | 11.2 (2.5–37.9) | 84,249 | 940,792 | 2.0 (1.0–3.6) | 10.1 (3.4–21.1) | 29 |
| Benue | 10.1 (2.3–34.2) | 90,004 | 907,425 | 2.3 (1.1–4.2) | 10.1 (3.4–21.2) | 12 |
| Borno | 10.6 (2.4–36.3) | 82,151 | 874,364 | 4.0 (1.9–7.1) | 8.7 (2.8–18.4) | 25 |
| Cross River | 11.3 (2.5–38.5) | 82,114 | 927,828 | 2.4 (1.1–4.2) | 9.1 (3.1–19.1) | 19 |
| Delta | 10.5 (2.4–35.6) | 88,338 | 926,435 | 1.2 (0.6–2.1) | 9.7 (3.3–20.2) | 2 |
| Ebonyi | 10.6 (2.4–35.9) | 86,515 | 914,489 | 6.6 (3.1–11.8) | 8.5 (2.8–17.7) | 13 |
| Edo | 10.0 (2.3–34.0) | 91,298 | 916,244 | 1.3 (0.6–2.3) | 9.2 (3.1–19.2) | 1 |
| Ekiti | 10.9 (2.4–37.0) | 84,649 | 921,316 | 2.2 (1.1–4.0) | 9.6 (3.2–20.0) | 9 |
| Enugu | 11.1 (2.5–37.6) | 83,137 | 919,066 | 2.4 (1.1–4.3) | 9.7 (3.2–20.2) | 14 |
| FCT | 10.8 (2.4–36.6) | 84,874 | 913,381 | 1.5 (0.7–2.6) | 9.1 (3.0–19.0) | 7 |
| Gombe | 9.9 (2.2–33.5) | 89,375 | 880,629 | 3.3 (1.5–5.9) | 8.9 (2.9–18.8) | 33 |
| Imo | 10.9 (2.4–37.1) | 84,318 | 919,175 | 1.4 (0.7–2.5) | 9.6 (3.2–20.1) | 5 |
| Jigawa | 9.9 (2.2–33.7) | 87,496 | 866,477 | 5.1 (2.4–9.1) | 8.0 (2.6–16.9) | 26 |
| Kaduna | 10.7 (2.4–36.6) | 83,330 | 895,464 | 3.3 (1.6–6.0) | 8.3 (2.7–17.3) | 24 |
| Kano | 10.2 (2.3–34.8) | 85,157 | 870,751 | 3.3 (1.6–6.0) | 8.4 (2.7–17.8) | 32 |
| Katsina | 11.2 (2.5–38.3) | 77,856 | 870,759 | 3.3 (1.5–5.9) | 8.9 (2.9–18.8) | 36 |
| Kebbi | 10.7 (2.4–36.6) | 82,350 | 883,342 | 3.3 (1.6–5.9) | 9.5 (3.1–20.0) | 31 |
| Kogi | 11.2 (2.5–38.0) | 81,229 | 906,324 | 2.2 (1.0–3.9) | 10.6 (3.5–22.2) | 18 |
| Kwara | 11.0 (2.5–37.5) | 82,369 | 907,431 | 2.3 (1.1–4.1) | 9.5 (3.2–20.0) | 17 |
| Lagos | 11.1 (2.5–37.7) | 82,658 | 915,597 | 1.2 (0.6–2.2) | 9.6 (3.2–20.2) | 27 |
| Nasarawa | 10.8 (2.4–36.9) | 83,463 | 905,396 | 2.5 (1.2–4.5) | 7.9 (2.6–16.4) | 15 |
| Niger | 11.1 (2.5–37.8) | 81,446 | 903,349 | 3.1 (1.5–5.5) | 9.4 (3.1–19.7) | 30 |
| Ogun | 11.0 (2.5–37.3) | 84,630 | 929,344 | 1.6 (0.8–2.9) | 9.6 (3.2–20.0) | 11 |
| Ondo | 10.9 (2.5–37.1) | 84,654 | 924,141 | 1.7 (0.8–3.1) | 10.2 (3.4–21.3) | 4 |
| Osun | 11.6 (2.6–39.4) | 81,343 | 940,999 | 1.8 (0.8–3.2) | 9.3 (3.2–19.3) | 22 |
| Oyo | 10.8 (2.4–36.6) | 86,849 | 936,051 | 1.5 (0.7–2.7) | 9.5 (3.2–19.8) | 8 |
| Plateau | 10.4 (2.3–35.3) | 86,019 | 893,700 | 2.8 (1.3–5.0) | 8.1 (2.7–17.1) | 21 |
| Rivers | 11.2 (2.5–37.9) | 83,687 | 933,826 | 1.6 (0.7–2.8) | 9.1 (3.1–19.0) | 10 |
| Sokoto | 11.0 (2.4–37.7) | 78,855 | 869,922 | 5.6 (2.6–10.1) | 7.9 (2.6–16.7) | 37 |
| Taraba | 10.3 (2.3–34.9) | 87,308 | 897,135 | 5.1 (2.4–9.1) | 8.4 (2.8–17.6) | 16 |
| Yobe | 9.8 (2.2–33.4) | 88,292 | 868,443 | 3.8 (1.8–6.9) | 8.2 (2.7–17.2) | 34 |
| Zamfara | 10.3 (2.3–35.2) | 84,875 | 878,348 | 3.9 (1.8–7.0) | 8.7 (2.8–18.3) | 28 |

HH = household (2.5 kVA petrol); Business = 20 kVA diesel. Payback is simple (undiscounted)
and excludes battery replacement. Low = solar low-cost with generator high-cost; high = the
reverse. Affordability ranges combine the upfront-cost case with household size 4.5–5.5.

## 6. Remaining limits

- **Generator use:** small petrol generator load and idle fuel use are the largest
  uncertainty, and the reason for the wide low–high payback range.
- **Solar costs:** from retail and installer pages, not an official benchmark. They are
  converted over time at the CBN official rate (A4), with a constant US$ price assumed.
- **Reliance and consumption** come from NLSS 2018/19 (2019 expenditure, CPI-adjusted;
  2021/22 population). Borno uses zone averages. The national CPI is applied to all states.
- **Tariffs:** 7 states show NERC placeholders. Aba is not represented. Supply hours are not
  modelled, so grid prices are not an availability claim.
- **Financing:** payback assumes the upfront cost can be paid or financed. The household
  upfront cost equals 1.2–6.6 months of consumption.
- **Business full cost is not computed** (no 20 kVA price source). Household full cost uses a
  constant 2026 ₦ generator price.
- **Solar resource** is a long-term average (1994–2018), not weather in the specific month.
- **National generator fuel use and CO2** are not published.
