# Phase 2 results: data build

**DRAFT — not reviewed.** Built 2026-11-26 under `docs/analysis_plan.md` v1.0 (frozen, unchanged).
Scripts are in `src/`, outputs in `data/processed/`, hand-entered inputs in `data/manual/`,
column definitions in `docs/data_dictionary.md`, and model inputs in `docs/parameters.md`.
All 13 tests in `tests/test_data.py` pass. smedan.gov.ng and SEforALL figures were not used.

## 1. What was built

| # | Output | Coverage | Status |
|---|---|---|---|
| 1 | `fuel_prices_state_monthly.csv` | PMS and AGO, 37 states, **Jan 2023 – May 2026** (41 months, 3,034 rows) | Complete |
| 2 | `grid_tariff_disco_monthly.csv`, `grid_tariff_state_monthly.csv`, `disco_state_map.csv` | 11 DisCos, bands A–E (Non-MD), Jan 2023 – May 2026; 37 states | Complete for NERC-regulated areas; placeholders for 7 state-regulated states |
| 3 | `generator_reliance_state.csv` | NLSS 2018/19: 36 states + FCT (Borno not covered) | Complete as published; no MICS state table |
| 4 | `mpi_2022_state.csv` | MPI 2022, 37 states | Complete |
| 5 | `fx_ngn_usd_monthly.csv` | CBN official NGN/USD, Jan 2023 – Oct 2026 | Complete |
| 6 | `docs/parameters.md` | All model inputs with low/central/high and source | Complete, with gaps marked |
| 7 | `state_centroids.csv` (+ ADM1 boundaries in `data/raw/`) | 37 states | Boundaries done; **solar resource not built** (manual download needed) |

## 2. Fuel prices (NBS)

- **Sources:** 80 NBS Excel tables. E-library for Jan 2023 – Oct 2024 (one "Download Tables" file per month); microdata catalogs 157 (PMS) and 158 (AGO) from Nov 2024. Latest month is **May 2026**; June–October 2026 were not yet published.
- **Filled values (plan 5.8 rule 1 only; rules 2 and 3 were not needed):**

| Fuel | Month | States | Filled from |
|---|---|---|---|
| AGO | Aug 2023 | 37 | Previous-month column of the Sep 2023 release (no Aug 2023 file published) |
| PMS | May 2024 | 37 | Previous-month column of the Jun 2024 release (the May 2024 table link returns 404) |

- **Consistency:** each release repeats the previous month and the same month a year
  earlier. All **4,894** repeated values agree exactly with the original releases, so
  `fuel_price_revisions.csv` is empty.
- **Source problems found and handled (documented in `src/build_prices.py`):**
  - The Oct 2024 PMS workbook also contains a **diesel sheet**. It is skipped (it had
    first been read as petrol).
  - The Apr 2024 AGO table has **month labels one month behind**. Its "Feb-24" column
    equals the March release exactly, and its "Mar-24" column equals the April value in
    the May release, so the labels are shifted by +1 month.
  - The Sep 2023 AGO sheet has the state table in column F, next to a "states with
    highest/lowest prices" summary. The summary is excluded.
  - The Jan 2026 PMS zip holds a file named "JANUARY_2025"; its month is taken from the
    table contents.

## 3. Grid tariffs and DisCo-to-state map (NERC)

- **The orders are scanned images.** Tesseract OCR could read paragraph text but not the
  tariff tables (shaded cells). The tables were rendered and **transcribed by hand**
  into `data/manual/nerc_tariff_tables_transcribed.csv`, with file and page for every value.
- **Tariff path (all 11 DisCos, Non-MD):**
  - **Jan 2023 – Mar 2024:** the "Jan–Mar 2024" rates in each April 2024 order
    (Band A ₦67.48–72.67/kWh, depending on DisCo). NERC's January 2024 MYTO order (p.9)
    says tariffs were "frozen for all customers at the rates payable since December
    2022", so the same rates apply throughout 2023.
  - **Band A:** ₦225.00 in Apr 2024, ₦206.80 in May–Jun 2024, ₦209.50 from Jul 2024
    onward (June 2026 orders, Table 3).
  - **Bands B–E:** unchanged since December 2022 in every DisCo. This was checked
    between the April 2024 and June 2026 tables.
  - YEDC has no Band E.
- **Which states NERC still regulates:** taken from paragraph 15 of each June 2026 order
  (read by OCR), the list of yet-to-transition states (YTTS).
  - **Not listed (now under state regulators):** Lagos, Enugu, Imo, Ekiti, Ondo, Niger, Kogi.
  - Several states with transfer orders are **still listed under NERC** in June 2026:
    Oyo, Ogun, Plateau, Bayelsa, Nasarawa, Anambra, Gombe and Akwa Ibom. A transfer
    order is therefore not the date tariffs change.
- **Enugu:** oversight passed to EERC (order dated April 2024). From then on the state
  panel shows the EEDC NERC rate as a flagged placeholder. EERC's own tariffs were not
  collected.
- **Aba:** Aba Power (APLE) serves the Aba ring-fenced area of Abia. Its tariffs are
  cost-reflective and much higher (Band A ₦219.70, Band B ₦210.46, D/E ₦145.87 in Jan 2025),
  and are known only for Jan–Feb 2025. APLE is in the map but **not averaged** into Abia;
  Abia uses EEDC.
- **Ondo:** not in BEDC's June 2026 list, and no transfer order was found on nerc.gov.ng.
  It is flagged from Apr 2024 as "transfer date unknown".
- **Multi-DisCo states (simple mean):** Lagos (EKEDP + IE), Ogun (IBEDC + EKEDP + IE),
  Ekiti (BEDC + IBEDC), Niger (AEDC + IBEDC). Phase 0 also noted parts of Kogi served by
  IBEDC, but no order confirms this, so it is not mapped.

## 4. Generator reliance, poverty, exchange rate

- **Reliance:** published state tables of the NBS **Nigeria Living Standards Survey
  2018/19**: generator ownership (Table 7.18; national 25.0%), generator as primary
  electricity source (Table 7.10) and generator hours/day (Table 7.12; national 4.1 h).
  - Borno is not covered.
  - In Table 7.12, rows with blank cells were checked against word positions on the page.
  - **MICS 2021:** no state table was available (the S3 report link was denied), so it is
    not included.
- **MPI 2022:** all 37 states from Appendix D (pp. 122–123); population shares sum to 100.2%.
- **Exchange rate:** CBN daily official rates via the CBN website's data endpoint, averaged
  by month. The June 2023 unification shows as a jump within the month (₦461 to ₦770).
  Cross-check: NERC's May 2026 order assumed ₦1,371.8/US$; the CBN May 2026 mean is ₦1,369.49.

## 5. Gaps

1. **Solar resource by state not built.** PVGIS disallows all crawling (robots.txt), and the
   Global Solar Atlas API refuses automated access. The GSA Nigeria GIS files must be
   downloaded by hand. Zonal statistics will then also need a raster library (e.g. rasterio),
   which is not in `requirements.txt`.
2. **Tariffs of state regulators** (7 states) not collected; NERC rates are flagged placeholders.
3. **Business generator reliance:** still no source (2021 MSME tables unavailable).
4. **Weak parameter sources:** solar and battery costs are installer web pages, not an
   authoritative benchmark. Diesel generator price, business load and days of use have no source.
5. **Tesseract OCR** (installed on this machine, v5.4) was used to locate pages and read
   paragraph text. It is an external program, not a Python package.

## 6. Conflicts with the plan (no amendment applied)

| # | Plan says | What Phase 2 found | Suggested action |
|---|---|---|---|
| C1 | 5.3: use state regulator orders where states have taken over | Not collected for 7 states; NERC rates used as flagged placeholders | Collect the orders (manual list), or amend 5.3 to report these states as "NERC rate, state regulator may differ" |
| C2 | 4/5.6: reliance R = generator as **main lighting source** (NBS) or ownership (MICS/DHS) | NBS NLSS 2018/19 gives **primary electricity source** and **ownership**, not lighting; survey years differ from price months; Borno missing | Amend 5.6: R = NLSS 2018/19 generator ownership (primary-source share as sensitivity); rule for Borno (e.g. North-East zone mean, flagged) |
| C3 | 4: solar resource from Global Solar Atlas, PVGIS as check | Neither downloadable automatically | Manual GSA download; PVGIS check only by hand; add rasterio in an amendment |
| C4 | 5.4: solar costs from "at least three published 2026 benchmarks" | Several ₦ sources found, all installer or vendor pages (quality C) | Accept with ranges, or find an authoritative benchmark before Phase 3 |
| C5 | 5.2 and 5.4 parameter values | Evidence suggests a lower petrol no-load fraction, longer petrol generator life and longer battery life (`docs/parameters.md` §4) | Decide; log an amendment before any change |
| C6 | 5.8: series ends at the latest NBS month | Latest is May 2026, so tariff and FX panels are also cut at May 2026 for the model (FX file runs to Oct 2026) | None |

## 7. Files you must download by hand

1. **Global Solar Atlas, Nigeria GIS data:** monthly PV output (PVOUT) GeoTIFFs from
   https://globalsolaratlas.info/download/nigeria. Read the GSA terms (CC BY 4.0 + additions).
   Save to `data/raw/gsa/`.
2. **State regulator tariff orders**, with their effective dates: LASERC (Lagos), EERC
   (Enugu), Imo, Ekiti (ESERC), Ondo, Niger (NSERC), Kogi. Also Ondo's transfer order or
   date.
3. **MICS 2021 Survey Findings Report** (UNICEF/NBS) to check for state tables; or MICS
   2021 microdata (`HC7E`, registration).
4. **DHS 2024 household microdata** (variable `sh132n`, generator ownership), via DHS
   Program registration.
5. **Cost evidence:** an authoritative 2026 solar and battery cost benchmark, or itemised
   installer quotes (PV, battery, inverter, installation). Also dealer quotes for a 20 kVA
   diesel generator.
6. **2021 SMEDAN–NBS MSME Survey report** (from NBS or SMEDAN directly, not smedan.gov.ng).
