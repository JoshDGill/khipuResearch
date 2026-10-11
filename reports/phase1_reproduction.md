# Phase 1 reproduction report

**Status: Gate G1 not passed.** P1-001 is outside its pre-registered tolerance. Under the plan, the project stops at G1 for debugging. G1 is signed off by the project owner, not by the pipeline.

Data: OKR v2.1.0 (Zenodo 10.5281/zenodo.18025748). KFG cross-checks are pending until the KFG download completes.

| Prereg | Target | Tolerance | Result | Verdict |
|---|---|---|---|---|
| P1-001 | Locke base-10 values reproduce the recorders' readings | ≥ 0.99 agreement | **0.937** (95% CI 0.934–0.940), 29,688 cords | **Not reproduced** |
| P1-002 | Share of khipus with ≥ 1 Ascher sum relation | 0.69–0.79 | pending | – |
| P1-003 | Santa Valley pooled recto share | 0.45–0.53 | pending | – |

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

### Proposed next step (needs owner approval)

Register **P1-001v2** (`supersedes: P1-001`) with group-aligned place bands. Within each cord group, cluster the knot positions of all cords into horizontal bands, anchor the units band on L/E knots, and give each S cluster the exponent of its band. The tolerance stays at 0.99. The revision is flagged as post hoc in this report, because its design was informed by the failure above. If v2 also fails, the honest outcome is that recorded positions alone do not determine place for a sizeable minority of cords, and Phase 1 uses the recorders' readings as values, with that limitation stated.
