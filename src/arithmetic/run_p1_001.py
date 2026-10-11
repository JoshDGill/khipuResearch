"""Run pre-registered test P1-001 (Locke base-10 decoding) and write results/.

    python -m arithmetic.run_p1_001

Writes results/<stamp>_P1-001/ with run.json, summary.json, cords.csv (every eligible cord),
mismatches.csv and exclusions.csv. The verdict is computed against the tolerance in the prereg;
Gate G1 is signed off by the project owner, not here.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from arithmetic.decode import (
    cord_clusters,
    decode,
    gaps,
    ineligibility,
    spacing_by,
)
from hypotheses.prereg import load
from khipu import paths
from khipu.runlog import start_run
from steward.okr import OUT_DIR as OKR

PREREG = "P1-001"


def wilson(k: int, n: int) -> tuple[float, float]:
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return float(lo), float(hi)


def accept(rule: str, x: float) -> bool:
    return bool(eval(rule, {"__builtins__": {}}, {"x": x}))  # rule comes from committed prereg


def main() -> int:
    reg = load(paths.PREREG / f"{PREREG}.yaml")
    inputs = [OKR / f"{t}.parquet" for t in ("cord", "knot", "knot_cluster", "khipu_main")]
    out = start_run(PREREG, reg.seed, [PREREG], inputs)

    cord = pd.read_parquet(inputs[0])
    knot = pd.read_parquet(inputs[1])
    kc = pd.read_parquet(inputs[2])

    orphan_knots = int((~knot["CORD_ID"].isin(cord["CORD_ID"])).sum())
    knot = knot[knot["CORD_ID"].isin(cord["CORD_ID"])]
    clusters = cord_clusters(knot, kc)
    ref = knot.groupby("CORD_ID")["knot_value_type"].agg(
        lambda s: np.nan if s.isna().any() else float(s.sum()))

    meta = cord.set_index("CORD_ID")[["kh", "CLUSTER_ID"]]
    meta["CLUSTER_ID"] = meta["CLUSTER_ID"].fillna(-1).astype("int64")  # NaN breaks dict keys
    excl, elig = [], []
    for cid, cl in clusters.items():
        reason = ineligibility(cl)
        if reason is None and pd.isna(ref.get(cid)):
            reason = "recorder_value_missing"
        if reason:
            excl.append({"CORD_ID": cid, "kh": meta.at[cid, "kh"], "reason": reason})
        else:
            elig.append(cid)

    # Place spacing: per khipu (primary) and per cord group (sensitivity), from eligible cords.
    by_kh, by_grp, all_gaps = defaultdict(list), defaultdict(list), []
    for cid in elig:
        g = gaps(clusters[cid])
        by_kh[meta.at[cid, "kh"]] += g
        by_grp[(meta.at[cid, "kh"], meta.at[cid, "CLUSTER_ID"])] += g
        all_gaps += g
    corpus_s = float(np.median(all_gaps))
    s_kh = spacing_by(by_kh, corpus_s)
    s_grp = spacing_by(by_grp, corpus_s)

    # Units position per cord group (fallback: khipu) for cords without a units cluster.
    up_grp, up_kh = defaultdict(list), defaultdict(list)
    for cid in elig:
        low = max(clusters[cid], key=lambda c: c.pos)
        if low.is_units:
            up_grp[(meta.at[cid, "kh"], meta.at[cid, "CLUSTER_ID"])].append(low.pos)
            up_kh[meta.at[cid, "kh"]].append(low.pos)

    def units_pos(kh, grp):
        v = up_grp.get((kh, grp)) or up_kh.get(kh)
        return float(np.median(v)) if v else None

    rows = []
    for cid in elig:
        kh, grp = meta.at[cid, "kh"], meta.at[cid, "CLUSTER_ID"]
        cl, u = clusters[cid], units_pos(kh, grp)
        v, exps = decode(cl, s_kh[kh], u)
        v_consec, _ = decode(cl, s_kh[kh], u, infer_gaps=False)
        v_grp, _ = decode(cl, s_grp[(kh, grp)], u)
        seq = " | ".join(
            "".join(c.types) + f"@{c.pos:g}" for c in sorted(cl, key=lambda c: c.pos))
        rows.append({"kh": kh, "CORD_ID": cid, "knots_top_to_bottom": seq,
                     "reference": int(ref[cid]), "decoded": v, "exponents_bottom_up": exps,
                     "has_units_cluster": max(cl, key=lambda c: c.pos).is_units,
                     "decoded_consecutive": v_consec, "decoded_group_spacing": v_grp})
    res = pd.DataFrame(rows)
    res["agree"] = res["decoded"] == res["reference"]

    def cause(r) -> str:
        if r.agree:
            return ""
        if r.decoded_consecutive == r.reference:
            return "zero_place_inferred_from_spacing"
        if not r.has_units_cluster:
            return "no_units_cluster_place_ambiguous"
        return "other"

    res["cause"] = res.apply(cause, axis=1)

    # Data-quality side checks (not part of the verdict).
    kv = knot.dropna(subset=["knot_value_type"])
    pow10 = {10 ** i for i in range(0, 9)}
    consistent = np.where(
        kv["TYPE_CODE"] == "L", kv["knot_value_type"] == kv["NUM_TURNS"],
        np.where(kv["TYPE_CODE"] == "E", kv["knot_value_type"] == 1,
                 np.where(kv["TYPE_CODE"] == "S", kv["knot_value_type"].isin(pow10), True)))
    tv = kc.groupby("CORD_ID")["TOTAL_VALUE"].agg(lambda s: s.sum() if s.notna().all() else np.nan)
    tv_cmp = res.assign(tv=res["CORD_ID"].map(tv))
    tv_have = tv_cmp["tv"].notna()

    n, k = len(res), int(res["agree"].sum())
    x = k / n
    tol = reg.tolerance
    summary = {
        "prereg": PREREG,
        "eligible_cords": n,
        "agree": k,
        "agreement": x,
        "agreement_ci95_wilson": wilson(k, n),
        "tolerance": tol.accept_if,
        "inside_tolerance": accept(tol.accept_if, x),
        "spacing_corpus_median_cm": corpus_s,
        "cords_with_knots": len(clusters),
        "orphan_knots_ignored": orphan_knots,
        "exclusions": pd.Series([e["reason"] for e in excl]).value_counts().to_dict(),
        "mismatch_causes": res.loc[~res["agree"], "cause"].value_counts().to_dict(),
        "sensitivity": {
            "consecutive_place": float((res["decoded_consecutive"] == res["reference"]).mean()),
            "group_spacing": float((res["decoded_group_spacing"] == res["reference"]).mean()),
            "kfg_value": "pending: KFG download not complete",
            "additive_reading": "not run: the additive model of Overmann & Florio (2025) needs "
                                "an operational definition before it can be computed",
        },
        "data_quality": {
            "knot_value_type_consistent_with_type": float(np.mean(consistent)),
            "knots_checked": int(len(kv)),
            "total_value_cords_with_all_clusters_nonnull": int(tv_have.sum()),
            "total_value_agrees_with_reference": float(
                (tv_cmp.loc[tv_have, "tv"] == tv_cmp.loc[tv_have, "reference"]).mean()),
        },
    }
    res.to_csv(out / "cords.csv", index=False)
    res[~res["agree"]].to_csv(out / "mismatches.csv", index=False)
    pd.DataFrame(excl).to_csv(out / "exclusions.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
