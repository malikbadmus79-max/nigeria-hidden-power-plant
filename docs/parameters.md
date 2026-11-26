# Model Parameters (Phase 2)

**DRAFT — not reviewed.** Compiled 2026-11-26 under `docs/analysis_plan.md` v1.0
(section 5). This register fixes inputs **before** any cost result is computed.

**Rule:** where the evidence below points to a value different from the plan's
provisional value, the plan value stays in force. The difference is flagged
(⚑ in the "vs plan" column) and listed at the end of this file. Changing a value
requires an entry in `docs/amendments.md` first.

**Columns:** "Low / Central / High" are the numeric range of each parameter. They are
not cost cases. The plan's low-cost and high-cost scenarios (section 5.9) pick whichever
end lowers or raises cost; for example, a *longer* battery life belongs to the low-cost
case.

**Source quality:** A = official or manufacturer document read by us;
B = published study or report; C = retailer, installer or vendor web page, or a
search-result summary not checked against the original; J = judgement (no source).

## 1. Generators

### 1.1 Archetypes (plan 5.1)

| Parameter | Low | Central | High | Source | Quality | vs plan |
|---|---|---|---|---|---|---|
| Household generator size | – | 2.5 kVA (≈2.0 kW rated) | – | A2EI/ZE-Gen *Fossil Fuel Generator Insights for Nigeria* (Jan 2026), p.18: 83% of metered generators < 3 kVA, 1.5 and 3 kVA most common | B | = |
| Household average load (kW) | 0.26 | 0.40 | 0.57 | A2EI/ZE-Gen pp.24–25: off-grid households 0.26 kW, on-grid households 0.57 kW | B | = |
| Household running hours/day | 2 | 4 | 8 | NLSS 2018/19 Table 7.12: generator hours/day, national 4.1 (state range 0.9–10.0) | A | = (central supported) |
| Household running days/month | 15 | 22 | 30 | No numeric source found (A2EI reports days/month only in charts) | J | = (source pending) |
| Business generator size | – | 20 kVA prime (16 kW) | – | Matches the diesel curve available (RID 20 S) | A | = |
| Business average load (% of rated) | 25% | 40% | 60% | No source found | J | = (source pending) |
| Business running hours/day | 6 | 8 | 12 | NBS/SMEDAN MSME survey 2010, §5.1.21: 39.8% of firms use alternative power 1–5 h/day, 34.9% 6–10 h, 12.0% 16–20 h (national) | A (old) | = |
| Business running days/month | 22 | 26 | 30 | No source found | J | = (source pending) |

### 1.2 Fuel use

**Diesel 20 kVA (prime, 50 Hz), L/h at load fraction.** Linear interpolation between points (plan 5.2).

| Load | 25% | 50% | 75% | 100% | Source |
|---|---|---|---|---|---|
| Central | 1.9 | 2.9 | 4.2 | 5.8 | RID 20 S-Series datasheet, as recorded in `nigeria-emission-factors/docs/phase0_results.md` §4 (A) |
| Low (central −5%) | 1.81 | 2.76 | 3.99 | 5.51 | Manufacturer tolerance band; Cummins sheets state "+5%" fuel tolerance (A); symmetric use is J |
| High (central +15%) | 2.19 | 3.34 | 4.83 | 6.67 | Allowance for age and poor maintenance (J) |

Cross-check: Cummins 4BTAA3.3-G14 engine (≈61 kVA set) 4/8/11/15 L/h at 25/50/75/100%, so 25% load uses 27% of full-load fuel. RID 20 kVA uses 33%. (A)

**Petrol 2.5 kVA household set.** Straight-line model `F = F_rated × (a + (1 − a) × load/rated)` (plan 5.2).

| Parameter | Low | Central | High | Source / derivation | Quality | vs plan |
|---|---|---|---|---|---|---|
| `F_rated`, L/h at ≈2.0 kW | 1.0 | 1.2 | 1.4 | Honda EU70is: 19.2 L tank / 6.5 h at 5.5 kW rated = 0.54 L/kWh → 1.07 L/h at 2.0 kW (inverter, efficient: low end) (A, derived). Retail claims for 2.5 kVA Sumec Firman: 0.8–1.0 L/h at 50% load → 1.1–1.4 L/h at rated if a = 0.4 (C) | C | new (plan said "set in Phase 2") |
| `a`, no-load fuel fraction | 0.15 | 0.30 | 0.45 | *Amendment A3* (was 0.30/0.40/0.55). Evidence: Honda EU70is with eco-throttle implies a ≈ 0.15 (25%-load run time 18 h vs 6.5 h rated) (A, derived); one calculator rule uses 0.13 (C); diesel spec sheets imply a ≈ 0.02–0.10 (A); anecdotal forum report of fuel use "flat-lining" below ~20% load on fixed-speed petrol sets (C) | C/J | A3 |

Plausibility check (no results computed): with the pre-A3 central `a` = 0.40, 1.2 × (0.40 + 0.60 × 0.20) = 0.62 L/h, about 55 L/month at 4 h/day × 22 days. With A3 (`a` = 0.30): 1.2 × (0.30 + 0.70 × 0.20) = 0.53 L/h, about 47 L/month. A2EI/ZE-Gen report a median monthly fuel spend of ₦30,000 when petrol cost ₦617–1,060/L in 2024 (≈ 28–49 L/month). The central case is therefore on the high side.

### 1.3 Maintenance and purchase

| Parameter | Low | Central | High | Source | Quality | vs plan |
|---|---|---|---|---|---|---|
| Petrol maintenance, % of fuel cost | 10% | 15% | 25% | A2EI/ZE-Gen p.20: median repair ₦5,000 vs median fuel ₦30,000 per month (≈17%) | B | = |
| Diesel maintenance, % of fuel cost | 5% | 10% | 15% | No source found | J | = (source pending) |
| Petrol 2.5–3.5 kVA purchase price (2026) | ₦265,000 | ₦280,000 | ₦380,000 | Retail comparison (Oct 2026): Sumec Firman 3–3.5 kVA ₦265k–295k; Elepaq SV5800/EC5800CX ₦310k–380k | C | new |
| Petrol generator life (years) | 3 | 5 | 8 | *Amendment A3* (was 2/3/5). A2EI/ZE-Gen p.18: 50% of generators bought 4–10 years ago | B/J | A3 |
| Diesel 20 kVA purchase price | – | – | – | Not found; needs dealer quotes (manual) | – | gap |
| Diesel generator life (years) | 6 | 8 | 12 | No source found | J | = (source pending) |

## 2. Solar + battery

| Parameter | Low | Central | High | Source | Quality | vs plan |
|---|---|---|---|---|---|---|
| PV modules, ₦/Wp (2026) | 190 | 260 | 350 | Solar Builders NG (checked Oct 2026): Tier-1 mono/bifacial ₦190–260/Wp; Nigeria Building Cost: ~₦350/W | C | new |
| LFP battery, ₦/kWh (2026) | 160,000 | 255,000 | 300,000 | Skillnaija: 5 kWh ₦0.8–1.5m, 10 kWh ₦1.5–2.8m (₦160–300k/kWh); Solar Builders NG: 5.12 kWh LiFePO4 ≈ ₦1.31m (≈₦255k/kWh). Outlier excluded: Afrotools ₦70–120k/kWh | C | new |
| Balance of system + installation (excl. inverter, A8) | 20% | 30% | 40% of PV + battery cost | No itemised source; full-system quotes (Voltage Africa: 1 kWp ₦0.9–2m, 5 kWp ₦4.5–9m; Solar Builders NG: 5 kVA/10 kWh ₦4.65–8.5m) to be used to check the total | J/C | new ⚑ weak |
| Inverter, household 1 kVA (₦, 2026) | 120,000 | 175,000 | 300,000 | *Amendment A8*. Nov 2026 price survey: new 1 kVA inverters ₦150k–205k (solarinverter.ng); other guides ₦120k–300k (solarinverterinstallation.com) | C | A8 |
| Inverter, business 20 kW (₦, 2026) | 2,800,000 | 3,500,000 | 4,200,000 | *Amendment A8*. Deye 20 kW three-phase hybrid listed at ₦3,498,750 (retailer, Nov 2026); ±20% (J) | C/J | A8 |
| Cost benchmarks before 2026 | – | Constant US$ price | – | *Amendment A4*: 2026 ₦ benchmarks converted to US$ at the CBN October 2026 average, then to ₦ for each month at that month's CBN rate | J | A4 |
| Night share of energy (household) | 0.5 | 0.7 | 0.9 | A2EI/ZE-Gen: households use generators more in the evening (qualitative); NLSS Table 7.12: national generator use 2.7 h in 6pm–10pm out of 4.1 h/day (≈0.66) | A/B | = (central supported) |
| Night share (business) | 0.1 | 0.3 | 0.5 | A2EI/ZE-Gen: businesses draw power mainly in daytime (qualitative) | B/J | = |
| Battery depth of discharge (LFP) | – | 0.8 | – | Vendor cycle-life tables are rated at 80% DoD (Portlandia Electric; Anern) | C | = |
| Battery round-trip efficiency | – | 0.90 | – | Typical LFP value (vendor sources) | C/J | = |
| Extra PV derate (small systems, soiling) | – | 0.9 | – | Plan assumption | J | = |
| PV output `PVOUT_min` by state | – | – | – | Global Solar Atlas monthly PVOUT, **not yet downloaded** (manual; see `docs/phase2_results.md`) | – | gap |
| Analysis horizon | – | 10 years | – | Plan | J | = |
| LFP battery life (years) | 8 | 10 | 15 | *Amendment A3* (was 6/8/10). Vendor sources: daily-cycled LFP lasts about 8–15 years; ~6,000 cycles at 80% DoD ≈ 16 years at 1 cycle/day (Portlandia Electric); 5,000 cycles (Anern) | C | A3 |
| Lead-acid battery life (separate case) | – | 3 years | – | Plan | J | = |
| Real discount rate | 10% | 15% | 25% | Plan judgement; no source | J | = |
| O&M, % of capital per year | 0.5% | 1% | 2% | Plan judgement | J | = |

## 3. Emission factors and fuel properties

From the 2006 IPCC Guidelines Vol. 2 (as recorded in `nigeria-emission-factors/docs/phase0_results.md` §6) (A).

| Parameter | Petrol (Motor Gasoline) | Diesel (Gas/Diesel Oil) | Table |
|---|---|---|---|
| CO2, kg/TJ | 69,300 (67,500–73,000) | 74,100 (72,600–74,800) | Ch.1 Table 1.4 |
| NCV, TJ/Gg | 44.3 (42.5–44.8) | 43.0 (41.4–43.3) | Ch.1 Table 1.2 |
| CH4 / N2O, stationary residential & commercial, kg/TJ | 10 / 0.6 | 10 / 0.6 | Ch.2 Tables 2.4, 2.5 |
| CH4 / N2O, off-road household (sensitivity), kg/TJ | 120 / 2 (4-stroke) | 4.15 / 28.6 | Ch.3 Table 3.3.1 |

| Fuel density (kg/L at 15 °C) | Low | Central | High | Source | Quality |
|---|---|---|---|---|---|
| Petrol | 0.720 | 0.745 | 0.775 | EN 228 specification range; Nigerian (SON/NMDPRA) specification **not checked** | C/J |
| Diesel | 0.820 | 0.840 | 0.850 | EN 590 range 0.820–0.845; Cummins fuel-data basis 0.85 | A/C |

## 4. Values that differ from the plan

Items 1–3 were adopted by Amendment A3 (2026-11-26); item 4 remains a judgement value.


1. **Petrol no-load fraction `a`:** evidence suggests lower values (about 0.15–0.30) than the plan's central 0.40.
   With the central `F_rated`, the plan values overstate household fuel use against the
   A2EI/ZE-Gen spending median. Proposed amendment: low 0.15 / central 0.30 / high 0.45.
2. **Petrol generator life:** survey age data suggest longer than 3 years. Proposed: 3 / 5 / 8.
3. **LFP battery life:** vendor data suggest 8–15 years. Proposed: 8 / 10 / 15 (one replacement only in the low case).
4. **Inverter + balance of system + installation:** a judgement share. Should be replaced by itemised quotes before Phase 3.

Values marked "source pending" or "gap" must be filled, or confirmed as judgement, before Phase 3.

## 5. Values added in Phase 3 (judgement; stated before results were reviewed)

| Parameter | Low | Central | High | Source | Quality |
|---|---|---|---|---|---|
| Persons per household (RQ5) | 5.5 | 5.0 | 4.5 | No source collected; fewer persons means more households (high case) | J |
| Population by state (RQ5) | – | MPI 2022: poor people ÷ headcount ratio | – | NBS MPI 2022 Appendix D (derived) | A (derived) |
| National petrol volume (RQ5 check) | – | 56.74 million L/day (Oct 2025) | – | NMDPRA Fact Sheet Oct 2025, p.4 | A |
| Plausible maximum share of national petrol used by household generators (plan 5.10) | – | 35% | – | Not stated in Phase 2 as the plan required; set now as judgement (vehicles take most petrol) | J |
| Generator purchase price over time | – | 2026 ₦ price held constant | – | A4 covers solar only; generator prices are not FX-scaled (flagged) | J |
| Benchmark month for A4 conversion | – | Oct 2026 (CBN mean ₦1,338.49/US$) | – | Month the 2026 ₦ solar price pages were checked | J |
