# Variable Codebook
*PP422 | LSE Growth Co-Lab | Last updated: March 2026*

For methodological assumptions and preprocessing flags, see `assumptions_and_flags.md`.

---

## Dependent Variables

Four outcome variables across 2 measures × 2 dimensions, run separately for each of 6 IS8 sectors (Defence excluded). All models run 4 times and interpreted jointly through the quadrant framework below.

### Location Quotient (LQ)

Captures current local specialisation relative to the national benchmark. Measures *where* a sector is concentrated at a point in time.

| Variable | Label | Definition | Source | Formula |
|---|---|---|---|---|
| `lq_emp` | Employment LQ | Relative specialisation of LAD in IS8 sector based on employment | Employee counts LAD | (IS8 emp in LAD / total emp in LAD) / (IS8 emp nationally / total emp nationally) |
| `lq_bus` | Business count LQ | Relative specialisation of LAD in IS8 sector based on business count | Business counts LAD | (IS8 businesses in LAD / total businesses in LAD) / (IS8 businesses nationally / total businesses nationally) |

**Threshold:** LQ = 1 (national average). LQ > 1 = above national specialisation; LQ < 1 = below.

---

### Growth Differential (GD)

Captures LAD sector growth trajectory relative to the national trend. Measures *direction and speed* of change, net of national conditions.

| Variable | Label | Definition | Source | Formula |
|---|---|---|---|---|
| `gd_emp` | Employment growth differential | LAD IS8 employment trajectory minus national IS8 employment trajectory | Employee counts LAD | β_LAD_emp − β_national_emp |
| `gd_bus` | Business count growth differential | LAD IS8 business count trajectory minus national IS8 business count trajectory | Business counts LAD | β_LAD_bus − β_national_bus |

**Method:** Both β coefficients are estimated via log-linear OLS: `log(y_t) ~ α + β·t`, where t = year and y = employment or business count. β approximates the annualised % growth rate (log points per year).

**β_national** is a single fixed value per sector × dimension, computed once at national level from the full 2016–2023 England panel and subtracted from every LAD's β.

**Interpretation:** GD > 0 → LAD growing faster than national trend; GD < 0 → LAD growing slower or declining faster; GD = 0 → same trajectory as national. Units: log points per year ≈ percentage points per year.

**Window:** 2016–2023. OLS fitted on all available years from first appearance of activity in a given LAD × sector, up to 2023.

---

### Diagnostic columns (not used in analysis)

| Variable | Label | Definition |
|---|---|---|
| `n_years_emp` | Valid employment years | Count of non-zero, finite employment observations used in LAD slope estimate. GD set to NaN when < 4. |
| `n_years_bus` | Valid business count years | Count of non-zero, finite business count observations used in LAD slope estimate. GD set to NaN when < 4. |
| `emp_share` | Employment share | IS8 employment as share of total LAD employment. Used internally for LQ computation. |

---

### Quadrant Framework

Combines LQ (current position) and GD (trajectory) into a 2×2 interpretation matrix. Applied separately for each of the 4 Y combinations. Discrepancies across outputs are analytically meaningful and enrich interpretation — they are not resolved into a single composite score.

| | **GD > 0** (above national trend) | **GD < 0** (below national trend) |
|---|---|---|
| **LQ > 1** (above national share) | Anchor & Growing | Established but Slowing |
| **LQ < 1** (below national share) | Emerging / Catching Up | Weak & Falling Behind |

---

## Independent Variables

Variables retained for regression. Grouped by EEG dimension. All ONS indicators are single time-point snapshots (roughly 2019–2023), treated as time-invariant.

### Human capital

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `nvq_level3` | NVQ level 3+ qualifications | ONS / NOMIS 2021 | Stock of skilled workers available to IS8 firms |
| `gcse_age19` | GCSEs by age 19 | ONS / DfE 2021/22 | Pipeline of qualified school leavers entering workforce |
| `apprenticeship_starts` | Apprenticeship starts | ONS / DfE 2022/23 | Vocational pipeline — relevant to Advanced Manufacturing, Life Sciences |
| `apprenticeship_achievements` | Apprenticeship achievements | ONS / DfE 2022/23 | Completed vocational training — workforce capability stock |
| `fe_participation` | FE and skills participation | ONS / DfE 2022/23 | Ongoing skills development in working-age population |
| `n_universities_feecap_lad` | Fee-cap HE providers | HESA campus locations + OfS register 2024 | Count of fee-cap registered HE providers with a physical campus in the LAD — institutional thickness, knowledge spillovers, graduate talent pipeline. Directly addresses key EEG gap. Treated as time-invariant structural condition. |

### Entrepreneurial discovery

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `enterprise_birth_rate` | Enterprise birth rate | ONS 2022 | New firm formation as share of active stock — entrepreneurial dynamism net of LAD size |
| `enterprise_death_rate` | Enterprise death rate | ONS 2022 | Creative destruction rate — Schumpeterian churn signal net of LAD size |
| `enterprise_high_growth_rate` | High growth enterprise rate | ONS 2022 | Share of active firms that are scaling — IS8 ecosystem depth |

**Derivation:** Raw counts (`enterprise_births`, `enterprise_deaths`, `enterprise_high_growth`) divided by `enterprise_active` to remove LAD size effect. `enterprise_active` dropped after normalisation.

### Connectivity and accessibility

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `transport_to_employer` | Public transport to employer | DfT 2019 | Labour market accessibility — workers can reach IS8 employers |
| `drive_to_employer` | Drive to employer | DfT 2019 | Labour market accessibility — car-dependent areas |
| `cycle_to_employer` | Cycle to employer | DfT 2019 | Local accessibility — urban density signal |
| `broadband` | Gigabit broadband availability | Ofcom Sep 2023 | Digital infrastructure — prerequisite for Digital and Technologies, Financial Services |
| `coverage_4g` | 4G coverage | Ofcom Sep 2023 | Mobile connectivity — baseline digital infrastructure |

### Labour market conditions

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `unemployment_rate` | Unemployment rate | ONS 2022/23 | Available labour supply — market flexibility for IS8 hiring |

### Place conditions

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `housing_net_additions` | Net additions to housing stock | DLUHC FY2023 | Housing supply capacity — affects worker attraction and retention |

### Derived variables (computed in IndicatorBuilder)

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `related_variety` | Related variety | Business counts LAD | Cross-sector Shannon entropy across IS8 sectors per LAD × year. Approximates EEG related variety — measures how diversified a LAD's business base is across IS8 sectors. Higher entropy = more adjacent industries available for capability spillovers. LAD × year level (same value across all sectors within a LAD × year). |
| `within_sector_diversity` | Within-sector diversity | Business counts LAD | Shannon entropy across SIC codes within each IS8 sector per LAD × year. Measures internal sectoral complexity. Complements related_variety. |

### Firm structure (computed in IndicatorBuilder)

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `size_large_share` | Large firm share | Business counts LAD | Share of large firms in IS8 sector per LAD — presence of anchor firms, potential cluster leaders |
| `size_micro_share` | Micro firm share | Business counts LAD | Share of micro firms in IS8 sector per LAD — entrepreneurial base density, new firm formation potential |

---

## Excluded Variables

### Excluded: reverse causality — outcomes of IS8 presence, not enablers

| Variable | Label | Reason |
|---|---|---|
| `gva_per_hour` | GVA per hour worked | IS8 cluster presence raises local productivity — outcome, not precondition |
| `weekly_pay` | Gross median weekly pay | IS8 firms pay above-average wages, raising local median — outcome, not precondition |
| `gdhi_per_head` | GDHI per head | Household income reflects sectoral composition of local economy — outcome, not precondition |
| `employment_rate` | Employment rate 16–64 | General economic health indicator — more likely outcome than enabling condition; redundant with unemployment rate |

### Excluded: not in EEG framework, reverse causality

| Variable | Label | Reason |
|---|---|---|
| `smokers` | Adult smokers | No EEG mechanism; reflects deprivation — outcome of place conditions, not enabler |
| `obesity_reception` | Reception age obesity | No EEG mechanism; reverse causality |
| `obesity_year6` | Year 6 obesity | No EEG mechanism; reverse causality |
| `obesity_adult` | Adult obesity | No EEG mechanism; reverse causality |
| `cancer_diagnosis` | Cancer diagnosis stages 1–2 | No EEG mechanism; reverse causality |
| `mortality_under75` | Under 75 mortality rate | No EEG mechanism; reverse causality |
| `life_satisfaction` | Life satisfaction | No EEG mechanism; likely outcome of economic conditions |
| `happiness` | Happiness | No EEG mechanism; likely outcome of economic conditions |
| `worthwhile` | Feeling life is worthwhile | No EEG mechanism; likely outcome of economic conditions |
| `anxiety` | Anxiety | No EEG mechanism; likely outcome of economic conditions |

### Excluded: temporal mismatch — no link to current workforce

| Variable | Label | Reason |
|---|---|---|
| `early_years_comms` | Early years communication | 15–20 year lag to workforce entry — captures future pipeline, not current capability stock |
| `early_years_literacy` | Early years literacy | As above |
| `early_years_maths` | Early years maths | As above |

### Excluded: insufficient geographic resolution

| Variable | Finest geography | Reason |
|---|---|---|
| Government R&D | ITL1 only | Key EEG variable — significant limitation, see assumptions_and_flags.md |
| UK exports | ITL1/ITL2 only | Significant limitation |
| Inward FDI | ITL1/ITL2 only | Significant limitation |
| Outward FDI | ITL1/ITL2 only | Significant limitation |
| KS2 attainment | County/UA only | Below LAD resolution |
| Ofsted rating | County/UA only | Below LAD resolution |
| Persistent absences | County/UA only | Below LAD resolution |
| FE achievements | County/UA only | Below LAD resolution |
| Female/Male HLE | County/UA only | Below LAD resolution |
| Homicide offences | Police Force Area | Below LAD resolution |
| Population under devolution | Region only | Below LAD resolution |

### Excluded: data not available or insufficient quality

| Variable | Notes |
|---|---|
| University/research intensity (HESA) | Partially addressed by `n_universities_feecap_lad`. Research income per institution not integrated — acknowledge remaining gap in limitations. |
| Business density | Working-age population unavailable at LAD level. Stock dimension captured implicitly through enterprise rate denominators. |
| Clean Energy Industries (sector) | Entirely absent from all source files — one IS8 sector cannot be modelled |
| OSM research centres | Too sparse (259 of 296 LADs = 0) and tagging inconsistency in OSM — excluded as unreliable |
| OSM hospitals | Credible counts but no clear EEG mechanism — excluded |
| OSM FE colleges | Partially overlaps with `fe_participation` — excluded to avoid redundancy |