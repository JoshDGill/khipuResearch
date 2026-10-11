# Khipu Decipherment Project: Execution Plan

This plan turns [`AGENTS.md`](../AGENTS.md) (the "brief") into ordered, gated work. Section references like §6.3 point to the brief. The brief stays authoritative on scientific rules. This plan decides **order, gates, ownership and how each rule is enforced in code**.

Prime directive, restated because it shapes every gate below: a pattern is a hypothesis until it beats null models on held-out data. A null result is a valid outcome and is reported with the same care as a positive one.

---

## 1. Starting position (verified 2026-10-11)

| Item | Status |
|---|---|
| Repository | `JoshDGill/khipuResearch`, contains LICENSE + README only. Layout of §5 will be created at repo root (repo root = `khipu/`). |
| OKR | Pinned to the Zenodo release v2.1.0 (2025-12-22, DOI 10.5281/zenodo.18025748). Its file set and `khipu.db` are byte-identical to git master `4039ca5` (2026-08-04). `khipu.db` = 39 MB SQLite. |
| KFG, Zenodo, figshare (KBCR), arXiv | Reachable since 2026-10-11 after a network policy change (D1). KFG serves one Excel file per khipu at `databook/excel_khipus/<KH>.xlsx` (697 IDs on its index). Its robots.txt asks for a 10 s crawl delay, which the fetcher honours. KBCR is CC BY-NC-SA 4.0. |
| Python | 3.13 and `uv` available in the container. Plan targets Python ≥3.11 per §5. |

**First look at OKR `khipu.db`** (informational only; Phase 1 recomputes everything under test):

- `khipu_main` 619 rows, every row has a unique `OKR_NUM` (KH number). `cord` 54,403; `knot` 110,677; `cord_cluster` 14,847; `knot_cluster` 60,169; `primary_cord` 633 (some khipus have more than one primary cord).
- 7 khipus have no cords and 26 have no knots. The brief says 14 have no knots, but that is a KFG figure, so the two definitions must be reconciled rather than one number trusted.
- Missingness is large. Attachment is `U` (unknown) or blank on about 26k of 54k cords. Cord twist is `U` or blank on about 9.4k cords. Knot direction is `U` on about 12.5k knots. This directly limits the recto/verso and S/Z work. The "~460 attribute-complete" tier must be recomputed under an explicit definition.
- `DUPLICATE_FLAG` is NULL on 97 rows and 0 on 522. Duplicate handling cannot rely on this flag alone.
- Post-2017 additions (KH0631–KH0702) are mostly separate `.xlsx`, `.pdf`, `.docx` and `.jpg` files **not loaded into `khipu.db`**. Some (for example KH0653–KH0663) exist only as images. These need a separate ingestion path, and the image-only ones are out of scope unless transcribed by hand.
- `okr-kh-numbers.csv` contains quoted multi-line fields, so it must be parsed with a real CSV parser.
- Santa Valley (KH0323–KH0328 = UR087–UR092), Puruchuco/Huaquerones (KH0298, KH0302), KH0305 (provenance blank), KH0082 (AS069) and KH0083 (AS070/UR035) are all present in OKR.

---

## 2. Work breakdown and dependency order

```
Phase 0  Setup ─────────────┐
                            ▼
Phase 1  Steward ──► Reconstruction counts
            │
            ├──► Prereg P1 tolerances ──► Reproduce: base-10 │ 74% sums │ Santa Valley
            │                                     │
            │                              GATE G1 (all reproduce, or stop & debug)
            ▼                                     ▼
Phase 2  Null-model toolkit + known-rule recovery ── GATE G2 (methods recover planted rules)
            │
            ├──► Hypothesis generator ──► prereg/H-*.yaml committed ── GATE G3 (prereg lint)
            │
            ├──► Modeler A (arithmetic)   ┐
            ├──► Modeler B (sequence)     ├──► Red team ──► Replication pipeline ── GATE G4
            ├──► Modeler C (alignment) ◄──┤
            └──► Archivist (runs in parallel from Phase 1 onward, feeds C)
                                          ▼
Phase 3  Hypothesize (only G4 survivors) ──► Human review packet (STOP) ──► Final report
```

The archivist and the data-access requests start as soon as Phase 0 is done, because colonial-document anchors take the longest to obtain.

---

## 3. Phase 0: Setup

**Goal:** an empty-but-runnable pipeline where `make data` fetches and checksums raw sources.

| # | Task | Output | Done when |
|---|---|---|---|
| 0.1 | Scaffold §5 layout at repo root | `data/{raw,interim,clean,anchors,controls}`, `src/{steward,hypotheses,arithmetic,sequence,alignment,archive,redteam}`, `prereg/`, `results/`, `reports/`, `tests/` | Tree exists; `src/` is an installable package (`khipu`) |
| 0.2 | Environment | `pyproject.toml` + `uv.lock` (pinned). Core deps: pandas, pyarrow, numpy, scipy, statsmodels, scikit-learn, openpyxl, pydantic, pyyaml, ortools (constraint solving), pytest, ruff | `uv sync --frozen` works from clean |
| 0.3 | Agent instructions | Brief copied to `AGENTS.md` (Codex) plus `CLAUDE.md` that imports it, so both tools load the same rules | Both files present |
| 0.4 | Raw-data fetcher | `src/steward/fetch.py` driven by `data/sources.yaml`: OKR from Zenodo v2.1.0 (md5-verified), KBCR from figshare (md5-verified), KFG per-khipu Excel files, writes `data/raw/MANIFEST.csv` (source, URL, version, sha256, retrieved_at, licence) | `make data` is idempotent and re-verifies checksums |
| 0.5 | Raw-data policy | `data/raw/` is git-ignored except the manifest (39 MB DB + KFG files do not belong in git). Optionally use git-LFS or DVC later | A pre-commit hook rejects edits under `data/raw/` |
| 0.6 | Provenance primitive | `Provenance(source, file, table/sheet, row_key)` type carried on every value through transforms | Unit-tested; required by every steward output column |
| 0.7 | Makefile | `make data`, `make clean-data`, `make phase1`, `make phase2`, `make report`, `make test`, `make prereg-check` | Targets exist, stubs fail loudly |
| 0.8 | CI | GitHub Actions: ruff, pytest, `prereg-check` (see §7) on a tiny fixture DB, not the full corpus | Green on `main` |
| 0.9 | Seeds and run log | `src/khipu/runlog.py`: every run records git SHA, seed, input checksums and the prereg IDs it serves into `results/<run_id>/run.json` | Every result folder has a `run.json` |

---

## 4. Phase 1: Rebuild

### 4.1 Data steward (§6.1)

Build in this order. Each step is one logged transform.

1. **Load OKR** `khipu.db` into typed interim tables, keyed by `KHIPU_ID` and mapped to KH number. Decode all `*_dc` code tables. Keep sentinel values (`U`, `''`, `NULL`, the literal `'null'`, `"''"`) as explicit categories in interim. They are mapped to missing only in `clean`, with a flag.
2. **Load post-2017 OKR spreadsheets** (KH0631–KH0702) through per-source adapters. Image-only and PDF-only records are logged as `no_machine_readable_data`.
3. **Load KFG** Excel files (Khipu, PrimaryCord, Cord Groups, Cords sheets) per its published spec. This step is blocked until D1 is resolved. Until then, Phase 1 runs OKR-only and says so in every report.
4. **Crosswalk.** `data/clean/id_crosswalk.csv` maps KH ↔ OKR internal ID ↔ UR/AS/LL/JC/etc. ↔ KFG name, built from `okr-kh-numbers.csv` "Other Names" plus `INVESTIGATOR_NUM`.
5. **Duplicate merge.** Merge the 15 known re-recordings (for example UR035/AS070 = KH0083; UR176/LL01 = KH0001). Keep both recordings in interim and select or merge into clean by a documented rule. Disagreements between recordings become a quality signal (a free estimate of recording error).
6. **Reconcile OKR and KFG** value-by-value. Every disagreement is written to `data/interim/okr_kfg_diffs.parquet`. The clean value is chosen by rule (default: OKR raw, KFG only where OKR is missing), and `value_source` records which one won.
7. **Quality flags** (never silent repair): `no_cords`, `no_knots`, `missing_twist`, `missing_ply_spin`, `missing_knot_direction`, `missing_attachment`, `malformed_record`, `suspect_splice` (KH0082), `spacing_unreliable` (KH0083), `duplicate_merged`, `post2017_adapter`, `conflicting_counts`.
8. **Outputs**: `data/clean/khipu_clean.parquet` (long cord-level table with khipu-level columns and per-value provenance), `data/clean/quality_flags.csv`, `reports/steward_changelog.md` (auto-generated from the transform log).
9. **Tests**: row counts equal source counts minus logged exclusions, KH uniqueness, every known duplicate merged exactly once, no clean value without provenance, and round-trip of 20 hand-checked cords per source.

### 4.2 Reconstruction counts (§10)

Script `src/steward/reconstruction_counts.py` produces `reports/reconstruction_counts.md`. It writes down **definitions first** (what counts as "drawable and consistent", "numerical values computable" and "attribute-complete"). It then computes each tier with the exclusion list for each step and places it next to the brief's approximate targets. If a computed tier differs from the target by more than ±10%, that is investigated and explained, not tuned away.

### 4.3 Phase 1 pre-registration

Before any reproduction code is run against the real corpus, commit `prereg/P1-001..003.yaml` with tolerances:

| ID | Target | Tolerance (approved, D4) |
|---|---|---|
| P1-001 | Locke base-10 cord values | ≥99% agreement with the recorders' own readings (summed per-knot `knot.knot_value_type`). Every mismatch listed with the knot sequence. `TOTAL_VALUE` turned out to be null or 0 on many clusters, so it is reported only as a data-quality figure. |
| P1-002 | Sum relations in ≥74% of the corpus (Medrano & Khosla) | Within ±5 percentage points on a matched corpus definition. Report the corpus size actually used. |
| P1-003 | Santa Valley recto/verso split | Recto share between 45% and 53% (published ~47/53; Contreras 49/51). KH0326 handled both ways. Both the 132 and 133 six-cord-group counts reported. |

### 4.4 Reproductions

- **Base-10 decoder** (`src/arithmetic/decode.py`): Locke rules. Single knots by position give tens and above, long knots with *n* turns give units 2–9, a figure-eight (`E`) gives 1, and an empty position gives 0. `SP`, `TF`, `EE`, `LL`, `BL` and blank types are reported as undecodable, not guessed. Also compute an additive-reading variant (Overmann & Florio) as a sensitivity check.
- **Sum-relation finder** (`src/arithmetic/sums.py`): pendant → top-cord and subsidiary → pendant sums, contiguous and group-level, using the published definition as closely as it can be reconstructed. Any ambiguity in their definition goes into a prereg note *before* the run.
- **Santa Valley** (`src/alignment/santa_valley.py`): attachment by cord over KH0323–KH0328, grouping into six-cord groups, comparison with the 1670 revisita counts.

**GATE G1.** All three are inside tolerance. If not, **stop**: debug data and definitions, log what was wrong, and re-run. Tolerances are never edited after seeing results. A new prereg version with a stated reason is the only allowed change, and it is flagged in the report. Output: `reports/phase1_reproduction.md`. The project owner signs off on G1 (D5); the pipeline does not pass the gate on its own.

---

## 5. Phase 2: Extend

### 5.1 Null-model and control toolkit (`src/redteam/`), built before any Phase 2 hypothesis runs

| Generator | What it preserves | What it destroys |
|---|---|---|
| `shuffle_cord_order` | each khipu's multiset of cords | positional structure within the khipu |
| `shuffle_labels` | the label's marginal distribution, stratified by site/collection | label ↔ cord association across khipus |
| `rule_scramble` | per-khipu marginals (cord count, value distribution, colour frequencies, group sizes) | the specific hypothesised structure (plugin per hypothesis) |
| `plant_rule` | real corpus or scrambled corpus | nothing. It **injects** a known rule at a known strength. |
| `alignment_chance` | the size and shape of a document match | the specific document ↔ khipu link (random target counts of equal size) |

**GATE G2 (method validity):** every modeling method must recover planted rules at the strengths realistically expected, and must not "find" them in the scrambled corpus. Power curves are saved to `results/controls/`. A method that cannot recover a planted rule is not run on real data.

### 5.2 Hypothesis generator and pre-registration (§6.2)

- Up to 10 hypotheses as `prereg/H-NNN.yaml` with a schema enforced by pydantic: `id, claim, features, data_subset + exclusion flags, held_out_split, prediction, refutation_criterion, planned_test, null_models[], effect_size_metric, alpha + correction, ood_check, replication_owner, date, status`.
- Seed candidates already named in the brief: white pendants as sum-cluster boundaries; fixed deductions (10/15 chili, 47/208 peanut, UR267B = 10); KH0082/KH0083 same-data rearrangement; Puruchuco three-level hierarchy (verify UR063 as top-level first, see §13 of the brief); non-numeric features add predictive power over numbers alone; recto/verso = moiety rediscovered blind; S/Z knot direction carries information beyond recorder style.
- **GATE G3:** `make prereg-check` passes. Each hypothesis file is committed in an earlier commit than any `results/` folder that references it (see §7).

### 5.3 Modeler A: arithmetic (§6.3)

Run on khipus with computable values only. Effect sizes are match rate minus null match rate, with bootstrap CIs (resampled by khipu). Constraint solving (OR-Tools CP-SAT) is used for cross-khipu links and fixed-deduction search, with search space size logged so the multiple-comparison burden is explicit. KH0082/KH0083 is the positive control for cross-khipu linking. Output: `reports/track_arithmetic.md`.

### 5.4 Modeler B: sequence and grammar (§6.4)

- Tokens per cord: value, colour, fibre, ply/spin, attachment, position, knot types and directions.
- Models in increasing complexity: frequency baseline → n-gram/CRF → gradient boosting on context windows → small transformer only if simpler models leave signal.
- **Core comparison**: numbers-only model vs. numbers + each non-numeric feature group. The test is masked-cord prediction on held-out khipus.
- Splits: grouped by khipu, and separately by site and by collection (leave-one-group-out). The duplicate crosswalk is used to make sure no physical khipu appears on both sides.
- Covariates and strata: collector/recorder (from `CREATED_BY` and investigator prefix), museum, region, data-completeness flags.
- Restricted to the attribute-complete subset for S/Z, ply and spin semantics. Gains count only if they vanish on the rule-scrambled corpus. Output: `reports/track_sequence.md`.

### 5.5 Modeler C: document alignment (§6.5)

Santa Valley is the positive control: a blind rerun with Santa Valley held out of any feature selection, which is validation technique 1 of §9. The anchor register (5.6) then supplies new targets. Every candidate match is scored against `alignment_chance` for the same match size, the number of grouping choices is counted and penalised (Holm or BH across all choices tried), and the search flags single-khipu and post-hoc-grouping dependencies. Output: `reports/track_alignment.md`.

### 5.6 Archivist (§6.6), parallel from Phase 1

`data/anchors/anchor_register.csv` columns: `anchor_id, document, date, archive/citation, khipu_ids, site, evidence, independence_rating (A–D), strength, mid_colonial (bool), notes`. Start with the five known anchors (Santa Valley, Inkawasi, KH0082/83, Puruchuco, Collata), then look for candidates in *Textos Andinos*, published revisitas and paper khipus. Collata khipus are not in OKR, so they need their own encoding schema in `data/anchors/collata/` from published descriptions (Hyland 2017). Respect source terms: no scraping where it is forbidden.

### 5.7 Red team (§6.7)

For each hypothesis that has results:

1. Re-run every null model.
2. Run confound checks by stratifying on collector, museum, region, recording style and completeness.
3. Run OOD checks: coastal → Inkawasi and back, where data allow.
4. Run a leakage audit.
5. Check the multiple-comparison correction across **all** hypotheses run so far, including failed ones.

The verdict is pass/fail with reasons in `reports/redteam_verdicts.md`. The red team's code is written without importing modeler code beyond the clean dataset.

### 5.8 Replication pipeline (§9.6)

A claim that passes red-team review is re-implemented in `replication/` **from its prereg YAML only**. This is done by a separate agent session that is not shown the original implementation, and preferably with a different stack (for example R or plain SQL for arithmetic claims). **GATE G4:** the finding reproduces within the prereg tolerance, and the project owner signs off (D5).

---

## 6. Phase 3: Hypothesize and report

- Only G4 survivors move on. Sign-meaning or phonetic hypotheses stay scoped to Collata-type material until replicated on Inka material.
- **Stop-and-escalate:** any claim resting on a single khipu or a single anchor halts automatically. `src/redteam/escalate.py` checks the dependency set and writes `reports/escalations.md`.
- **Human review packet** (§6.8): `reports/review_packet/<H-id>.md` with the claim, evidence, all tests and nulls, effect sizes with CIs, caveats, provenance gaps and ethics notes. The pipeline **stops there**. No code path can set `status: accepted`; only a human edit can.
- **Final report** `reports/final_report.md`: what reproduced, what failed (with the same detail), the null results, what remains undeciphered, and data limitations, with citations per §12/§14 including OKR's citation guidance.

---

## 7. How the rules are enforced (not just stated)

| Brief requirement | Enforcement |
|---|---|
| Pre-registration before runs (§9.4) | `make prereg-check` in CI: every `results/*/run.json` names prereg IDs, and `git log` shows each prereg file's first commit is an ancestor of the commit that produced the result. Edits to a prereg after results exist must create a new version with a `supersedes` field. |
| Traceability (§2.1) | Provenance columns are required by the clean-table schema. Tests fail on any null provenance. |
| Fixed seeds, pinned deps, one `make` per result (§5) | `run.json` records seed, lockfile hash and git SHA. `make report` rebuilds every report from `results/`. |
| Null baselines on every experiment (§7) | The experiment runner refuses to write a result without the null models listed in its prereg. |
| Multiple-comparison correction (§7) | A central ledger `results/hypothesis_ledger.csv` holds every test run, pass or fail. Corrections are computed over the whole ledger. |
| Leakage audit (§9.7) | A split builder asserts there is no KH or crosswalk-duplicate overlap and logs site/collection overlap. |
| No "readings" (§0) | The report templates use "hypothesis"/"pattern" language. A lint step greps reports for "reads as", "means", "deciphered" and similar phrases, and fails unless quoted from literature. |
| Human-only acceptance (§6.8) | The `status: accepted` value is rejected by the prereg schema when written by the pipeline. |

---

## 8. Decisions

Recorded 2026-10-11.

| ID | Decision | Outcome |
|---|---|---|
| D1 | Data access for KFG (`khipufieldguide.com`), Zenodo, figshare (KBCR) and arXiv | **Resolved.** Hosts allowed in the environment's network policy, all verified reachable. |
| D2 | Push access to `khipuResearch` | **Resolved.** Claude GitHub App can push and open PRs. |
| D3 | Raw-data storage | **Decided:** git-ignored `data/raw/` + checksummed `data/raw/MANIFEST.csv`. |
| D4 | Phase 1 tolerances in §4.3 | **Approved as proposed.** |
| D5 | Sign-off on G1 and G4 | **Project owner (Josh Gill)** signs off on both gates. The pipeline prepares the evidence and stops; it does not pass a gate on its own. |
| D6 | Replication independence | Default applies (not separately discussed): separate agent session working from the prereg YAML only, different stack where practical. |
| D7 | Licensing | Default applies (not separately discussed): code Apache-2.0 per LICENSE; derived data carries upstream licences and citations. KFG licence still to be checked by the fetcher step. |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Published 74% / Santa Valley definitions can't be reconstructed exactly | Pre-register our interpretation and its ambiguities. Report a sensitivity range rather than one number. If outside tolerance, G1 stops the project for debugging rather than moving on. |
| Heavy attribute missingness (attachment unknown on roughly half of cords) | Analyses run on explicitly defined complete subsets, with missingness itself tested as a confound (recorder style). |
| Recorder/collection effects masquerading as meaning | Stratified nulls and leave-one-collection-out splits. Recorder is always a covariate. |
| Garden of forking paths in alignment and constraint search | Count and log all grouping choices. Ledger-wide correction. Chance-rate baselines of equal size. |
| Small anchor set (5) → single-anchor claims | Automatic stop-and-escalate. No claim is promoted on one anchor. |
| Replication not truly independent when the same assistant writes both | Replication works from the prereg YAML only, in a fresh session with a different stack, and disagreements are reported. |
| Ethics and provenance (looted objects, contested attribution) | Provenance gaps flagged per khipu. Citation and attribution kept per OKR guidance. No speculative reading presented as fact. |

---

## 10. First tickets (in order)

1. Phase 0.1–0.3: scaffold, `pyproject.toml`/`uv.lock`, `AGENTS.md` + `CLAUDE.md`.
2. Phase 0.4–0.6: fetcher (OKR Zenodo v2.1.0, KBCR, KFG), manifest with sha256, provenance type.
3. Steward step 1: OKR loader + code-table decoding + sentinel inventory report.
4. Steward steps 4–5: crosswalk + 15-duplicate merge, with tests.
5. Steward step 7: quality flags; first `reports/reconstruction_counts.md` (OKR-only).
6. Commit `prereg/P1-001..003.yaml`.
7. Locke decoder + P1-001 run.
8. Sum-relation finder + P1-002 run.
9. Santa Valley recto/verso + P1-003 run → `reports/phase1_reproduction.md` → Gate G1.
10. Archivist: seed `anchor_register.csv` with the five known anchors (parallel with 3–9).
