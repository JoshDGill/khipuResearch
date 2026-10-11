# Khipu Decipherment Project: Codex Brief

> Rename to `AGENTS.md` if you want Codex to load it automatically from the repo root.

## 0. How to use this file

You are building a reproducible, AI-assisted research pipeline for studying Inka khipus (quipu), the knotted-cord records of the Andes. The work is organized as a set of **roles** (Section 6). Implement each role as a module, script or notebook in the repo layout of Section 5, and run them in the phase order of Section 8.

**Prime directive:** this corpus has almost no ground truth. Every finding is a *hypothesis* until it beats null models on held-out data. A null result is an acceptable outcome. Never present a pattern as a "reading".

---

## 1. Background (what is already known)

- Khipus are knotted-cord records used by the Wari (c. 600-1000 CE) and Inka (c. 1400-1532) and in post-Inka use. Roughly **1,650-1,721** survive (Thompson, *Advances in Archaeological Practice* 13(2), 2025). About 750 are in South America, 300 in North America, 610 in Europe.
- **Solved:** Inka base-10 knot numbers (Locke, 1912/1923). Single overhand knots encode tens and higher places by position. Long knots with 2-9 turns encode units 2-9. Figure-eight = 1. An empty position = 0. Top cords often sum pendant groups. (Overmann & Florio 2025 argue the system may be additive rather than truly positional; minority view.)
- **Ascher relations** (Marcia & Robert Ascher): arithmetic links between cords. Medrano & Khosla (*Latin American Antiquity*, 2024/2025) found sum relations in at least **74%** of a 650-khipu corpus.
- **Proposed but NOT accepted as decipherment:**
  - Urton (2003): binary choices (fiber, spin/ply, recto/verso, S/Z knots) may encode information.
  - Urton & Brezine (*Science*, 2005): three-level accounting hierarchy at Puruchuco; a figure-eight-knot "toponym" (hypothesis only).
  - Medrano & Urton (*Ethnohistory* 65(1), 2018): recto/verso attachment encodes moiety (*hanan*/*hurin*) on six Santa Valley khipus matched to a 1670 census. FitzPatrick (*Ethnohistory* 71(4), 2024) found a stronger fit with verso = *hanan*, recto = *hurin*.
  - Hyland (*Current Anthropology* 58(3), 2017): logosyllabic signs on two 18th-century Collata khipus (colonial, post-Inka). 95 colour/fibre/ply combinations. Read the cords as the lineage name *Alluka*.
  - Urton & Chu (2015, 2019): fixed deductions (10 or 15 on chili khipus, 47 or 208 on peanut khipus) at Inkawasi, interpreted as a tax. UR267B uses a fixed value of 10.
  - Clindaniel (Harvard PhD, 2019): computational/semiotic claims about non-numerical signs; not independently replicated.
  - Thompson (*Nawpa Pacha*, 2025): KH0082 and KH0083 record the same data in different arrangements (10x7 vs 7x10 groups, red/white dividers, an apparent "shortcut" knot for 9).
  - FitzPatrick (*LAQ*, 2026): mathematical knot theory suggests visually different knots may be topologically equivalent.
  - Contreras (arXiv 2607.00185, July 2026, **single-author preprint, not peer reviewed**): UMAP + HDBSCAN on 27 features of 619 OKR khipus; three clusters; XGBoost classifier for Inka Late Horizon F1 = 0.86 (overall weighted F1 0.46); reproduced the Santa Valley recto/verso split from OKR data alone.
- **Undeciphered:** no narrative khipu has been read. No non-numerical sign is accepted across the field. Wari wrapped khipus are entirely unread.

---

## 2. Assumptions

1. OKR and KFG data are accurate enough to model but carry legacy errors. Every value must be traceable to its source file and row.
2. Base-10 knot numbers and Ascher sum relations are settled. They are the **baseline**, not the discovery.
3. The corpus is biased toward coastal, looted, museum-held khipus (collector and recording-style effects). Wari and post-Inka khipus are underrepresented.
4. Ground truth is scarce. The only anchors are Santa Valley, Inkawasi, KH0082/KH0083, Puruchuco and Collata.
5. A pattern is not a meaning. Only prediction on held-out data counts as support.
6. Non-numerical decipherment is unproven. A null result is acceptable.
7. Counts below are approximate and drawn from different snapshots (OKR core 619; KFG 651 analysed, site now reports 703). Do not hard-code them; recompute from the data you download.

## 3. Goals

1. **Rebuild**: reproduce known results (base-10 values, ~74% sum relations, Santa Valley moiety split) from the raw data.
2. **Extend**: apply the same methods to unanchored khipus.
3. **Hypothesize**: propose non-numerical sign meanings only where results survive the controls.
4. **Document**: record failures and null results as carefully as successes.

**Success criteria:** Phase 1 reproduces published numbers within stated tolerances. Every Phase 2/3 claim has a pre-registered test, a null-model comparison, an out-of-distribution check and a replication by a second pipeline.

---

## 4. Data sources

| Source | Use | Access |
|---|---|---|
| **Open Khipu Repository (OKR)** | Primary raw data. SQLite `khipu.db`; ~619 khipus, ~54,403 cords, ~110,677 knots in core DB; KH numbers to KH0702. MIT license. | https://github.com/khipulab/open-khipu-repository ; Zenodo DOI 10.5281/zenodo.18025748 (https://zenodo.org/records/18025748) |
| **Khipu Field Guide (KFG)** | Cleaned, analysis-ready Excel file per khipu (sheets: Khipu, PrimaryCord, Cord Groups, Cords). 703 well-formed khipus per its Databook. | https://khipufieldguide.com/ ; spec: https://khipufieldguide.com/databook/KFGExcelSpecification.html ; build notes: https://khipufieldguide.com/databook/DatabaseBuild.html |
| **Khipu-Biblio Cross-Reference (KBCR)** | Census and literature coverage; shows ~504 literature-mentioned khipus absent from open databases. | figshare DOIs 10.26188/25661322 and 10.26188/28786049 |
| **Harvard KDB (legacy)** | Website is offline. Historical only. Unofficial MySQL/CSV mirror (licence unclear). Prefer OKR. | https://github.com/rdfgiraldez/KhipuAnalysis |
| **Ascher Code of the Quipu databooks** | Descriptions of AS001-AS215. Already in OKR/KFG. | https://courses.cit.cornell.edu/quipu/ |
| **Clindaniel dissertation + code/data** | Inkawasi khipu data. | https://dash.harvard.edu/entities/publication/9d33330d-3b2b-4fec-a8f1-91c310ba2034 |
| **Museum portals** | Images and provenance only; no machine-readable knot data. | Berlin SMB museum-digital (e.g. https://smb.museum-digital.de/object/28130); Dumbarton Oaks "Written in Knots" |
| **Existing code** | Reference only; audit assumptions before reuse. | https://adafieno.github.io/khipu-computational-toolkit/ ; `khipu-ml` (Contreras 2026); MIT CSAIL KhipuDB API |
| **Colonial documents** | Candidate external anchors (revisitas, *Textos Andinos*, paper khipus). | Sourced by the Archivist role |

**OKR schema notes:** tables include `khipu_main`, `primary_cord`, `cord`, `cord_cluster`, `knot`, `knot_cluster`, `ascher_cord_color`, plus `*_dc` code-description tables. `okr-kh-numbers.csv` is the master list of KH IDs.

**Naming:** use neutral **KH numbers** as primary identifiers (Brezine et al., "A New Naming Convention for Andean Khipus", LAQ 2024). Keep a crosswalk to legacy codes (UR, AS, etc.).

**Known data issues to handle explicitly:**
- 14 KFG khipus have no knots.
- ~188 lack recorded knot twist; ~136-140 lack ply/spin (heavy overlap; union ~190).
- ~135+ Harvard KDB records were malformed.
- 15 duplicate re-recordings (e.g. UR035/AS070 = KH0083; UR176/LL01 = KH0001) must be merged.
- KH0082: ~1,831 cords, missing object, possible splicing error, no ply/spin data.
- KH0083: pendants moved for display, so spacing is unreliable.
- Collata khipus are **not** in OKR and need separate encoding.
- Counts of "recto/verso" etc. for Santa Valley conflict across sources (e.g. 132 vs 133 six-cord groups); record both.

## 5. Suggested repository layout

```
khipu/
  AGENTS.md                  # this file
  data/
    raw/                     # untouched downloads (OKR, KFG, KBCR), with checksums
    interim/
    clean/                   # steward output (one table + quality flags)
    anchors/                 # Santa Valley, Inkawasi, KH0082/83, Puruchuco, Collata
    controls/                # synthetic + rule-scrambled corpora
  src/
    steward/                 # loading, reconciliation, QA
    hypotheses/
    arithmetic/              # Modeler A
    sequence/                # Modeler B
    alignment/               # Modeler C
    archive/                 # Archivist tools
    redteam/                 # null models, shuffles, leakage checks
  prereg/                    # pre-registered hypotheses (YAML), timestamped, committed BEFORE runs
  results/
  reports/
  tests/
  environment.yml / pyproject.toml
  Makefile                   # make data | make phase1 | make phase2 | make report
```

Engineering rules: Python 3.11+, fixed random seeds, pinned dependencies, every result reproducible with one `make` target, raw data never edited in place, every transform logged.

---

## 6. Roles and prompts

### Shared preamble (prepend to every role prompt)

```
You are part of a khipu decipherment team. Claims are hypotheses until
they beat null models on held-out data. Cite the khipu (KH number),
source file and row for every value you use. Report failures and
uncertainty plainly. Never state an interpretation as a reading.
```

### 6.1 Data steward (`src/steward/`)

```
Load OKR khipu.db and the KFG Excel files. Reconcile them by KH number,
merging known duplicates (e.g. UR035/AS070 = KH0083). Flag khipus with no
knots (14), missing ply/spin or knot direction (~190), and malformed or
suspect records (e.g. KH0082 splicing). Output one clean table plus a
quality-flag column and a log of every change. Do not repair values
silently.
```
**Deliverables:** `data/clean/khipu_clean.parquet`; `data/clean/quality_flags.csv`; `reports/steward_changelog.md`; unit tests asserting row counts, ID uniqueness and duplicate merges. Record which source (OKR vs KFG) each value came from.

### 6.2 Hypothesis generator (`src/hypotheses/`)

```
Read the provided literature summaries and the clean corpus. Propose up to
10 testable hypotheses about khipu structure or meaning. For each, state:
the claim, the features it uses, the prediction it makes on held-out
khipus, and what result would refute it. Rank by testability. Do not
propose hypotheses that cannot be falsified with the available data.
```
**Deliverable:** `prereg/H-XXX.yaml` files (claim, features, held-out prediction, refutation criterion, planned test, null model, date), committed before any model runs.

### 6.3 Modeler A: arithmetic (`src/arithmetic/`)

```
Search the corpus for sum relations, fixed deductions and cross-khipu
numerical links (like KH0082/KH0083). Reproduce the ~74% sum-relation
result first. Then report new relations with their match rate against
shuffled-cord baselines. Use constraint solvers where useful. Report
effect sizes, not just p-values.
```
**Notes:** compute cord values from knot type and position (Locke rules) first; sum relations include pendant-to-top-cord and subsidiary-to-pendant. Test white pendants as sum-cluster boundary markers (Medrano & Khosla). Test fixed-deduction patterns (Inkawasi chili/peanut khipus). Use only khipus with computable values (~637 expected; recompute).

### 6.4 Modeler B: sequence and grammar (`src/sequence/`)

```
Tokenize cords (color, fiber, ply, attachment, position, knot type). Train
models to predict held-out cords. Test whether non-numerical features add
predictive power beyond numerical values alone. Run every experiment on
the real corpus and on a rule-scrambled copy. Report only gains that
vanish on the scrambled data.
```
**Notes:** restrict semantics tests (S/Z, ply, spin) to the ~460 attribute-complete khipus; exclude flagged records. Include a numbers-only baseline model so any gain from colour/attachment/twist is measurable. Split by khipu (and by site/collection) to prevent leakage. Control for collector and museum recording style.

### 6.5 Modeler C: document alignment (`src/alignment/`)

```
Given an archive-supplied colonial record (census, tribute list), search
for khipu structures that match its counts, groupings and totals.
Evaluate each match against the chance rate for matches of that size
across the corpus. Rank candidates; flag any that rely on a single khipu
or on post-hoc grouping choices.
```
**Notes:** first reproduce the Santa Valley match (KH0323-KH0328 vs the 1670 revisita of 132 tributaries) as the positive control, then search for new matches. Penalize flexible grouping choices (multiple-comparisons correction).

### 6.6 Archivist (`src/archive/`)

```
Find colonial and archaeological documents that could anchor khipus:
revisitas, Textos Andinos, paper khipus, excavation records. For each,
record the khipu or site it might connect to, the evidence, and how
independent it is from our model training data. Mark mid-colonial
documents as weaker anchors for Inka-era khipus.
```
**Deliverable:** `data/anchors/anchor_register.csv` (anchor, khipu IDs, evidence, independence rating, date of document, strength).

### 6.7 Red team (`src/redteam/`)

```
Before any model runs, pre-register each hypothesis and its test. After
results, attack them: shuffle labels, check confounds (collector,
region, museum recording style), test out-of-distribution (coastal rule
on Inkawasi), and look for leakage between training and test. Issue a
pass/fail verdict with reasons. A claim you cannot break must still be
replicated by a second pipeline.
```
**Deliverable:** `reports/redteam_verdicts.md` with pass/fail per hypothesis, the tests run, and reasons.

### 6.8 Human review gate (not automated)

```
You receive only claims that passed red-team review. For each, decide:
plausible in Andean context, consistent with known colonial sources, and
worth a physical or archival follow-up. Reject anything resting on one
khipu or one anchor.
```
Codex should generate a review packet (claim, evidence, tests, caveats) and stop. It must not mark anything as accepted.

---

## 7. Modeling tracks and null models

**Tracks:** (1) arithmetic, (2) sequence/grammar, (3) document alignment (Sections 6.3-6.5).

**Required null models for every experiment:**
- shuffled cord order within khipu
- shuffled labels (colour, attachment, twist) across khipus
- **rule-scrambled corpus**: synthetic copies preserving marginal distributions but destroying the hypothesized structure
- synthetic khipus generated with a *known* rule, to confirm the method can recover it
- chance-rate baseline for alignment matches of equal size

Report effect sizes with confidence intervals, not only p-values. Apply multiple-comparison correction across hypotheses.

## 8. Phases

**Phase 1: Rebuild.** Steward output; reproduce base-10 values, the ~74% sum-relation rate, and the Santa Valley recto/verso split (published ~47% recto / 53% verso; Contreras got 49/51 from OKR with KH0326 mixed). Tolerances must be set in `prereg/` before running. If baselines do not reproduce, stop and debug the data.

**Phase 2: Extend.** Run the same methods on unanchored khipus. Test: new sum relations; cross-khipu links; whether non-numerical features add predictive power. Examples to include: Puruchuco group (e.g. KH0298/UR061, KH0305/UR068, KH0302/UR065), Inkawasi (UR267B), KH0082/KH0083.

**Phase 3: Hypothesize.** Only from results that passed controls. Phonetic or sign-meaning hypotheses stay specific to Collata-type material until replicated on Inka material.

**Stop-and-escalate rule:** halt and escalate to a human whenever a claim depends on a single khipu or a single anchor.

## 9. Validation techniques (all required)

1. **Hold-out anchors:** train without Santa Valley; check whether the moiety split is rediscovered blind.
2. **Null baselines:** a claim counts only if it beats shuffled cords and the rule-scrambled corpus.
3. **Out-of-distribution:** a rule found on coastal khipus must hold on Inkawasi (and vice versa where data allow).
4. **Pre-registration:** hypothesis and test committed before the run (`prereg/`).
5. **Prediction tests:** predict a missing or masked cord's value (the 74% sum-relation work is the model for this).
6. **Replication:** a second, independently written pipeline must reproduce each finding.
7. **Leakage audit:** split by khipu, site and collection; check duplicates across the split.
8. **Confound controls:** collector, museum, region, recording style, data-completeness flags.

## 10. Reconstruction-count deliverable

Produce `reports/reconstruction_counts.md` computed from the data (do not copy these numbers; they are targets to compare against):

| Tier | Expected (approx.) |
|---|---|
| Known surviving khipus | ~1,650-1,721 |
| With any digital record | ~650-703 |
| Cord- and knot-level data, drawable and consistent | ~640 (range 619-703) |
| Numerical values computable | ~637 |
| Fully attribute-complete (colour, attachment, ply/spin, knot direction) | ~460 |
| Partially documented or needing repair | ~135+ |
| No public digital data | ~1,000 |

Document the definition of "reconstructable" and every exclusion rule.

## 11. Deliverables

- Clean, versioned dataset and quality flags
- Reproduction report for Phase 1 baselines
- Pre-registered hypothesis files and red-team verdicts
- Per-track result reports with effect sizes and null comparisons
- Anchor register
- Reconstruction count report
- A final report that lists **what failed** alongside what worked, and what remains undeciphered

## 12. Ethics and conduct

- Treat the khipus as cultural heritage of Andean communities. Do not present speculative readings as fact; flag provenance gaps (most khipus were looted without context).
- Respect database licences (OKR is MIT; check KFG and others). Cite sources for all data.
- The OKR board distances itself from the conduct of a former principal (Gary Urton). Credit data via citations and the OKR citation guidance; do not remove attribution.
- Do not scrape sources whose terms forbid it; ask for access where needed.

## 13. Known caveats

- Contreras (2026) is a single-author preprint, not peer reviewed.
- Hyland's Collata work concerns colonial-era khipus and may not generalize to Inka cotton khipus.
- Clindaniel's claims have not been independently replicated.
- The Puruchuco seven-khipu accounting set could not be verified online; UR063 is commonly cited as top-level. Verify before using as an anchor.
- Some counts above come from different database snapshots and will not match exactly.
- A "complete" record is not the same as an accurate record of the physical object.

## 14. Key references

- Locke (1923), *The Ancient Quipu or Peruvian Knot Record*
- Ascher & Ascher (1981), *Code of the Quipu*
- Urton (2003), *Signs of the Inka Khipu*; Urton & Brezine (2005), *Science*
- Brokaw (2010), *A History of the Khipu*
- Medrano & Urton (2018), *Ethnohistory* 65(1); FitzPatrick (2024), *Ethnohistory* 71(4)
- Hyland (2017), *Current Anthropology* 58(3)
- Medrano & Khosla (2024/2025), *Latin American Antiquity*
- Thompson (2025), *Advances in Archaeological Practice* 13(2); *Nawpa Pacha* 2025
- Brezine et al. (2024), "A New Naming Convention for Andean Khipus", *LAQ*
- Clindaniel (2019), Harvard PhD dissertation
- FitzPatrick (2026), *LAQ*; Contreras (2026), arXiv 2607.00185
