# Variable Codebook
*PP422 | LSE Growth Co-Lab | Last updated: March 2026*

---

## Dependent Variables

| Variable | Label | Definition | Source | Formula | Role |
|---|---|---|---|---|---|
| `lq_emp` | Employment LQ | Relative specialisation of LAD in IS8 sector based on employment | Employee counts LAD | (IS8 emp in LAD / total emp in LAD) / (IS8 emp nationally / total emp nationally) | Primary dependent variable |
| `lq_bus` | Business count LQ | Relative specialisation of LAD in IS8 sector based on business count | Business counts LAD | (IS8 businesses in LAD / total businesses in LAD) / (IS8 businesses nationally / total businesses nationally) | Robustness check |
| `growth_emp` | Employment growth | Change in IS8 employment over 2015–2024 | Employee counts LAD | (emp_2024 − emp_2015) / emp_2015 | Descriptive only (Steps 7, 9) |
| `growth_bus` | Business count growth | Change in IS8 business count over 2016–2024 | Business counts LAD | (bus_2024 − bus_2016) / bus_2016 | Descriptive only (Steps 7, 9) |

---

## Independent Variables

Variables retained for regression. Grouped by EEG dimension. All ONS indicators are single time-point snapshots (roughly 2021–2024), treated as time-invariant.

### Human capital

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `nvq_level3` | NVQ level 3+ qualifications | ONS | Stock of skilled workers available to IS8 firms |
| `gcse_age19` | GCSEs by age 19 | ONS | Pipeline of qualified school leavers entering workforce |
| `apprenticeship_starts` | Apprenticeship starts | ONS | Vocational pipeline — relevant to Advanced Manufacturing, Life Sciences |
| `apprenticeship_achievements` | Apprenticeship achievements | ONS | Completed vocational training — workforce capability stock |
| `fe_participation` | FE and skills participation | ONS | Ongoing skills development in working-age population |

### Entrepreneurial discovery

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `enterprise_births` | New enterprise births | ONS | Rate of new firm formation — entrepreneurial dynamism |
| `enterprise_deaths` | Enterprise deaths | ONS | Creative destruction — Schumpeterian churn signal |
| `enterprise_active` | Active enterprises | ONS | Stock of firms — agglomeration base |
| `enterprise_high_growth` | High growth enterprises | ONS | Presence of scaling firms — IS8 ecosystem depth |

### Connectivity and accessibility

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `transport_to_employer` | Public transport to employer | ONS | Labour market accessibility — workers can reach IS8 employers |
| `drive_to_employer` | Drive to employer | ONS | Labour market accessibility — car-dependent areas |
| `cycle_to_employer` | Cycle to employer | ONS | Local accessibility — urban density signal |
| `broadband` | Gigabit broadband availability | ONS | Digital infrastructure — prerequisite for Digital and Technologies, Financial Services |
| `coverage_4g` | 4G coverage | ONS | Mobile connectivity — baseline digital infrastructure |

### Labour market conditions

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `unemployment_rate` | Unemployment rate | ONS | Available labour supply — market flexibility for IS8 hiring |

### Place conditions

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `housing_net_additions` | Net additions to housing stock | ONS | Housing supply capacity — affects worker attraction and retention |

### Derived variables (computed in IndicatorBuilder)

| Variable | Label | Source | EEG rationale |
|---|---|---|---|
| `related_variety` | Related variety | Business counts LAD + SIC lookup | Core EEG concept — adjacent industries enable IS8 emergence via capability spillovers |
| `business_density` | Business density | Business counts LAD + ONS population | IS8 firms per 1,000 working-age population — ecosystem density |

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
| Government R&D | ITL1 only | Key EEG variable — acknowledge as significant limitation in memo |
| UK exports | ITL1/ITL2 only | Acknowledge as limitation |
| Inward FDI | ITL1/ITL2 only | Acknowledge as limitation |
| Outward FDI | ITL1/ITL2 only | Acknowledge as limitation |
| KS2 attainment | County/UA only | Below LAD resolution |
| Ofsted rating | County/UA only | Below LAD resolution |
| Persistent absences | County/UA only | Below LAD resolution |
| FE achievements | County/UA only | Below LAD resolution |
| Female/Male HLE | County/UA only | Below LAD resolution |
| Homicide offences | Police Force Area | Below LAD resolution |
| Population under devolution | Region only | Below LAD resolution |

### Excluded: data not available

| Variable | Notes |
|---|---|
| University/research intensity | Not in ONS file — key EEG variable. Source: HESA. Acknowledge as significant limitation in memo |
| Clean Energy Industries (sector) | Entirely absent from all source files — one IS8 sector cannot be modelled |

---

## Notes

- Growth variables (`growth_emp`, `growth_bus`, `cagr_emp`, `cagr_bus`) are used as descriptive measures only, not as regression outcomes. Running a growth regression with time-invariant independent variables would require strong assumptions about the stability of local conditions over the growth period.
- `related_variety` is currently a placeholder in `IndicatorBuilder` — SIC adjacency method to be finalised.
- Expected signs for all independent variables to be documented after Step 8 results.
- The two most significant data gaps for EEG are university/research intensity and government R&D at LAD level. Both should be prominently acknowledged as limitations.