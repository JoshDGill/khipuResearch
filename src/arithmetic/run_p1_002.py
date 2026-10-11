"""Run pre-registered test P1-002 (share of khipus with an Ascher sum relation).

    python -m arithmetic.run_p1_002
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from arithmetic.sums import DETECTORS, RELATIONS, Khipu, group_totals, top_cord_sums
from arithmetic.sums import build_khipus as build
from hypotheses.prereg import load
from khipu import paths
from khipu.runlog import start_run
from steward.crosswalk import OUT_CROSSWALK
from steward.okr import OUT_DIR as OKR

PREREG = "P1-002"
KFG_COUNTS = {"R1": 8088, "R2": 3023, "R3": 4746, "R4": 767, "R5": 149, "R6": 315, "R7": 103}


def shares(hits: pd.DataFrame, cols: list[str]) -> tuple[int, float, list[float]]:
    k = int(hits[cols].gt(0).any(axis=1).sum())
    n = len(hits)
    lo, hi = proportion_confint(k, n, method="wilson")
    return k, k / n, [float(lo), float(hi)]


def ge10(name: str, k: Khipu, hits: set[int]) -> int:
    """Sensitivity: count only relations whose sum value is >= 10."""
    if name in ("R1", "R2", "R3"):
        return sum(1 for i in hits if k.values[i] >= 10)
    if name == "R4":
        return sum(1 for j in hits if k.subs[j][0] >= 10)
    if name == "R5":
        return sum(1 for g in hits
                   if sum(k.values[i] for i in k.groups[g][: len(k.groups[g]) // 2]) >= 10)
    if name == "R6":
        totals = group_totals(k)
        return sum(1 for g in hits if totals[g] >= 10)
    return len(hits)  # R7 is an ordering, not a sum


def main() -> int:
    reg = load(paths.PREREG / f"{PREREG}.yaml")
    inputs = [OKR / f"{t}.parquet" for t in ("cord", "knot", "ascher_cord_color")] + [
        OUT_CROSSWALK]
    out = start_run(PREREG, reg.seed, [PREREG], inputs)

    cord, knot, color = (pd.read_parquet(p) for p in inputs[:3])
    xw = pd.read_csv(OUT_CROSSWALK)
    dups = set(xw.loc[xw["duplicate_of"].notna(), "kh"])
    khipus = build(cord, knot, color, exclude=dups)
    eligible = {kh: k for kh, k in khipus.items()
                if any(not np.isnan(v) for v in k.values)}

    rows, instances = [], []
    for kh, k in sorted(eligible.items()):
        row = {"kh": kh, "pendants": len(k.values), "groups": len(k.groups)}
        for name in RELATIONS:
            hits = DETECTORS[name](k)
            row[name] = len(hits)
            row[f"{name}_ge10"] = ge10(name, k, hits)
            instances += [{"kh": kh, "relation": name, "index": int(i)} for i in sorted(hits)]
        row["top_cord_sums"] = len(top_cord_sums(k))
        rows.append(row)
    hits = pd.DataFrame(rows)

    k7, x, ci = shares(hits, RELATIONS)
    tol = reg.tolerance
    summary = {
        "prereg": PREREG,
        "eligible_khipus": len(hits),
        "excluded_duplicates": sorted(dups),
        "khipus_with_relation": k7,
        "share": x,
        "share_ci95_wilson": ci,
        "tolerance": tol.accept_if,
        "inside_tolerance": bool(eval(tol.accept_if, {"__builtins__": {}}, {"x": x})),
        "per_relation": {
            r: {"khipus": int((hits[r] > 0).sum()), "share": float((hits[r] > 0).mean()),
                "instances": int(hits[r].sum()), "kfg_instances": KFG_COUNTS[r]}
            for r in RELATIONS
        },
        "sensitivity": {
            "sum_relations_only_R1_R6": shares(hits, RELATIONS[:6])[1],
            "with_top_cord_sums": float(
                (hits[RELATIONS].gt(0).any(axis=1) | (hits["top_cord_sums"] > 0)).mean()),
            "sum_value_ge10": shares(hits, [f"{r}_ge10" for r in RELATIONS])[1],
            "kfg_values": "pending: KFG download not complete",
        },
        "null_models": "deferred to Phase 2 per prereg; this share is not evidence of design",
    }
    hits.to_csv(out / "khipus.csv", index=False)
    pd.DataFrame(instances).to_csv(out / "instances.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
