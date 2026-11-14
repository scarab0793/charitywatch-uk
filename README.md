# CharityWatch UK — Version 1.0

Independent charity finance transparency website. This is a **published first release**, not a complete audit of every UK charity.

## Release status — 14 November 2026

The GitHub Pages website has passed its automated smoke tests (including a headless browser test), 360Giving snapshot validation, and deployment. Version 1.0 is the feature-frozen baseline; future data imports are routine maintenance, not unfinished release work.

## Included in version 1.0

- Searchable charity register and organisation detail pages, sourced from published Charity Commission for England and Wales (CCEW) datasets.
- Financial histories with reported income and expenditure, reporting periods, and source context; missing values are not interpreted as zero.
- CCEW annual-return Part A salary bands (employee counts, **not** named CEO salaries) and Part B expenditure categories.
- Sourced, manually verified CEO remuneration for **six organisations**, with different pay definitions labelled and original evidence linked.
- Institutional grant-making summaries for **5,868 organisations** in the published CCEW Part B extract. This is reported spending, not a named-recipient ledger.
- 360Giving award snapshots for a bounded sample of organisations: latest verified snapshot (14 November 2026) contained **682 cached records across 22 successfully refreshed directions out of 24 selected directions**. This number is a snapshot, not a permanent target.
- Named 360Giving funders and recipients where published, searchable cached awards, paged JSON storage, cached GBP award sample totals, and transparent source-coverage caveats.
- Automatic updates via GitHub Actions, plus data-integrity, browser smoke, and deployment checks.

## Limits and interpretation

- The full E&W register contains **357,053 entries** in the latest published manifest, including registry records beyond current operating organisations. Figures change after refresh.
- This is **not yet complete UK-wide regulator coverage**: Scotland and Northern Ireland are not represented at the same level as England and Wales.
- Public annual accounts do not always name a CEO's salary; do not infer individual remuneration from staff salary bands.
- CCEW grant expenditure and 360Giving *awards* have different dates, definitions, and coverage. Awarded money is not necessarily paid money; neither figure should be subtracted from the other as an accounting reconciliation.
- Some 360Giving sources return 404 or other errors. A missing endpoint does **not** establish that no grant was made or received. Snapshots are partial and capped at 100 awards per organisation/direction.
- Charity registration numbers can include linked charities. Financial totals for a linked fund must not automatically be attributed to a parent charity without a verified relationship.
- The site is a public-data explorer, not an audit, charity rating, fraud finding, or endorsement.

## Maintenance

GitHub Actions maintains the data when source data and workflows are available. The cache selection is bounded and periodically retries unavailable 360Giving endpoints; older valid data is preserved when refreshes fail. Review [Actions](https://github.com/scarab0793/charitywatch-uk/actions) for live results. Routine automated refreshes may change counts without changing the 1.0 feature scope.

## Release acceptance

At the 1.0 baseline the following runs completed successfully:

- [Website smoke tests](https://github.com/scarab0793/charitywatch-uk/actions/runs/43597483883)
- [360Giving cache validation](https://github.com/scarab0793/charitywatch-uk/actions/runs/43597483866)
- [GitHub Pages deployment](https://github.com/scarab0793/charitywatch-uk/actions/runs/43597483944)
- [Sourced CEO-pay validation](https://github.com/scarab0793/charitywatch-uk/actions/runs/43596972928)

The first release is **complete within the scope above**. Additional source coverage, more verified CEO-pay records, and future enhancements are later versions rather than blockers for 1.0.

## Data provenance

CCEW official bulk charity data and annual returns; independently sourced charity annual reports for explicitly cited CEO remuneration; 360Giving published award API records. Inspect individual profiles and source links before drawing conclusions.
