@AGENTS.md

# Working in this repo

- `AGENTS.md` is the project brief and is authoritative on scientific rules. `docs/EXECUTION_PLAN.md` sets phase order, gates and how each rule is enforced.
- Never run a test on the corpus before its `prereg/<ID>.yaml` is committed. Results go in `results/<stamp>_<name>/` via `khipu.runlog.start_run`, from a clean tree.
- Never edit files under `data/raw/`. Every transform from raw to clean is logged, and every clean value keeps its provenance columns (`khipu.provenance`).
- Gates G1 and G4 are signed off by the project owner, not by the pipeline. Nothing in code may set a prereg status to `accepted`.
- Use "hypothesis" or "pattern", never "reading" or "meaning", for any finding.

## Commands

- `uv sync` installs the pinned environment.
- `make data` fetches raw sources (KFG honours a 10 s crawl delay, about 3 hours) and verifies checksums.
- `make test`, `make lint`, `make prereg-check` are the checks CI runs.
