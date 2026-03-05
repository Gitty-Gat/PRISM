# DASHBOARD_PATCH_FIX (Stage H Phase 0)

## Issue
A prior automated patch operation reported a failed edit in `dashboard/run_dashboard.py`.

Goal: ensure multi-campaign support works end-to-end:
- `REALDATA_GRID_RUN`
- `REALDATA_EXPANDED_VALIDATION`

## Fix applied
### API endpoints
- `/api/experiment` already accepted:
  - `campaign` (defaults to `default_campaign`)
  - `id`

- **Added** campaign filtering to `/api/state`:
  - `/api/state` → returns global meta state: campaigns list, default_campaign, campaign_states
  - `/api/state?campaign=<campaign>` → returns the selected campaign state only

### Loader behavior
`dashboard/data_loader.py` already resolves paths dynamically:
- `results/<campaign>/<experiment_id>/summary.json`

and loads aggregated CSVs from:
- `results/<campaign>/analysis/*.csv`

### UI
Dashboard UI already has dropdown filters:
- campaign
- time slice
- window length
- weighting
- dependence
- posterior mode
- experiment id

The UI sends `campaign` to `/api/experiment`.

## Verification
Started dashboard:
- `python3 dashboard/run_dashboard.py --port 8053`

Verified:
- `GET /api/state` returns both campaigns.
- `GET /api/state?campaign=REALDATA_EXPANDED_VALIDATION` returns 300 experiments.
- `GET /api/experiment?campaign=REALDATA_EXPANDED_VALIDATION&id=Sopen__W60m__RAW__RAW_N__sequential_update` returns `hash_check.status == ok`.

## Notes
Dashboard remains read-only:
- reads results only
- no Databento calls
- no writes to results
