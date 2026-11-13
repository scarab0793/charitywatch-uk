# Official UK charity data ingestion

## England and Wales

The Charity Commission publishes daily JSON and tab-delimited ZIP extracts at:
https://register-of-charities.charitycommission.gov.uk/en/register/full-register-download

Relevant tables:
- charity
- charity_annual_return_history
- charity_annual_return_parta
- charity_annual_return_partb
- charity_published_report

These are separate relational datasets, not the simplified CSV currently accepted by
`scripts/import_uk_register.py`. **Do not point that importer directly at a ZIP or
raw official TXT extract.** First inspect the published data-definition document,
join on the documented identifiers, and validate each annual-return field's
accounting meaning and period.

## Safe ingestion sequence

1. Download the regulator's published archive and its data-definition document.
2. Record URL, download time, file hash, licence and extract version.
3. Unzip in a temporary directory; validate file names, header schemas and sizes.
4. Join charity identifiers to annual-return rows using documented keys.
5. Prefer the latest *valid filed* accounting period, not the most recent calendar year.
6. Keep income, expenditure, CEO pay, grants, reserves and document links distinct.
7. Export compact JSON shards and an audit manifest with counts and provenance.
8. Only publish when record counts and integrity checks pass.

## Current status

The repository has a CSV-to-JSON prototype, a searchable frontend and a
manual GitHub Actions workflow requiring a configured CSV URL. It does not yet
ingest the regulator's official ZIP format or publish a nationwide dataset.
Do not enable unattended publishing until a real download has been validated.

## Other jurisdictions

Scotland (OSCR) and Northern Ireland (CCNI) need separate documented source
adapters, jurisdiction-specific registration identifiers, and explicit
coverage statistics. Never claim UK-wide coverage from England/Wales alone.
