"""Run pre-registered test P1-001v2 (group-aligned place bands) and write results/.

    python -m arithmetic.run_p1_001v2
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
    decode_banded,
    gaps,
    ineligibility,
    make_bands,
    units_band_index,
)
from hypotheses.prereg import load
from khipu import paths
from khipu.runlog import start_run
from steward.okr import OUT_DIR as OKR

PREREG = "P1-001v2"
MIN_GAPS = 5


def wilson(k: int, n: int) -> list[float]:
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return [float(lo), float(hi)]


def decode_all(elig, clusters, meta, factor: float, per_khipu: bool):
    """Decode every eligible cord. Returns {CORD_ID: (value, exps)} and excluded {CORD_ID: why}."""
    key = (lambda cid: meta.at[cid, "kh"]) if per_khipu else (
        lambda cid: (meta.at[cid, "kh"], meta.at[cid, "CLUSTER_ID"]))
    groups, kh_gaps, all_gaps = defaultdict(list), defaultdict(list), []
    kh_units = defaultdict(list)
    for cid in elig:
        groups[key(cid)].append(cid)
        g = gaps(clusters[cid])
        kh_gaps[meta.at[cid, "kh"]] += g
        all_gaps += g
        low = max(clusters[cid], key=lambda c: c.pos)
        if low.is_units:
            kh_units[meta.at[cid, "kh"]].append(low.pos)
    corpus_gap = float(np.median(all_gaps))

    decoded, excluded = {}, {}
    for cids in groups.values():
        kh = meta.at[cids[0], "kh"]
        g_gaps = [x for cid in cids for x in gaps(clusters[cid])]
        if len(g_gaps) >= MIN_GAPS:
            med = float(np.median(g_gaps))
        elif len(kh_gaps[kh]) >= MIN_GAPS:
            med = float(np.median(kh_gaps[kh]))
        else:
            med = corpus_gap
        delta = factor * med
        units = [max(clusters[c], key=lambda x: x.pos).pos for c in cids
                 if max(clusters[c], key=lambda x: x.pos).is_units]
        units = units or kh_units.get(kh, [])
        if not units:
            for cid in cids:
                excluded[cid] = "no_units_anchor"
            continue
        u = float(np.median(units))
        bands = make_bands([c.pos for cid in cids for c in clusters[cid]], delta)
        ui = units_band_index(bands, u)
        for cid in cids:
            decoded[cid] = decode_banded(clusters[cid], bands, ui)
    return decoded, excluded


def main() -> int:
    reg = load(paths.PREREG / f"{PREREG}.yaml")
    inputs = [OKR / f"{t}.parquet" for t in ("cord", "knot", "knot_cluster")]
    out = start_run(PREREG, reg.seed, [PREREG], inputs)

    cord, knot, kc = (pd.read_parquet(p) for p in inputs)
    knot = knot[knot["CORD_ID"].isin(cord["CORD_ID"])]
    clusters = cord_clusters(knot, kc)
    ref = knot.groupby("CORD_ID")["knot_value_type"].agg(
        lambda s: np.nan if s.isna().any() else float(s.sum()))
    meta = cord.set_index("CORD_ID")[["kh", "CLUSTER_ID"]]
    meta["CLUSTER_ID"] = meta["CLUSTER_ID"].fillna(-1).astype("int64")

    excl, elig = {}, []
    for cid, cl in clusters.items():
        reason = ineligibility(cl)
        if reason is None and pd.isna(ref.get(cid)):
            reason = "recorder_value_missing"
        if reason:
            excl[cid] = reason
        else:
            elig.append(cid)

    primary, no_anchor = decode_all(elig, clusters, meta, 0.5, per_khipu=False)
    excl.update(no_anchor)
    variants = {
        "delta_0.35": decode_all(elig, clusters, meta, 0.35, per_khipu=False)[0],
        "delta_0.75": decode_all(elig, clusters, meta, 0.75, per_khipu=False)[0],
        "per_khipu_bands": decode_all(elig, clusters, meta, 0.5, per_khipu=True)[0],
    }

    rows = []
    for cid, (v, exps) in primary.items():
        cl = clusters[cid]
        rows.append({
            "kh": meta.at[cid, "kh"], "CORD_ID": cid, "group": meta.at[cid, "CLUSTER_ID"],
            "knots_top_to_bottom": " | ".join(
                "".join(c.types) + f"@{c.pos:g}" for c in sorted(cl, key=lambda c: c.pos)),
            "reference": int(ref[cid]), "decoded": v, "exponents_bottom_up": exps,
            "has_units_cluster": max(cl, key=lambda c: c.pos).is_units,
            **{f"decoded_{k}": d[cid][0] for k, d in variants.items() if cid in d},
        })
    res = pd.DataFrame(rows)
    res["agree"] = res["decoded"] == res["reference"]

    n, k = len(res), int(res["agree"].sum())
    x = k / n
    by_units = res.groupby("has_units_cluster")["agree"].agg(["mean", "size"])
    summary = {
        "prereg": PREREG,
        "supersedes": reg.supersedes,
        "eligible_cords": n,
        "agree": k,
        "agreement": x,
        "agreement_ci95_wilson": wilson(k, n),
        "tolerance": reg.tolerance.accept_if,
        "inside_tolerance": bool(eval(reg.tolerance.accept_if, {"__builtins__": {}}, {"x": x})),
        "exclusions": pd.Series(list(excl.values())).value_counts().to_dict(),
        "sensitivity": {
            **{k_: float((res[f"decoded_{k_}"] == res["reference"]).mean()) for k_ in variants},
            "with_units_cluster": {"agreement": float(by_units.loc[True, "mean"]),
                                   "cords": int(by_units.loc[True, "size"])},
            "without_units_cluster": {"agreement": float(by_units.loc[False, "mean"]),
                                      "cords": int(by_units.loc[False, "size"])},
            "kfg_value": "pending: KFG download not complete",
        },
        "post_hoc": True,
    }
    res.to_csv(out / "cords.csv", index=False)
    res[~res["agree"]].to_csv(out / "mismatches.csv", index=False)
    pd.Series(excl, name="reason").rename_axis("CORD_ID").to_csv(out / "exclusions.csv")
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
