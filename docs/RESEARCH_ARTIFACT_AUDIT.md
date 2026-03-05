# RESEARCH_ARTIFACT_AUDIT (Stage J)

## Scope
Audit of artifact completeness and hash integrity for:
- `results/DATABENTO_LIVE_PROBE/`
- `results/REALDATA_GRID_RUN/`
- `results/REALDATA_EXPANDED_VALIDATION/`

No new experiments were executed for this audit.

---

## Artifact requirements (per experiment)
Required files:
- `summary.json`
- `adapter_diagnostics.json`
- `metrics_aggregated.csv`
- `artifact_hashes.json`
- `run_log.txt`

Hash requirement:
- `artifact_hashes.json["summary.json"]` must equal SHA256(`summary.json`).

---

## Results
### DATABENTO_LIVE_PROBE
- directories audited: 1
- missing/invalid: 0
- hash mismatches (summary.json): 0
- recorded cost: ~$0.0285

### REALDATA_GRID_RUN
- experiments audited: 50
- missing/invalid: 0
- hash mismatches (summary.json): 0
- recorded cost (campaign summary): ~$0.2827

### REALDATA_EXPANDED_VALIDATION
- experiments audited: 300
- missing/invalid: 0
- hash mismatches (summary.json): 0
- recorded cost (campaign summary): ~$2.8617

---

## Totals
- total experiments executed (campaign cells): **350**
  - 50 grid + 300 expanded
  - (plus 1 live probe scenario)
- total Databento estimated spend: **~$3.1729**

---

## Notes
- These campaigns are explicitly **proxy evidence** and intended for demonstration/illustration.
- Results directories are gitignored by design to avoid committing large generated artifacts.
