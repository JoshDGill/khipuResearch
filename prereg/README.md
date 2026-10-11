# Pre-registrations

One YAML file per test, validated by `src/hypotheses/prereg.py`. Commit the file **before** running the test on the corpus. `make prereg-check` verifies that every result names prereg IDs that were committed before the run and were not changed afterwards.

- `P<phase>-NNN`: Phase 1 reproductions of published results, each with a fixed tolerance.
- `H-NNN`: Phase 2/3 hypotheses, each with null models, a multiple-comparison plan and an out-of-distribution check.

After a run, only `status` and `notes` may change. Any other change needs a new file (for example `H-004v2.yaml`) with `supersedes: H-004` and the reason in `notes`. The status `accepted` does not exist in the schema, because only the human review gate can accept a claim.
