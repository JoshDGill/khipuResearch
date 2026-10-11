# Phase 1 reproduction report

**Status: Gate G1 awaiting the owner's decision.** P1-002v2 and P1-003 reproduce (P1-003 signed off; P1-002v2 is a post-hoc revision). P1-001 did not reproduce under either registered rule; its pre-registered refutation clause applies, so cord values come from the recorders' readings with that limitation stated. Phase 2 does not start until the owner signs off G1.

Data: OKR v2.1.0 (Zenodo 10.5281/zenodo.18025748). KFG cross-checks are pending until the KFG download completes.

| Prereg | Target | Tolerance | Result | Verdict |
|---|---|---|---|---|
| P1-001 | Locke base-10 values reproduce the recorders' readings | ≥ 0.99 agreement | **0.937** (95% CI 0.934–0.940), 29,688 cords | **Not reproduced** |
| P1-001v2 | Same, group-aligned place bands (post hoc) | ≥ 0.99 agreement | **0.874** (95% CI 0.870–0.878), 29,337 cords | **Not reproduced** |
| P1-002 | Share of khipus with ≥ 1 Ascher sum relation | 0.69–0.79 | **0.793** (95% CI 0.760–0.824), 484/610 khipus | **Not reproduced** (marginally; components diverge) |
| P1-002v2 | Same, KFG's published criteria on KFG data (post hoc) | 0.69–0.79 **and** median per-relation Jaccard vs KFG ≥ 0.7 | **0.760** (95% CI 0.727–0.790), 528/695; median Jaccard **0.85** | **Reproduced** (post hoc), awaiting sign-off |
| P1-003 | Santa Valley pooled recto share | 0.45–0.53 | **0.479** (95% CI 0.445–0.514), 382/797 pendants | **Reproduced**, signed off; effective n = 6 khipus |

## P1-001: Locke base-10 decoding

Run `results/20261011T152605Z_P1-001/` (code at commit recorded in its `run.json`).

### Result as registered

- 37,082 cords carry knots. 29,688 are eligible under the pre-registered rules. Exclusions: 4,546 have long knots with missing or invalid turn counts, 2,239 have an L/E knot above the lowest cluster, 538 have knot types outside S/L/E, and 71 have malformed units clusters. A further 526 orphan knots reference no cord.
- Agreement with the recorders' own readings is 27,819 of 29,688 = **0.937** (Wilson 95% CI 0.934–0.940). The tolerance is 0.99, so **P1-001 is not reproduced**.
- Pre-registered sensitivity analyses also fail: consecutive-place decoding (no zeros inferred) 0.948, and place spacing estimated per cord group 0.923.

### Debugging (exploratory, after the run; not part of the verdict)

1. **The failure is in place assignment, not digit reading.** On cords with a units knot, the consecutive-place variant agrees on 97.4%. On cords without a units knot it agrees on only 84.7%, because nothing on the cord fixes which place its lowest S cluster belongs to.
2. **The pre-registered zero-place rule over-fires.** It inferred an empty place from cluster spacing where the recorders saw none on 1,113 cords (for example `S@5.5 | L@17.5`, read 12, decoded 102). The tens-to-units gap is systematically larger than gaps between higher places, so one median spacing per khipu is the wrong yardstick.
3. **The rule also misses real zeros.** For example, KH0326 `S@7 | L@17.5` is read as 106. Spacing alone cannot separate these from the cases in point 2.
4. **The reference data contradicts itself in places.** 4.4% of all knots carry a recorded place value inconsistent with their own type or turn count (an L knot with 2 turns recorded as 3, for instance). Most sit on cords that were already ineligible. Only 97 eligible cords are affected, so this is not the main cause.
5. **`knot_cluster.TOTAL_VALUE` is not usable.** Where every cluster on a cord has a value, the total agrees with the recorders' readings on 0.08% of cords. Switching the reference away from it before the run was correct.
6. Mismatches are concentrated. KH0326 has 67 of its 122 cords mismatched, KH0506 62 of 96 and KH0001 36 of 36. 314 of 581 khipus have at least one mismatch.

### What this means

Locke's digit rules are not in question here. Digits read from knot type and count agree wherever place is unambiguous. What failed is this project's operational rule for assigning place from a single cord's geometry. Locke and the Aschers assigned place by aligning knot rows across the cords of a group, which the registered rule does not do.

### Next step (approved by the owner, 2026-10-11)

Register **P1-001v2** (`supersedes: P1-001`) with group-aligned place bands. Within each cord group, cluster the knot positions of all cords into horizontal bands, anchor the units band on L/E knots, and give each S cluster the exponent of its band. The tolerance stays at 0.99. The revision is flagged as post hoc in this report, because its design was informed by the failure above. If v2 also fails, the honest outcome is that recorded positions alone do not determine place for a sizeable minority of cords, and Phase 1 uses the recorders' readings as values, with that limitation stated.

### P1-001v2 result (post hoc, approved 2026-10-11)

Run `results/20261011T154558Z_P1-001v2/`.

- Agreement is 25,637 of 29,337 = **0.874** (Wilson 95% CI 0.870–0.878), below 0.99. **Not reproduced.** Sensitivity analyses: delta at 0.35× gives 0.873, at 0.75× gives 0.843, and bands per khipu give 0.806.
- Cords with a units knot agree on **0.978** (23,603 cords). Cords without one agree on **0.447** (5,734 cords).
- The v2 rule has a design error, found after the run. It let an S-knot cluster take the units place, but recorders almost never do this (only 1% of cords without a units knot have a recorded value below 10). When a group has no units knots, the rule also anchored on the nearest band however far away it was. As a result, 2,681 mismatches are exactly one place too low.
- Fixing this would not reach the tolerance. Cords with a units knot are already capped at 0.978 under both v1 and v2, so no handling of the other 20% can lift the total to 0.99. No v3 is registered.

### Conclusion for P1-001 (both versions)

Neither registered rule reproduces the recorders' readings at 0.99 from OKR knot positions. For cords with a units knot, digit reading plus positional place assignment agrees with the recorders on about 97.5–98%. For cords without a units knot, the recorded geometry does not determine place reliably. Recorders resolved those cases by judgement and alignment that the database does not capture. **Per the pre-registered refutation criterion, Phase 1 and later work use the recorders' readings (`knot_value_type`) as cord values, with this limitation stated.** P1-002 already does so.

## P1-002: Share of khipus with an Ascher sum relation

Run `results/20261011T153032Z_P1-002/`.

### Result as registered

- 610 khipus are eligible: they have at least one computable pendant, and the duplicate KH0483 is excluded. 484 have at least one of R1–R7, a share of **0.793** (Wilson 95% CI 0.760–0.824). The tolerance is 0.69–0.79, so **P1-002 is not reproduced**, by 0.003.
- Sensitivity analyses: sum relations only (R1–R6) give 0.782, adding top-cord sums gives 0.793, and counting only sums ≥ 10 gives 0.716.

### Debugging (exploratory)

The headline share is close to the published ~0.74 and KFG's 0.709, but the components are not. Instance counts compared with the KFG table:

| Relation | This run: khipus | This run: instances | KFG instances |
|---|---:|---:|---:|
| R1 pendant-pendant sum | 448 | 12,983 | 8,088 |
| R2 colour pendant sum | 423 | 12,146 | 3,023 |
| R3 indexed pendant sum | 181 | 615 | 4,746 |
| R4 subsidiary-pendant sum | 238 | 3,818 | 767 |
| R5 group sum band | 68 | 132 | 149 |
| R6 group sum pair | 127 | 896 | 315 |
| R7 decreasing group | 42 | 92 | 103 |

R1, R2, R4 and R6 are 1.6–4× more permissive than KFG's implementation, and R3 is 8× stricter. The pre-registered definitions are this project's reading of one-line descriptions, and they evidently do not match the code that produced the published figures. A near-match on the headline share is therefore partly coincidental, and it should not count as reproduction even if it had landed inside the tolerance.

Note also that any-distance search makes these relations easy to find by chance: R1 alone fires on 73% of khipus. Whether that exceeds a shuffled-cord baseline is the Phase 2 question, and nothing here bears on it.

### Next step (approved by the owner, 2026-10-11)

Obtain KFG's own relation definitions. The KFG notebooks reference `utils_khipu` and a fieldmark CSV (`ascher_sums_overview.csv`), and the authors may share the code. Then register **P1-002v2** implementing them, with the same tolerance. If they cannot be obtained, report P1-002 as not reproducible from published descriptions and carry the definitional uncertainty into Phase 2.

**Done so far.** KFG's detection library (`qollqa_chuspa` and its fieldmark modules) is not public. Its analysis pages do, however, state each relation's search criteria, include code cells for several relations (indexed sums, group-pair significance, the decreasing-group test), and embed the per-khipu outputs as plot data. Together the R1–R7 outputs cover 488 of 654 khipus (**0.746**), which is the source of the ~74% figure. **P1-002v2** (`prereg/P1-002v2.yaml`) implements those criteria, runs on KFG's own data, and adds a co-criterion: the per-relation khipu sets must match KFG's published sets with median Jaccard ≥ 0.7. Several criteria differ materially from this project's P1-002 reading:

- R1 sums must be ≥ 11, zeros are skipped rather than breaking ranges, and ranges are capped at 250 cords.
- R3 drops zeros and skips groups that lack the index position, requires sums > 5, and filters round numbers.
- R6 requires a significant total (≥ 100, or ≥ 11 and not a multiple of 10). The page text says ≥ 21, but the code cell is used.
- R7 is KFG's "roughly linear decreasing" fit (r² > 0.6, slope angle between −87° and −5°), not strict decrease.

### P1-002v2 result (post hoc, approved 2026-10-11)

Run `20261011T171837Z_P1-002v2/`. An earlier run (`20261011T171754Z_P1-002v2/`) crashed with a KeyError before computing anything: one pendant on one KFG khipu lies outside every CordGroups range. The fix rejects runs containing such a pendant, as the adjacent-groups condition requires. The crashed folder is kept with `CRASHED.txt`.

- 695 KFG khipus parsed with no failures. 528 have at least one of R1–R7: **0.760** (Wilson 95% CI 0.727–0.790), inside 0.69–0.79.
- Agreement with KFG's published per-khipu sets (644 khipus in both; 4 published names unmapped: CM009, QU016, QU017, QU019):

| Relation | Ours | KFG | Both | Jaccard |
|---|---:|---:|---:|---:|
| R1 pendant-pendant sum | 422 | 422 | 413 | 0.96 |
| R2 colour pendant sum | 206 | 261 | 182 | 0.64 |
| R3 indexed pendant sum | 223 | 226 | 216 | 0.93 |
| R4 subsidiary-pendant sum | 217 | 132 | 128 | 0.58 |
| R5 group sum band | 94 | 95 | 88 | 0.87 |
| R6 group sum pair | 134 | 94 | 76 | 0.50 |
| R7 decreasing group | 128 | 122 | 115 | 0.85 |

- The median Jaccard is **0.85**, so the co-criterion (≥ 0.7) is met and **P1-002v2 is reproduced**. Three relations still diverge. R4 and R6 flag more khipus than KFG does, which points to unpublished filters, and R2 flags fewer. Their individual Jaccards are reported, not hidden by the median.
- On the same 644 khipus, KFG's own published outputs give a share of 0.748. Sensitivity analyses: OKR values give 0.752, and sum relations only (R1–R6) give 0.734. The top-cord sensitivity was not computed, because KFG publishes no code for it.
- Caveat: this is a post-hoc revision, and it calibrates to KFG's published criteria, not to an independent definition. It shows the published rate can be reproduced from the published method and data. It says nothing yet about whether these relations occur more often than chance, which is the first Phase 2 test.

## P1-003: Santa Valley recto/verso split

Run `results/20261011T153022Z_P1-003/`.

- 811 pendants on KH0323–KH0328 (13 top cords and 254 subsidiaries excluded). 382 recto, 415 verso and 14 unknown, a pooled recto share of **0.479** (Wilson 95% CI 0.445–0.514). The tolerance is 0.45–0.53, so **P1-003 is reproduced**. The project owner signed this off on 2026-10-11, accepting the six-khipu caveat below.
- Sensitivity analyses: excluding KH0326 gives 0.496, and including subsidiaries and top cords gives 0.490.
- **Caveat on precision.** Attachment is constant within five of the six khipus. KH0323 (287 R) and KH0328 (55 R) are all recto. KH0324 (53 V), KH0325 (204 V) and KH0327 (90 V) are all verso. KH0326 is mixed, at 37% recto. The pooled share therefore mostly reflects which khipus are recto and how many cords each has. The effective sample is six khipus, and the cord-level CI overstates precision. This matches the khipu-level reading in the literature (a moiety per khipu, with KH0326 mixed, as Contreras reported).
- **Six-cord groups.** OKR's cord clusters give 39 groups of exactly six pendants (KH0323: 34, KH0325: 4, KH0326: 1), against the 132/133 published. The published count does not use OKR's cluster structure, so the census-matching grouping must be reconstructed from the publication before Modeler C can use Santa Valley as its positive control. No tolerance was set for this count.

## Data limitations carried forward

- The KFG cross-checks (values, attachment) are pending until the KFG download completes.
- The additive reading of Overmann & Florio needs an operational definition before it can be computed.
