# Analysis Plan — Where Solar Beats the Generator: Nigeria, State by State, Month by Month (2023–2026)

**Version 1.0 · DRAFT** (draft until the Phase 4 audit is complete)

Once frozen (`docs/plan_freeze.md`), any change to this plan is logged in
`docs/amendments.md` before it is applied. Context: `docs/phase0_results.md`.

---

## 1. Problem and objective

**Problem.** Since the removal of the petrol subsidy in mid-2023, petrol and diesel prices
in Nigeria have changed sharply and differ from state to state. Electricity tariffs have
also changed (for example, the Band A changes from 2024). Many households and small
businesses still rely on generators. No public source compares, for each state and each
month, the cost of power from a generator with the grid tariff and with solar plus battery.

**Objective.** Build an open, dated, state-by-state and month-by-month cost comparison
(January 2023 to the latest NBS price month) for two typical users, and publish it as a
Power BI dashboard showing where and when solar plus battery became cheaper than a
generator. All outputs are estimates with low/central/high ranges.

## 2. Research questions

- **RQ1 — Generator cost.** What is the monthly cost, in ₦/day and ₦/kWh, of running
  (a) a typical household generator (small petrol) and (b) a typical small-business
  generator (diesel) in each of the 36 states and the FCT, from January 2023 to the latest
  NBS month?
- **RQ2 — Comparison.** How does that cost compare with (a) grid tariffs by DisCo and band,
  mapped to states, and (b) the levelised cost of solar plus battery, adjusted for each
  state's solar resource?
- **RQ3 — Payback and affordability.** *(A5)* For each state, month and user type, how many
  months of fuel and maintenance savings repay the upfront cost of solar plus battery, and
  how large is that upfront cost relative to monthly household consumption in the state?
  (The earlier crossover-month result is kept as a supporting table.)
- **RQ4 — Market priority.** Which states rank highest on a market priority index combining
  generator reliance, the monthly saving from switching *(A6)*, and ability to pay?
- **RQ5 (optional, range only).** What are the indicative national household generator
  fuel spend and CO2 emissions, checked top-down against NMDPRA national fuel volumes?

## 3. Scope

**In scope**
- 36 states + FCT, monthly, January 2023 to the latest NBS month (May 2026 at Phase 0).
  *(A7)* Solar cost, payback, affordability and crossover start in June 2023; generator costs
  and grid tariffs start in January 2023.
- Two user archetypes: household on a small petrol generator, and small business on a
  small diesel generator.
- Running cost and full cost (including the generator's purchase price) of the generator,
  grid tariffs by band, and solar plus battery LCOE.
- National household fuel spend and CO2, only as indicative ranges (RQ5).

**Out of scope**
- Exact national generator fleet totals.
- Large industrial and commercial generators (above about 50 kVA).
- Business generator ownership by state (no usable source; see Phase 0, item 3).
- Health and air-quality effects.
- Any figure from SEforALL "Beyond Gensets" without written permission from SEforALL.
- Grid reliability modelling (hours of supply by state are not published).

## 4. Data per research question

| RQ | Data | Source | Notes |
|---|---|---|---|
| RQ1 | Monthly petrol (PMS) and diesel (AGO) retail prices by state | NBS Price Watch (e-library to Oct 2024; microdata catalogs 157/158 from Nov 2024) | Jan 2023 – latest month; AGO Aug 2023 gap (see 5.8) |
| RQ1 | Diesel generator fuel curves | Manufacturer spec sheets (25/50/75/100% load), as collected in `nigeria-emission-factors` | e.g. 20 kVA: 1.9/2.9/4.2/5.8 L/h |
| RQ1 | Petrol generator fuel use | Published small-engine studies and manufacturer run-time data, used as a range | No load curves exist for common Nigerian 1–3.5 kVA brands |
| RQ1 | Usage (load, hours, days) | A2EI/ZE-Gen smart-meter study (Jan 2026); other published field studies | Published aggregates only |
| RQ1 | Maintenance | A2EI/ZE-Gen survey (median repair vs fuel cost); published sources | |
| RQ2 | Grid tariffs by DisCo, band and month | NERC monthly MYTO / supplementary orders per DisCo; state regulator orders where states have taken over | ₦/kWh by band A–E |
| RQ2 | DisCo-to-state mapping | NERC licence areas; Phase 0 table, verified in Phase 2 | Dated mapping |
| RQ2 | Solar resource by state | Global Solar Atlas (PV output, annual and monthly); PVGIS monthly as a check | CC BY 4.0; GSA extra terms |
| RQ2 | State boundaries | An admin-1 boundary dataset with an open licence (chosen in Phase 2) | For zonal statistics |
| RQ2 | Solar + battery costs | At least three published 2026 cost benchmarks (installed ₦ or US$ per kWp and per kWh storage) | Range, not a single source |
| RQ2 | Exchange rate (if benchmarks are in US$) | CBN official monthly average rate | Needed to convert US$ costs to ₦ by month |
| RQ4 | Generator reliance by state | NBS survey tables: main source of lighting by state (generator share); MICS 2021 generator ownership (`HC7E`) if available; DHS 2024 (`sh132n`) if microdata access is granted | Survey years differ from price months |
| RQ4 | Ability to pay | NBS Multidimensional Poverty Index 2022 (state headcount ratio) | |
| RQ5 | Households per state | NPC/NBS population and household projections (chosen in Phase 2) | |
| RQ5 | National fuel volumes | NMDPRA monthly Fact Sheets (truck-out, national) | From about late 2024 |
| RQ5 | Emission factors | IPCC 2006 Vol. 2 (CO2: Table 1.4; CH4/N2O: Tables 2.4/2.5 and 3.3.1) | Fuel density from a cited source |

**Not to be used:** smedan.gov.ng (appeared compromised at Phase 0), and SEforALL "Beyond
Gensets" figures without permission.

## 5. Methods

All parameters below have a low, central and high value. Provisional values are given
here. During Phase 2 they are confirmed or revised against cited sources and recorded in
`docs/parameters.md` **before any cost result is computed**. Any change from the values
below is logged in `docs/amendments.md`.

### 5.1 User archetypes

| Parameter | Household (petrol) | Small business (diesel) |
|---|---|---|
| Generator size | 2.5 kVA (≈2.0 kW rated) | 20 kVA prime (16 kW) |
| Average load while running (kW) | low 0.26 / central 0.40 / high 0.57 | low 4.0 (25%) / central 6.4 (40%) / high 9.6 (60%) |
| Running hours per day | low 2 / central 4 / high 8 | low 6 / central 8 / high 12 |
| Running days per month | low 15 / central 22 / high 30 | low 22 / central 26 / high 30 |

The household loads follow the A2EI/ZE-Gen published averages (off-grid households 0.26 kW,
on-grid households 0.57 kW). The 2.5 kVA size reflects A2EI's finding that 83% of metered
generators are under 3 kVA. The business archetype follows the diesel spec-sheet curve
available for 20 kVA.

### 5.2 Generator cost (RQ1)

For state *s*, month *m* and user *u*:

- **Fuel use per running hour:** `F(L/h) = f(load / rated)`.
  - **Diesel:** linear interpolation between the published 25/50/75/100% points.
  - **Petrol:** a straight-line fuel model `F = F_rated × (a + (1 − a) × load/rated)`, where
    `a` is the no-load fuel fraction. *(A3)* Values: low 0.15 / central 0.30 / high 0.45,
    with `F_rated` set from published small-engine data in Phase 2.
- **Daily fuel cost:** `C_fuel = F × hours × P_fuel(s, m)`, where `P_fuel` is the NBS state
  price (₦/L).
- **Maintenance allowance:** a share of fuel cost.
  - Petrol: low 10% / central 15% / high 25%. The A2EI/ZE-Gen median repair cost (₦5,000) was
    about 17% of the median fuel cost (₦30,000) per month.
  - Diesel: low 5% / central 10% / high 15%.
- **Running cost per day** = `C_fuel × (1 + maintenance share)`.
- **Full cost per day** = running cost + annualised purchase price ÷ 365. Purchase price and
  life are set in Phase 2 from cited market prices. *(A3)* Petrol generator life 3 / 5 / 8
  years (low / central / high); diesel about 8 years.
- **Cost per kWh** = daily cost ÷ (average load × hours).
- **Monthly cost** = daily cost × running days.

### 5.3 Grid tariff (RQ2a)

- ₦/kWh tariff for each DisCo, band (A–E) and month, from NERC orders. Where a state
  regulator has taken over tariff setting, that regulator's order is used from the date it
  applies.
- Mapped to states with the dated DisCo-to-state table. For states served by more than one
  DisCo (e.g. Lagos: Eko and Ikeja), both values are shown, and a simple mean is used for the
  state-level view.
- The grid is shown as a **price reference** only. Supply hours are not modelled, so the
  comparison does not imply the grid is available when needed.
- *(A1)* For the 7 states whose tariff oversight has passed to a state regulator (Lagos,
  Enugu, Imo, Ekiti, Ondo, Niger, Kogi), the NERC DisCo tariff is used as a **flagged
  placeholder** from the month the regulator took over (Ondo: from April 2024, transfer
  date unknown). The state regulator's own tariff may differ. Aba Power (APLE) is kept
  separate and not averaged into Abia.

### 5.4 Solar + battery LCOE (RQ2b)

Each system is sized to deliver the same daily energy `E` as the generator archetype.

- **Night share** (energy used without sun, served from battery): household low 0.5 /
  central 0.7 / high 0.9; business low 0.1 / central 0.3 / high 0.5.
- **Battery capacity** = `E × night share / (depth of discharge × round-trip efficiency)`,
  with LFP depth of discharge 0.8 and round-trip efficiency 0.90.
- **PV size (kWp)** = `(E × (1 − night share) + E × night share / RTE) / (PVOUT_min × 0.9)`.
  - `PVOUT_min` is the state's lowest monthly specific PV output (kWh/kWp/day) from the Global
    Solar Atlas. This is a conservative sizing choice.
  - 0.9 is an extra derate for small-system losses and soiling.
- **Capital cost** = PV kWp × ₦/kWp + battery kWh × ₦/kWh + inverter and installation, from
  the 2026 benchmark range. *(A8)* The inverter is costed explicitly per system (household
  1 kVA: ₦120k / 175k / 300k; business 20 kW: ₦2.8m / 3.5m / 4.2m). A balance-of-system
  share of 20 / 30 / 40% of PV + battery covers cabling, mounting and installation.
  - *(A4)* The 2026 ₦ benchmarks are converted to US$ at the CBN average rate of the
    benchmark month (October 2026) and back to ₦ for each model month at that month's CBN
    rate (constant US$ equipment price assumption, flagged).
- **Analysis horizon:** 10 years. PV and inverter are assumed to last at least 10 years.
- **Battery replacement:** *(A3)* LFP battery life 15 years (low-cost case, no replacement) /
  central 10 years (no replacement within the 10-year horizon) / 8 years (high-cost case, one
  replacement). A lead-acid battery (replacement every 3 years) is a separate high-cost case.
- **Real discount rate:** low 10% / central 15% / high 25%.
- **O&M:** 1% of capital cost per year (range 0.5–2%).
- **LCOE** = (capital cost + present value of battery replacement + present value of O&M)
  ÷ present value of energy delivered over 10 years. It is reported in ₦/kWh and converted
  to ₦/day and ₦/month for the archetype.

### 5.5 Payback and affordability (RQ3, A5)

- **Upfront cost:** the solar + battery capital cost from 5.4 (PV, battery, inverter and
  installation), sized for the archetype's daily energy.
- **Monthly saving:** the generator's fuel + maintenance cost for the same monthly energy
  (central usage: average load × hours × days), minus solar O&M per month.
- **Payback (months)** = upfront cost ÷ monthly saving. It is simple (undiscounted) and
  excludes battery replacement. "No payback" if the saving is ≤ 0.
  - Low (shortest): solar low-cost upfront cost ÷ saving with the generator's high-cost case.
  - Central: both central.
  - High (longest): solar high-cost upfront cost ÷ saving with the generator's low-cost case.
- **Affordability (households):** upfront cost ÷ monthly household consumption in the state.
  Consumption = NBS *Consumption Expenditure Pattern in Nigeria 2019*, Table 12 (total
  household expenditure by state) ÷ number of households (MPI 2022 population ÷ household
  size), ÷ 12. It is brought to each month with the NBS all-items CPI (old base chained
  to the 2024 = 100 series over their 2023–2024 overlap). Flagged as approximate. No
  business equivalent exists.
- **Supporting table:** the crossover rule below is kept, as a supporting result only.

**Crossover (supporting table)**

- **Comparison basis:** solar plus battery LCOE (central) against the generator's **running
  cost** (central). This is the switching decision for someone who already owns a generator,
  and it is the conservative test for solar. The full-cost comparison is shown alongside.
- **Crossover month:** the first month in which the generator running cost is above the solar
  LCOE **and stays above for at least 3 consecutive months**.
- **Robust crossover:** the first month in which the generator's *low* case is above solar's
  *high* case for 3 consecutive months.
- If neither condition is met by the latest month, the result is reported as "not yet".

### 5.6 Market priority index (RQ4) — weights fixed now

Three components per state, each converted to a **percentile rank** across the 37 states
(1/37 to 1), so that no component becomes zero:
- **R, generator reliance:** *(A2)* share of all households using a generator as their
  primary electricity source (NBS NLSS 2018/19, Table 7.10: access × generator share). The
  generator ownership share (NLSS Table 7.18) is used as a sensitivity. Borno, not covered
  by NLSS, takes the North-East zone average (Adamawa, Bauchi, Gombe, Taraba, Yobe) and is
  flagged. The source is named in the output.
- **G, saving:** *(A6)* the monthly ₦ saving from switching to solar + battery (5.5), for the
  latest month, household archetype, central case. Negative values are set to 0 before
  ranking.
- **A, ability to pay:** 1 − MPI 2022 headcount ratio.

**Index** = R^(1/3) × G^(1/3) × A^(1/3), a geometric mean with **equal weights**.

**Sensitivity:**
- reliance-led weights (0.5 / 0.25 / 0.25);
- gap-led weights (0.25 / 0.5 / 0.25);
- the business archetype instead of the household for G.

States are shown as ranks and in five groups, not as precise scores.

### 5.7 DisCo-to-state mapping

The Phase 0 table is verified against NERC licence-area documents and state regulator
orders in Phase 2, and stored as `data/processed/disco_state_map.csv` with valid-from dates.
States split across DisCos list each DisCo.

### 5.8 Gap-filling for missing price months

Applied in this order, and each filled value is flagged in the data:
1. Use the value for the missing month that appears in a later NBS release, from the
   previous-month column or the year-ago column.
2. Otherwise, interpolate linearly within the state between the adjacent months, for gaps of
   up to 2 months.
3. Otherwise, apply the national month-on-month change to the state's last known value.

The series ends at the latest published NBS month and is not extrapolated forward.

### 5.9 Sensitivity cases

- **Low:** all generator parameters at their low-cost end, and solar at its high-cost end.
- **High:** the opposite.
- **Central:** central values throughout.

The dashboard shows central values with the low–high band. A one-at-a-time sensitivity
(tornado) chart is produced for the latest month for one representative state per
geopolitical zone.

### 5.10 RQ5 (optional): national household spend and CO2

- **Spend** = Σ over states of households × generator reliance share × archetype monthly
  running cost. *(A2)* Reliance here uses the NLSS ownership share (high) and the
  primary-source share (low). It is reported only as a low–high range.
- **CO2** = litres × density × NCV × IPCC CO2 factor. CH4 and N2O are reported in a sensitivity
  using both the stationary and the off-road factors.
- **Top-down check:** the implied household generator petrol volume is compared with NMDPRA
  national PMS truck-out. If the range exceeds a plausible share (to be stated in Phase 2,
  allowing for vehicle use), the RQ5 result is reported as "not consistent with national
  supply" rather than published as a total.

## 6. Phases

| Phase | Work | Main outputs |
|---|---|---|
| 0 (done) | Data availability check | `docs/phase0_results.md` |
| 1 (this) | Analysis plan and freeze | `docs/analysis_plan.md`, `docs/plan_freeze.md`, `docs/amendments.md` |
| 2 | Data build | Clean state price panel, tariff panel, DisCo-to-state map, solar resource by state, survey reliance and MPI tables, solar cost benchmarks, `docs/parameters.md`, data dictionary, tests |
| 3 | Cost model and crossover | Generator, grid and solar cost series (low/central/high), crossover months, priority index, sensitivity charts |
| 4 | Audit | Independent re-check of a sample of states and months, formula review, source checks, corrections log; DRAFT label removed only after this phase |
| 5 | Power BI dashboard | Dashboard built from `data/processed/` CSVs (`.pbix` kept out of git) |
| 6 | Communication | Post, carousel and short methods note, all following section 7 |

## 7. Safe-claim rules (binding)

1. **Estimates with ranges.** Every figure is an estimate and is shown with its low–high range
   or labelled as central.
2. **Dated and sourced.** Every figure states the month it refers to and its sources.
3. **No blame.** No company, DisCo, regulator or brand is blamed or accused. Differences
   are described, not judged.
4. **National totals only as indicative ranges.** National spend or emissions (RQ5) are shown
   only as ranges and labelled indicative.
5. **No SEforALL figures without permission.**
6. **DRAFT until the Phase 4 audit.**

## 8. Limits and what would change the plan

**Limits**
- **Prices:** NBS prices are state averages and do not show variation within a state or
  queue-related price spikes.
- **Ownership vs use:** generator reliance comes from surveys taken in different years from
  the price months, and ownership or main lighting source is not the same as use.
- **Petrol fuel use** is the least certain input (no load curves for common brands); this is
  why the ranges are wide.
- **Usage patterns** come from published aggregates (A2EI/ZE-Gen), not state-specific data.
- **Grid:** tariffs are not the same as bills (estimated billing, unmetered customers), and
  supply hours are not modelled.
- **Solar costs** vary with quality, financing and installer, so benchmarks are ranges. Pre-2026
  months depend on the exchange-rate conversion.
- **DisCo boundaries** do not follow state lines and are changing under the Electricity Act 2023.

**What would change the plan** (logged in `docs/amendments.md` first)
- Access to DHS 2024 or MICS 2021 microdata: generator ownership by state would replace or
  complement main lighting source.
- Obtaining the 2021 MSME survey tables: business reliance by state could enter RQ4.
- SEforALL permission: Lagos figures could be used as an external check.
- Published state-level supply hours: grid reliability could be added to RQ2.
- NBS stopping or changing the price series, or major gaps.
- More states taking over tariff setting: the tariff source would become state regulators.
- New published small petrol generator fuel data: the petrol fuel model would change.
- Audit findings in Phase 4.
