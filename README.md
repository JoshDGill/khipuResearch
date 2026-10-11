# khipuResearch

A reproducible, null-model-first research pipeline for studying Inka khipus (knotted-cord records of the Andes).

Every finding is a hypothesis until it beats null models on held-out data, and null results are reported as carefully as positive ones. Nothing here is a "reading" of a khipu.

- **Project brief:** [`AGENTS.md`](AGENTS.md)
- **Execution plan:** [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md)
- **Pre-registrations:** [`prereg/`](prereg/)

## Quick start

```sh
uv sync          # pinned environment (Python >= 3.11)
make data        # download OKR, KBCR and KFG into data/raw/ and verify checksums
make check       # lint, tests, pre-registration check
```

Raw downloads are not committed. `data/raw/MANIFEST.csv` records every file's URL, version, sha256 and licence.

## Data and citation

| Source | Version | Licence |
|---|---|---|
| Open Khipu Repository | v2.1.0, [10.5281/zenodo.18025748](https://doi.org/10.5281/zenodo.18025748) | MIT |
| Khipu Field Guide | live site, snapshot dates in the manifest | MIT notice on site; cite KFG and original recorders |
| Khipu-Biblio Cross-Reference | v6, [10.26188/25661322.v6](https://doi.org/10.26188/25661322.v6) | CC BY-NC-SA 4.0 |

Please cite these sources and follow the OKR citation guidance when using derived data. The khipus are cultural heritage of Andean communities, and most were removed from their contexts without record.

Code is licensed under Apache-2.0.
