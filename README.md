# Household Energy Consumption Pipeline (GCP)

A GCP data platform project, built to get hands-on with the exact stack used
by 1KOMMA5°'s data platform team — Terraform, BigQuery, and (next) SQLMesh —
using household energy consumption data as the theme. **This is an active,
in-progress project.**

## Why this project

Built specifically to close the gap between my AWS experience and this
role's GCP stack, using a dataset thematically close to what 1KOMMA5°
works with: household-level energy consumption.

## Architecture
UCI public dataset (CSV)
│
▼
GCS bucket (raw landing) ← provisioned with Terraform
│ load_to_bigquery.py
▼
BigQuery: energy_raw ← 2,075,259 rows loaded ✅
│ SQLMesh (next step)
▼
BigQuery: energy_staging ← not built yet
│ SQLMesh
▼
BigQuery: energy_marts ← not built yet
│
▼
Looker Studio dashboard ← not built yet


## Status

| Component | Status |
|---|---|
| Terraform infra (GCS bucket, 3 BigQuery datasets, service account, least-privilege IAM) | ✅ Done |
| Python ingestion script (download → clean → GCS → BigQuery) | ✅ Done — 2,075,259 rows loaded |
| Data quality fix: normalized two different missing-value styles in the source file | ✅ Done |
| SQLMesh models (raw → staging → daily marts) with audits and a unit test | 🔜 In progress |
| GitHub Actions CI (validate Terraform, run SQLMesh tests, lint Python) | 🔜 Not started |
| Data dictionary / governance doc | 🔜 Not started |
| Looker Studio dashboard | 🔜 Not started |


## What's provisioned (Terraform)

- 1 GCS bucket (`energy-pipeline-raw-suhas`) — raw data landing zone
- 3 BigQuery datasets — `energy_raw`, `energy_staging`, `energy_marts`, separated so access can differ by layer (pipeline-only vs. read access for other teams)
- 1 service account (`energy-pipeline-sa`) — used only by the pipeline, not by me directly
- Least-privilege IAM bindings — the service account can only read/write the bucket and the three datasets, nothing else in the project

## What the ingestion script does

1. Downloads the [UCI Individual Household Electric Power Consumption dataset](https://archive.ics.uci.edu/dataset/235) (~2 million minute-level readings from one household)
2. **Cleans it:** the source file mixes two styles of missing value — an explicit `?` marker, and some rows with a truly empty field. BigQuery's loader only recognizes one null marker, so the script normalizes both to `?` before loading. This was a real issue hit during the build, not an assumption going in.
3. Uploads the cleaned file to the GCS landing bucket
4. Loads it into `energy_raw.household_power_consumption` in BigQuery with an explicit schema (not auto-detected)

## Next steps

1. **SQLMesh transformations** — build a `stg_power_consumption` model to clean and type the raw data, then a `daily_household_consumption` mart to aggregate it, each with audits (not-null, uniqueness checks) and a unit test that runs against fixture data without needing a live BigQuery connection.
2. **GitHub Actions CI** — a workflow that runs on every push: validates the Terraform, runs the SQLMesh unit tests, and lints the Python ingestion script.
3. **Data dictionary** — document every table and column, who owns it, and who can access it (governance, matching the "data catalogs / metadata management" requirement of a data platform role).
4. **Looker Studio dashboard** — a simple chart on top of the final daily mart table, to demonstrate connecting a BI tool to a modern data setup.
5. **Cleanup** — `terraform destroy` once done experimenting, to avoid any ongoing cost.

## Notes

- `terraform.tfvars`, Terraform state files, the Python virtual environment, and the downloaded dataset are all gitignored — none of them belong in version control.
- Region used: `europe-west3` (Frankfurt). 
