# Data Dictionary

**DRAFT — not reviewed.** Files in `data/processed/` are built by the scripts in `src/`.
Files in `data/manual/` are entered by hand from cited documents. The values in these
tables come from the named third-party sources; that data keeps its original terms
(see `LICENSE-DATA.md`). States use the names in `src/states.py`: 36 states plus "FCT".
Months are `YYYY-MM`.

---

## fuel_prices_state_monthly.csv — `src/build_prices.py`
NBS Price Watch monthly average retail prices by state, Jan 2023 to the latest NBS
month (May 2026 when built). One row per fuel × state × month (2 × 37 × 41 = 3,034 rows).

| Column | Description |
|---|---|
| `fuel` | `PMS` (petrol) or `AGO` (diesel) |
| `product` | Full product name |
| `state`, `month` | State and month the price refers to |
| `price_ngn_per_litre` | Average retail price, ₦ per litre (NBS) |
| `value_type` | `reported` (from that month's own release); `filled_rule1_previous_month` / `filled_rule1_year_ago` / `filled_rule1_history` (value for that month published in a later NBS release); `filled_rule2_interpolation`; `filled_rule3_national_change` (plan 5.8) |
| `is_filled` | True for any filled value |
| `source_release` | NBS release month the value was taken from |
| `source`, `source_file` | Source name and raw file (under `data/raw/nbs_prices/`) |

## fuel_price_revisions.csv — `src/build_prices.py`
Cases where a later NBS release reports a different value for a month already published.
Empty when built: all 4,894 overlapping values agreed exactly.
Columns: `fuel, state, month, current_release_price, later_release, later_role, later_price`.

## grid_tariff_disco_monthly.csv — `src/build_tariffs.py`
NERC allowed end-user tariffs for Non-MD customers by DisCo, band and month (Jan 2023 – May 2026).

| Column | Description |
|---|---|
| `disco` | AEDC, BEDC, EEDC, EKEDP, IBEDC, IE, JED, KAEDC, KEDCO, PHED, YEDC |
| `band` | Service band A–E (YEDC has A–D only) |
| `month` | Month |
| `tariff_ngn_per_kwh` | Allowed tariff, ₦/kWh (Non-MD class) |
| `basis` | `frozen_since_dec_2022`: Jan 2023 – Dec 2023 use the Jan–Mar 2024 rate, because NERC's Jan 2024 MYTO order states tariffs were frozen at December 2022 rates. `order_period`: the period stated in the order |
| `source_file`, `page` | NERC order PDF and page the value was transcribed from |

## grid_tariff_state_monthly.csv — `src/build_tariffs.py`
Tariffs mapped to states (plan 5.3).

| Column | Description |
|---|---|
| `state`, `month`, `band` | |
| `tariff_ngn_per_kwh` | Simple mean across the DisCos serving the state |
| `tariff_min`, `tariff_max` | Range across those DisCos |
| `discos`, `n_discos` | DisCos averaged (Aba Power excluded; see map) |
| `tariff_status` | `nerc_order`; `nerc_rate_placeholder_state_regulated` (a state regulator has taken over and its tariff is not collected, so the NERC rate is shown as a placeholder); `nerc_rate_placeholder_transfer_date_unknown` (Ondo, from Apr 2024) |
| `basis` | As in the DisCo file |

## disco_state_map.csv — `data/manual/disco_state_map.csv` (copied with a flag by `src/build_tariffs.py`)

| Column | Description |
|---|---|
| `state`, `disco` | One row per DisCo serving a state |
| `coverage` | `whole` or `part` |
| `regulator_from` | Month of NERC's transfer-of-oversight order to a state regulator (`unknown` for Ondo; blank if none) |
| `regulator` | NERC or the state regulator named |
| `source`, `note` | Order(s) used, e.g. "June 2026 order para 15" (the list of yet-to-transition states, YTTS) |
| `in_nerc_ytts_jun2026` | State still listed under NERC in the June 2026 orders |

## nerc_tariff_tables_transcribed.csv — `data/manual/` (hand-entered)
Tariff tables transcribed from rendered pages of scanned NERC orders (OCR could not read
the tables). One row per DisCo × class × period. Columns: `disco, tariff_class, band,
period_start, period_end, tariff_ngn_per_kwh, source_file, source_url, page, table, note`.
Sources: the April 2024 Supplementary Orders (Table 2, Jan–Mar 2024 column) and the June
2026 orders (Table 3) for 11 DisCos, plus Aba Power's February 2025 order.

## generator_reliance_state.csv — `src/build_reliance.py`
NBS Nigeria Living Standards Survey 2018/19, published state tables (Borno not covered).

| Column | Description |
|---|---|
| `electricity_access_pct_hh` | % of households with electricity (Table 7.10) |
| `gen_primary_source_pct_of_electrified_hh` | Generator as primary electricity source, % of households with electricity (T7.10) |
| `grid_primary_source_pct_of_electrified_hh` | National grid as primary source (T7.10) |
| `gen_primary_source_pct_of_all_hh` | Derived: access × generator share ÷ 100 |
| `gen_ownership_pct_hh` | % of all households owning a generator (Table 7.18) |
| `grid_hours_per_day`, `gen_hours_per_day`, `gen_hours_6pm_10pm` | Average hours of electricity per day by source, past 7 days (Table 7.12) |
| `data_available`, `note` | False and a note for Borno |
| `survey`, `survey_year`, `source_pages_pdf` | |

## mpi_2022_state.csv — `src/build_mpi.py`
NBS Nigeria Multidimensional Poverty Index 2022 (survey Nov 2021 – Feb 2022), Appendix D, all ages.
Columns: `mpi` (+95% CI), `headcount_pct` (H, +CI), `intensity_pct` (A, +CI),
`population_share_pct`, `poor_people_million`, `source_page_pdf`, `state_representative`
(False for Borno, per the report), `survey`, `source`.

## fx_ngn_usd_monthly.csv — `src/build_fx.py`
CBN official NGN/USD central rate, monthly mean, min and max of daily values, and
`n_days`. Covers Jan 2023 to the latest complete month. The exchange-rate windows were
unified in June 2023.

## state_centroids.csv — `src/fetch_boundaries.py`
Area-weighted centroid (`lon`, `lat`) of each state from geoBoundaries NGA ADM1 (GRID3
2022, CC BY 4.0). `source_name` is the name in the boundary file.
