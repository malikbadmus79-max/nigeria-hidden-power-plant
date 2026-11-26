# Phase 0 results: data availability check

**DRAFT — not reviewed.** Checked on 2026-11-26. Downloaded files are listed in
`docs/sources/README.md` with URL and access date; third-party files stay in gitignored
folders. Figures quoted below are as published by the named source and have not been
checked independently.

## Summary

| # | Item | Best source found | Years | State-level | Time step | Licence | Rating |
|---|---|---|---|---|---|---|---|
| 1 | Petrol and diesel prices by state | NBS PMS and AGO Price Watch | Jan 2023 – May 2026 | **Yes** (36 + FCT) | Monthly | None stated (NBS publication) | **Green** |
| 2 | Household generator ownership | DHS 2024 (fieldwork Dec 2023–May 2024) microdata; MICS 2021 | 2021, 2024 | Yes, from microdata only | One-off surveys | DHS/MICS data terms (registration) | **Amber** |
| 3 | Business generator use | SMEDAN–NBS MSME Survey 2021 | 2021 | Unknown (report not obtained) | One-off | Unknown | **Red** |
| 4 | National petrol and diesel consumption | NMDPRA monthly Fact Sheets | late 2024 onward (found) | No | Monthly | None stated | **Amber** |
| 5 | DisCo supply and reliability + DisCo-to-state map | NERC quarterly reports, monthly DisCo orders | 2025–2026 | DisCo-level only | Quarterly (Band A feeders monthly) | None stated (© NERC) | **Amber** |
| 6 | SEforALL "Beyond Gensets" (Lagos) | SEforALL / Lagos State report, Oct 2024 | 2024 | Lagos only | One-off | **"Confidential — do not cite without permission"** | **Amber** |
| 7 | "₦7.6 trillion" petrol generator spend | Traced to SEforALL, which cites A2EI–Dalberg 2019 and REA/Vista 2022 | pre-2023 | No | – | – | **Red** (as calibration) |
| 8 | Solar resource by state | Global Solar Atlas; PVGIS | Long-term average | Via zonal statistics | Annual / monthly averages | CC BY 4.0 (GSA with extra terms) | **Green** |
| 9 | Poverty by state | NBS Multidimensional Poverty Index 2022 | 2021/22 | **Yes** | One-off | None stated (NBS publication) | **Green** |
| 10 | Generator fuel curves, IPCC factors | Reused from `nigeria-emission-factors` Phase 0 | – | – | – | – | Diesel **Green**, petrol **Red/Amber** |

---

## 1. Petrol (PMS) and diesel (AGO) prices by state — Green

**What exists:** NBS monthly "Price Watch" reports give the average retail price per litre
for each of the 36 states and the FCT, plus zonal and national averages.
- **Jan 2023 – Oct 2024:** NBS e-library (nigerianstat.gov.ng/elibrary), one report per month.
- **Nov 2024 – May 2026:** NBS microdata catalog: PMS is catalog 157, AGO is catalog 158.
  Each month is a PDF report plus an Excel state table, sometimes zipped together.
  Downloads need **no login**.
- Each state table also repeats the previous month and the same month a year earlier.
  For example, the March 2026 PMS table has columns for Mar 2025, Feb 2026 and Mar 2026.
  A sample is in `data/raw/nbs_prices/PMS_2026-03/`.

**Missing months**
| Series | Not found | Note |
|---|---|---|
| PMS | none for Jan 2023 – May 2026 | Aug and Sep 2025 were released as one combined report, but each has its own Excel table |
| AGO | **Aug 2023** (not found in e-library) | Can likely be recovered from the Sep 2023 report (previous-month column) or the Aug 2024 report (year-ago column) |
| Both | **Jun – Oct 2026** | Not yet published as of 2026-11-26. NBS's release calendar lists them, but the files are not in the catalog. |

**Licence:** no licence is stated on the catalog pages. These are public NBS statistics, so
cite NBS.

**Risks:** the method behind the price collection (outlets, number of quotes per state) needs
reading. Press reports disagree on some national figures (e.g. AGO November 2025: ₦1,409.61
vs ₦1,531.34), so always use the NBS file itself. The 2023–24 e-library format (PDF only, or
with tables) has not yet been checked.

## 2. Household generator ownership by state — Amber

| Survey | Variable | Year | Published state table? | Access |
|---|---|---|---|---|
| **DHS 2024** (often called 2023-24; fieldwork Dec 2023 – May 2024) | `sh132n` "Household has: generator" | 2024 | **No.** The final report (FR395, Table 2.5) gives only national 22.5%, urban 32.9%, rural 11.7%. The KIR (PR157) has no generator item. | Household recode microdata: DHS Program registration with a short project description. Also listed in World Bank Microdata Library catalog 8029 (access terms to check). |
| **MICS 2021** | `HC7E` "Household has: generator" | 2021 | Not confirmed. National about 22.4% per the catalog tabulation; the sample is designed for 37 strata (states + FCT). | Microdata: UNICEF MICS / World Bank catalog 5959, registration |
| NLSS 2018-19 | Electricity source incl. generator (**not** ownership) | 2018/19 | From microdata | NBS NADA catalog 68 |
| GHS-Panel Wave 5 | Household assets (Table 3.15) | 2023/24 | No. Urban/rural only, and the panel is **not designed for state estimates** | World Bank catalog 6410 |

**Risks:** ownership is not the same as use or size. DHS samples about 1,000 households per
state, so state estimates will have wide confidence intervals. The DHS and MICS items match,
but NLSS measures something different.

## 3. Business generator use by state — Red

- **2021 SMEDAN–NBS MSME Survey: not obtained.**
  - The NBS file `pdfuploads/MSMES.pdf` turned out to be the **2010** survey (published 2012).
    It reports daily hours of "alternative source of power" use: 39.8% of firms use it 1–5 h/day,
    34.9% 6–10 h and 12.0% 16–20 h. These figures are national and by sector, **not by state**.
  - The NBS e-library has MSME surveys for 2010, 2013/14 and 2017, but not 2021.
  - **smedan.gov.ng appears to be compromised:** its robots.txt shows a hacker group's defacement
    text. Nothing was downloaded from it, and it should not be used until fixed.
- SEforALL used the 2021 survey's count of Lagos MSMEs (80,072), so the report exists. Its
  energy tables and state breakdown are unverified.

**Risks:** without the 2021 tables, business generator use by state has no source. The
2017 NBS MSME survey is a possible fallback to check.

## 4. National petrol and diesel consumption (NMDPRA) — Amber

**What exists:** NMDPRA's monthly "State of the Midstream and Downstream Sector" Fact Sheet
(sample: October 2025). It gives:
- average daily consumption ("truck-out") per month. October 2025: PMS 56.74 million L/day,
  AGO 17.13 million L/day, ATK 2.61 million L/day, LPG 6,095 t/day;
- daily demand benchmarks (PMS 50 million L/day, AGO 14 million L/day);
- days of fuel sufficiency;
- indicative prices for six cities;
- a chart for October 2024 – October 2025.

Press reports cite fact sheets through at least January 2026 (PMS 60.2 million L/day, AGO
19.2 million L/day).

**Gaps:** national only, **not by state**. No index of all fact sheets was found: the files
sit on an Azure blob with random names. Coverage for 2023 and early 2024 is unconfirmed. No
licence is stated.

**Risks:** truck-out is not end-use consumption. It includes vehicles, stockpiling and
cross-border leakage.
- **Cross-check issue:** SEforALL's Lagos estimate (section 6) is about 9 bn L/yr of household
  generator fuel (97.7% petrol) plus about 2.5 bn L/yr of MSME petrol.
- That is around **11.5 bn L/yr**, against national PMS truck-out of about 21–23 bn L/yr
  (56.7–63.7 million L/day × 365).
- Lagos generators alone would then use roughly half of all petrol, which is not plausible
  once vehicles are counted. Either the survey extrapolation is high or truck-out is undercounted.
- The method must reconcile this before using either figure for calibration.

## 5. DisCo supply and reliability, and DisCo-to-state mapping — Amber

**What exists (NERC)**
- **Quarterly reports**, per DisCo: energy offtake vs. available capacity (MWh/h), energy
  received and billed, energy accounting efficiency, billing and collection efficiency,
  ATC&C loss and complaints. In 2026 Q2 all DisCos offtook 3,197 MWh/h against 3,398 MWh/h
  available.
- **Monthly DisCo orders (MYTO supplementary orders)** cite feeder performance reports and
  list Band A feeders that missed their 20-hour supply level, with compensation. DisCos must
  also publish rolling 7-day average Band A hours on their own websites.
- **Not found:** hours of supply for all customers (all bands) by DisCo or by state.

**DisCo-to-state mapping** (from press summaries; check against NERC licence areas before use)

| DisCo | States |
|---|---|
| Abuja (AEDC) | FCT, Kogi, Nasarawa, Niger |
| Benin (BEDC) | Delta, Edo, Ekiti, Ondo |
| Eko (EKEDC) | Lagos (part), Agbara area of Ogun |
| Ikeja (IE) | Lagos (part) |
| Enugu (EEDC) | Abia, Anambra, Ebonyi, Enugu, Imo *(from general knowledge; not in the sources found)* |
| Aba Power | Aba ring-fenced area, Abia *(to verify)* |
| Ibadan (IBEDC) | Oyo, Ogun, Osun, Kwara, plus parts of Niger, Ekiti, Kogi |
| Jos (JEDC) | Bauchi, Benue, Gombe, Plateau |
| Kaduna (KAEDCO) | Kaduna, Kebbi, Sokoto, Zamfara |
| Kano (KEDCO) | Kano, Katsina, Jigawa |
| Port Harcourt (PHED) | Rivers, Bayelsa, Cross River, Akwa Ibom |
| Yola (YEDC) | Adamawa, Borno, Taraba, Yobe |

All 36 states and the FCT are covered.

**Risks:** DisCos span several states, and some states are split across DisCos (Lagos,
Ogun, Niger, Ekiti, Kogi, Abia). Under the Electricity Act 2023, DisCos are creating
state-level subsidiaries (e.g. AEDC's Niger and Kogi units), so boundaries change over time
and need a dated mapping. There is no open licence.

## 6. SEforALL "Beyond Gensets" (Lagos, Oct 2024) — Amber

**Important:** the public PDF is marked **"Confidential and proprietary. Please do not copy,
cite or distribute without the permission of SEforALL."** Figures below are noted for
assessment only. Ask SEforALL for permission, or cite the public press release, before
publishing any of them. The PDF is a 20-page extract; its contents list runs to p. 73+.

**Method**
- **Households:** stratified cluster survey with a target of 6,000 households in 20 LGAs.
  200 ward clusters of 30 households each were chosen in proportion to LGA population.
  Enumerators walked from the ward centroid and visited about 1 in 5 homes.
- **Commercial (MSMEs):** survey of about 240 firms (sample-size basis: World Bank Enterprise
  Survey), scaled up to the NBS 2021 MSME count.
- **Markets:** 9 markets surveyed, scaled up to 276.
- **Capacity:** the most-reported generator size per class × number of households.
- **Supporting data:** GRID3 geospatial data.

**Key numbers (Lagos)**
| | Households | MSMEs | Markets |
|---|---|---|---|
| Generators | 4,323,000 | 113,642 | 13,704 |
| Capacity | 8.8 GW | 10.4 GW | 192 MW |
| Units owning ≥1 | 72% of 5,703,437 households | 94% of 80,072 MSMEs | 276 markets |
| Fuel type | petrol 97.7%, diesel 1.7%, gas 0.6% | diesel 59%, petrol 38%, gas 3% | petrol 99%, diesel 1% |
| Capacity share 0.1–5 kVA | 96% | 33% | 76% |
| Fuel use | 9 bn L/yr | 6.6 bn L/yr | 61 million L/yr |
| Emissions | 21 Mt CO2e | 17.8 Mt CO2e | 141,125 t |

Total: about 19 GW and about 39 Mt CO2e per year. Small businesses are quoted as spending
"~₦20,000–40,000 per month" on fuel (from an REA/Vista 2022 study, before subsidy removal).
**Generator running hours were not found in the 20-page extract.** Press coverage quotes
₦5.3 trillion per year for MSME fuel and ₦14 trillion in total; these are not in the extract.

**Risks:** the confidentiality marking; the scale-up method (modal size × count) may push
capacity and fuel use up (see section 4); and the fuel-use method is not shown in the extract.

## 7. The "₦7.6 trillion" estimate — Red as calibration

**How the figure travelled**
1. Leadership, "Nigeria's N7.6trn Annual Spend On Petrol, Generator Spread Emissions", quotes
   SEforALL's Beyond Gensets.
2. SEforALL (p. 16) says: "Nigerians reportedly spend **$10 billion (~₦7.6 trillion)**
   annually on fuel and maintenance for small petrol gensets." Its footnote says the costs
   are from before petrol subsidy removal.
3. SEforALL's listed sources are the REA/Vista/UMass Amherst 2022 preliminary MSME and market
   energy study, and the **A2EI & Dalberg 2019** report "Putting an End to Nigeria's Generator
   Crisis".

**Method:** not given in SEforALL. The naira figure implies about ₦760/$. A2EI–Dalberg
estimated about 22 million small petrol generators. Secondary sources quote its spend as
**$12 billion a year (2018)**. No $10 billion figure was found in what was checked.

**Use:** cite only as a reported figure, showing this chain of sources. Do not use it to
calibrate: it covers fuel *and* maintenance, dates from before subsidy removal and its
method is unverified.

## 8. Solar resource by state — Green

- **Global Solar Atlas (World Bank / Solargis):** country GIS layers (e.g. GHI, PV output).
  The licence is CC BY 4.0 with mandatory additions in the GSA terms (an arbitration clause
  and required attribution "© The World Bank, Source: Global Solar Atlas 2.0, Solar resource
  data: Solargis"). The terms page itself could not be read automatically (the site is
  JavaScript-only), so read it before use.
- **PVGIS (EU JRC):** free web tool and API; JRC's data catalogue lists PVGIS 5.3 data as
  CC BY 4.0. The API terms have not yet been read.
- **State level:** needs zonal statistics over state boundaries, which require a separate
  admin-boundary dataset with its own licence.

## 9. Poverty or income by state — Green

- **NBS Nigeria Multidimensional Poverty Index 2022** (with UNDP, OPHI, UNICEF): survey
  Nov 2021 – Feb 2022, representative for all 36 states, the FCT and 109 senatorial districts.
  Multidimensional poverty ranges from 27% (Ondo) to 91% (Sokoto); 63% nationally. The state
  tables are in the 184-page PDF and need extracting.
- **Alternative:** NLSS 2018-19 consumption poverty by state (older).
- **Licence:** none stated; cite NBS.

## 10. Generator fuel curves and IPCC factors — reused

From `nigeria-emission-factors/docs/phase0_results.md` (not re-downloaded):
- **Diesel:** full 25/50/75/100% fuel curves (e.g. a 20 kVA set: 1.9 / 2.9 / 4.2 / 5.8 L/h).
- **Petrol:** only partial points (Honda EU70is run times); **no load curves for the
  1–3.5 kVA brands common in Nigeria**.
- **IPCC 2006:** CO2 74,100 kg/TJ (diesel) and 69,300 kg/TJ (petrol); NCV 43.0 and 44.3 TJ/Gg.
  The CH4/N2O factors depend on whether generators are treated as stationary or off-road.

This gap matters most here: Lagos household generators are 97.7% petrol and 96% are 0.1–5 kVA
(SEforALL), and A2EI's meters show 83% are under 3 kVA and run at low load.

---

## Plan changes

1. **Prices:** use NBS monthly state tables (Jan 2023 – May 2026). Fill gaps (AGO Aug 2023)
   from neighbouring releases' previous-month and year-ago columns. Extend when June 2026
   onward is published.
2. **Household ownership:** use DHS 2024 microdata (`sh132n`) for state ownership, and
   MICS 2021 as a second time point. Drop GHS-Panel for state estimates.
3. **Business use:** the 2021 MSME tables are missing. Get the report from a trusted copy;
   check the 2017 NBS MSME survey as a fallback; use SEforALL's MSME results for Lagos only
   (with permission).
4. **Top-down check:** NMDPRA gives national monthly totals only, from about late 2024. Find
   2023 coverage elsewhere. Reconcile the Lagos-versus-national petrol gap (section 4) before
   calibrating.
5. **Reliability:** no all-customer supply hours by state exist. Use DisCo-level NERC
   indicators (offtake vs available, ATC&C) mapped to states with a dated DisCo map, and treat
   them as a proxy.
6. **SEforALL:** ask for permission to cite and for the full report. Until then, cite only the
   public press release figures.
7. **"₦7.6 trillion":** report as a cited claim with its source chain; do not calibrate to it.
8. **Petrol fuel curves:** these are the main modelling weakness. Prioritise small petrol
   generator data (measurement or literature) over refining diesel.

## Files to download by hand

1. **DHS 2024 Nigeria household recode microdata:** register at dhsprogram.com (project
   description required).
2. **MICS 2021 Nigeria microdata:** UNICEF MICS site or World Bank catalog 5959 (registration).
3. **SMEDAN–NBS MSME Survey 2021 report:** from a trusted copy (ask NBS or SMEDAN). Do not use
   smedan.gov.ng while it appears compromised.
4. **NMDPRA monthly Fact Sheets (all available months):** from nmdpra.gov.ng; no index page
   was found automatically.
5. **Global Solar Atlas, Nigeria GIS data:** the download page is interactive. Read the GSA
   terms page first.
6. **SEforALL full Beyond Gensets report and permission to cite:** contact SEforALL.

The NBS price files (catalogs 157/158 and the e-library) and the NERC monthly DisCo orders
can be downloaded by script; robots.txt allows it and no login is needed.
