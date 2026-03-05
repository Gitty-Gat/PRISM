# REPRODUCIBILITY

## Reproducibility posture
This repository is designed so that key analyses and figures can be reproduced **without**:
- any Databento API calls
- any additional data downloads

Reproduction relies on saved artifact directories under `results/`.

## Quickstart
```bash
git clone <repo>
cd PRISM
python3 scripts/reproduce_prism_results.py
```

## What the reproduction script does
- Recomputes aggregated CSV tables for:
  - `REALDATA_GRID_RUN`
  - `REALDATA_EXPANDED_VALIDATION`
- Regenerates visualization suites:
  - grid showcase
  - expanded showcase
  - predictive showcase
  - baseline comparison showcase
- Rebuilds:
  - `results/FINAL_EXPERIMENT_SUMMARY.csv`

## Artifact integrity verification
Each experiment directory contains `artifact_hashes.json`.

At minimum:
- the stored SHA256 for `summary.json` should match the file content.

The dashboard also surfaces hash warnings.

## Notes
- The plotting stack is dependency-light (SVG + ImageMagick `convert`).
- Some PDF exports may be blocked by ImageMagick security policy; PNG/SVG are the canonical artifacts.

## No-network guarantee
- Databento live calls require `PRISM_DATABENTO_LIVE=1`.
- Reproduction scripts do not set this flag or invoke live transports.
