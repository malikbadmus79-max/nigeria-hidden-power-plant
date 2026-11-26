# Power BI dashboard (Phase 5)

`report/HiddenPowerPlant.pbip` is a Power BI Project (open it in Power BI Desktop). It has four pages
matching the approved mockups in `figures/mockups/`; screenshots are in `figures/dashboard/`
(`pageN.png`, and `compare_pageN.png` = mockup above, Power BI below). All figures are estimates
with low–high ranges; method and limits are in `docs/phase4_audit.md`.

## Data path

The model reads the CSVs in `data/processed/powerbi/` through one Power Query text parameter,
**DataFolder**. Power Query has no relative paths, so DataFolder holds the absolute path of that
folder (with a trailing backslash). On another machine, change only this value
(Transform data > Edit parameters) and refresh, or re-run `build_pbip.py`.

## How it is built

| Step | Script | Notes |
|---|---|---|
| 1 | `build_pbip.py` | Semantic model (TMDL: DataFolder, 8 CSV tables, relationships), report shell, theme |
| 2 | `build_topojson.py` | Shape Map TopoJSON of the 36 states + FCT from geoBoundaries ADM1 |
| 3 | `apply_model.py` | Measures, calculated columns/tables from `model_spec.py` via the Power BI Modeling MCP (`mcp_client.py`); prints the check table (`check_table.txt`, 43/43 OK) |
| 4 | `build_pages.py` | The 4 report pages (PBIR JSON), validated with `pbir_validate.py` before they are copied in |
| – | `tmdl_add_measures.py` | Adds missing measures to `_Measures.tmdl` while Power BI Desktop is closed |
| – | `compare.py`, `pbi_*.ps1` | Screenshots, side-by-side checks, safe save/close and UI steps in Power BI Desktop |

Every number on the dashboard is a DAX measure (no typed numbers). Each series colour has its own
measure; there are no field-value colour rules. Low–high ranges use Power BI error bars (a shaded
band on page 1, whiskers on page 3). PBIR schemas for the validator are fetched with
`fetch_schemas.py` into `schemas/` (not committed).

## Credits

- State boundaries: geoBoundaries NGA ADM1 (NGA-ADM1-27671186, GRID3 2022), CC BY 4.0.
  Runfola et al. (2020), *geoBoundaries: A global database of political administrative boundaries*,
  PLoS ONE 15(4): e0231866. Simplified by grid snapping for the Shape Map.
- Data sources: NBS, NERC, CBN, Global Solar Atlas 2.0 (© The World Bank, Solar resource data:
  Solargis, CC BY 4.0), NBS NLSS 2018/19 and MPI 2022 (see `docs/phase4_audit.md`).
- `CY26SU04.json` in `StaticResources/SharedResources/BaseThemes/` is Power BI Desktop's base theme.

## Known small differences from the mockups

Axis tick steps are chosen by Power BI (for example ₦50,000 not ₦20,000 steps on page 1); on page 2 the
axis ticks show no ₦ sign; the page-1 end label sits above the line, not to its right.
