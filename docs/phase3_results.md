# Phase 3 results: cost model, crossover and priority index

**SUPERSEDED (2026-11-27) by `docs/phase4_audit.md`.** This is the Phase 3 record. Amendments
A5–A8 (payback, saving-based index, June 2023 start, explicit inverter cost) changed several figures
below; use `docs/phase4_audit.md` for current numbers. All figures are estimates.
Model: `src/model.py`, following `docs/analysis_plan.md` (v1.0 + amendments A1–A4) and
`docs/parameters.md`. Months: Jan 2023 – May 2026 (latest NBS price month). Money is
nominal ₦. Each figure has a low/central/high range; "central" is quoted unless stated.
Sources: NBS fuel prices, NERC tariff orders, Global Solar Atlas 2.0 (© The World Bank,
Solar resource data: Solargis), CBN exchange rates, NBS NLSS 2018/19 and MPI 2022.
All 38 tests pass (`tests/test_data.py`, `tests/test_model.py`).

## 1. Headline findings

1. **In the central case, solar plus battery was already cheaper per kWh than a small
   generator in all 37 states at the start of the series (January 2023), for both typical
   users.** There is no later "crossover month" to report. The method can only say
   "January 2023 or earlier".
2. **By May 2026 the gap is very large:**
   - **Household (2.5 kVA petrol, about 0.4 kW for 4 h a day):** the generator costs about
     **₦2,230–2,620 per kWh** (state range, central; ₦2,426 median). Solar plus battery
     costs about **₦246–273 per kWh**. That is about 89% cheaper in every state.
   - **Typical monthly cost (central estimate, May 2026):** about ₦85,000 a month on fuel and
     maintenance, against about ₦9,000 a month for the same energy from solar (spread over
     10 years; before A8 added the inverter cost).
   - **Small business (20 kVA diesel at 40% load, 8 h a day):** about ₦1,210–1,630 per kWh
     for the generator against about ₦136–162 for solar.
3. **Robust test (the generator's cheapest case still costs more than solar's dearest case):**
   - **Households:** true in **26 states from June 2023**, the month petrol subsidy was
     removed. It was true earlier in 11 states: January 2023 in Ebonyi, Enugu, Imo, Jigawa,
     Kaduna and Kano; February–May 2023 in Adamawa, Katsina, Gombe, Taraba and Kebbi.
   - **Small businesses:** true in all states from January 2023.
   - **By May 2026:** solar is cheaper in all 37 states, even in the robust test.
4. **The timing of the robust result depends on the exchange-rate assumption (A4).** A4
   converts 2026 naira solar prices to US$ and back at each month's CBN official rate.
   Before June 2023 the CBN official rate was about ₦455–461/US$. It jumped to about ₦770/US$
   within June 2023 when the exchange-rate windows were unified (CBN data), which suggests the
   earlier official rate understated import costs. A4 therefore probably makes early solar
   look too cheap (addressed by A7).
   - With solar held at **2026 naira prices** (the plan's original rule), the robust
     household crossover moves to **May–September 2024**: May 2024 in Benue and Jigawa,
     and August–September 2024 in 29 states, when petrol passed about ₦1,000/L.
   - On that basis the robust business crossover is **October 2023 – June 2024**.
   - The central-case result (solar cheaper from January 2023) is the same under both
     assumptions.
5. **Grid tariffs are lower than both, where supply exists.**
   - Band A has been ₦209.50/kWh since July 2024; Bands B–E are ₦32–69/kWh.
   - Household solar (₦246–273/kWh) is above Band A but far below the generator.
   - Supply hours are not modelled (A1). These are price references only.
   - Seven states (Ekiti, Enugu, Imo, Kogi, Lagos, Niger, Ondo) show NERC rates as
     placeholders because their own regulators now set tariffs.
6. **Market priority (equal weights, household gap, generator as primary electricity
   source):**
   - **Top 10:** 1 Edo, 2 Delta, 3 Abia, 4 Imo, 5 Ondo, 6 FCT, 7 Oyo, 8 Ekiti, 9 Benue,
     10 Akwa Ibom.
   - **Bottom 5:** Yobe, Gombe, Osun, Bayelsa, Sokoto.
   - **Stable across all 12 variants** (3 weightings × 2 users × 2 reliance measures):
     Abia, Edo and FCT are in the top 10 every time; Imo in 10 of 12; Delta in 8.

## 2. Key sensitivities

One parameter at a time, latest month, household, one state per zone
(`model/sensitivity_tornado.csv`). Median swing in ₦/kWh:

| Side | Parameter | Swing (₦/kWh) |
|---|---|---|
| Generator | Average load (0.26–0.57 kW) | ≈1,420 |
| Generator | Idle-fuel fraction `a` (0.15–0.45) | ≈1,360 |
| Generator | Full-load fuel use (1.0–1.4 L/h) | ≈830 |
| Generator | Maintenance (10–25%) | ≈330 |
| Solar | Discount rate (10–25%) | ≈150 |
| Solar | Night share (0.5–0.9) | ≈110 |
| Solar | Battery price | ≈100 |
| Solar | PV price, battery life, balance of system | 40–50 each |

The uncertainty sits mainly on the generator side (how lightly small petrol generators are
loaded), but even the low-cost generator case is several times the high-cost solar case
in 2026. Results are not sensitive to the solar cost assumptions within the ranges used.

## 3. RQ5: national household generator petrol and CO2 — not publishable

*Table removed in the Phase 4 audit (safe-claim rule 4): national totals are not shown,
because the range failed the consistency check. The internal working file is
`data/processed/model/rq5_national_range.csv` and is not for publication.*

The high case exceeds total national petrol supply (NMDPRA, Oct 2025), which is impossible. Under plan 5.10 and the safe-claim rules, **no national total is
published**. The range also spans two orders of magnitude. Only the central case falls within the 35%
plausibility limit (a judgement threshold stated in this phase; see `docs/parameters.md` §5).

## 4. Surprising or inconsistent points to review in Phase 4

1. **No crossover inside the window (central).** The research question assumed a crossover
   after the fuel-price shock; in the central case it had already happened by January 2023.
   The "crossover" story rests on the **robust** test and on the FX assumption (A4), which
   should be presented together.
2. **The cost-gap term G barely varies:** 88–90% in every state in May 2026. Turning such
   small differences into percentile ranks magnifies noise, so the index ordering is driven
   mainly by reliance (R) and ability to pay (A). Possible fix for an amendment: use the
   absolute monthly saving (₦) or drop G from the ranking and show it separately.
3. **A4 and pre-unification exchange rates:** the CBN official rate before June 2023 did
   not reflect import costs. Consider an amendment to use a market (parallel) rate for
   Jan–May 2023, or start the solar series in June 2023.
4. **Business full cost was not computed:** there is no source for a 20 kVA diesel
   generator price. **Household full cost** uses a constant 2026 ₦ generator price, which
   overstates early months.
5. **Solar affordability is not in an LCOE.** Household systems cost about ₦0.7 m upfront
   (0.6 kWp, 1.6 kWh LFP). Business systems cost about ₦13.4 m (17.8 kWp, 21 kWh). The
   per-kWh comparison assumes the upfront cost can be financed at the stated discount rate.
6. **Generator fuel use looks consistent with field data.** The model implies about 1.3 L
   per kWh for small petrol sets at household loads. A2EI/ZE-Gen's median (₦30,000/month in
   2024 for under 1.5 kWh/day) implies about 1.1 L/kWh.
7. **Data limits carried forward:**
   - Reliance comes from a 2018/19 survey; Borno uses a zone average (A2).
   - Tariffs for 7 states are placeholders (A1).
   - Solar resource is a long-term average, not month-specific weather.
   - Petrol prices for May 2024 and diesel for August 2023 were filled from the next NBS release.

## 5. Outputs

- `data/processed/model/`: generator, solar, crossover (plus the 2026-naira sensitivity),
  priority index, RQ5 and tornado tables.
- `data/processed/powerbi/`: `dim_state`, `dim_month`, `fact_generator_cost`,
  `fact_grid_tariff`, `fact_solar_cost`, `fact_crossover`, `fact_priority_index`.
