# CharityWatch UK

Independent UK charity finance transparency portal.

## Current status
An accessible initial landing page with official regulator links and an explicit data-integrity policy. The nationwide dataset, CEO compensation extraction, grant tracing, comparisons and automatic refresh **are not implemented yet**.

## Deployment
Enable GitHub Pages under Settings > Pages > Deploy from a branch > main / root.

## Roadmap
1. Obtain and validate permitted bulk data exports for England & Wales, Scotland and Northern Ireland.
2. Normalize registration IDs, jurisdiction, reporting periods, income and expenditure; retain original sources.
3. Build a paginated searchable dataset (not one huge JSON file).
4. Extract grant recipients and executive remuneration from annual reports with source references and human review.
5. Schedule updates and add tests for duplicate records, stale data and accounting category consistency.

## Accuracy
Never represent missing fields as zero. Keep reporting periods and accounting definitions visible. Do not equate charitable activity spending with direct grants.
