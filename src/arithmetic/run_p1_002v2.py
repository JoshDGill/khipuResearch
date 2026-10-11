"""Run pre-registered test P1-002v2 (KFG search criteria on KFG data) and write results/.

    python -m arithmetic.run_p1_002v2

Needs the complete KFG download (make data), then `make steward` (steward.kfg,
steward.kfg_published).
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from arithmetic.sums import build_khipus as build_okr
from arithmetic.sums_kfg import DETECTORS, RELATIONS, khipus_from_kfg
from hypotheses.prereg import load
from khipu import paths
from khipu.runlog import start_run
from steward.crosswalk import OUT_CROSSWALK
from steward.okr import OUT_DIR as OKR

PREREG = "P1-002v2"
KFG = paths.INTERIM / "kfg"


def name_map(kfg_khipus: pd.DataFrame, xw: pd.DataFrame) -> dict[str, str]:
    """Any known name (KH, UR..., AS...) -> KFG file name (usually a KH number)."""
    m: dict[str, str] = {}
    for r in kfg_khipus.itertuples():
        m[r.kh] = r.kh
        for a in str(r.aliases or "").replace(";", ",").split(","):
            if a.strip():
                m.setdefault(a.strip(), r.kh)
    kfg_set = set(kfg_khipus["kh"])
    for r in xw.dropna(subset=["aliases"]).itertuples():
        if r.kh in kfg_set:
            for a in r.aliases.split(";"):
                m.setdefault(a.strip(), r.kh)
    return m


def run_relations(khipus: dict) -> pd.DataFrame:
    rows = []
    for kh, k in sorted(khipus.items()):
        if not any(not np.isnan(v) for v in k.values):
            continue
        rows.append({"kh": kh, **{r: len(DETECTORS[r](k)) for r in RELATIONS}})
    return pd.DataFrame(rows)


def share(df: pd.DataFrame, cols: list[str]) -> dict:
    k, n = int(df[cols].gt(0).any(axis=1).sum()), len(df)
    lo, hi = proportion_confint(k, n, method="wilson")
    return {"khipus": k, "of": n, "share": k / n, "ci95_wilson": [float(lo), float(hi)]}


def main() -> int:
    reg = load(paths.PREREG / f"{PREREG}.yaml")
    inputs = [KFG / "cords.parquet", KFG / "groups.parquet", KFG / "khipus.parquet",
              KFG / "published_relations.csv", KFG / "published_universe.csv",
              OKR / "cord.parquet", OKR / "knot.parquet", OKR / "ascher_cord_color.parquet",
              OUT_CROSSWALK]
    out = start_run(PREREG, reg.seed, [PREREG], inputs)

    cords, groups, kk = (pd.read_parquet(p) for p in inputs[:3])
    published = pd.read_csv(inputs[3])
    universe = pd.read_csv(inputs[4])
    xw = pd.read_csv(OUT_CROSSWALK)

    ours = run_relations(khipus_from_kfg(cords, groups))
    headline = share(ours, RELATIONS)
    x = headline["share"]

    nm = name_map(kk, xw)
    published["kh"] = published["kfg_name"].map(nm)
    universe["kh"] = universe["kfg_name"].map(nm)
    unmapped = sorted(set(universe.loc[universe["kh"].isna(), "kfg_name"]))
    common = set(universe["kh"].dropna()) & set(ours["kh"])
    jac = {}
    for r in RELATIONS:
        a = set(ours.loc[ours[r] > 0, "kh"]) & common
        b = set(published.loc[(published["relation"] == r), "kh"].dropna()) & common
        jac[r] = {"jaccard": len(a & b) / len(a | b) if a | b else None,
                  "ours": len(a), "kfg": len(b), "both": len(a & b)}
    median_j = float(np.median([v["jaccard"] for v in jac.values() if v["jaccard"] is not None]))
    pub_any = set(published.loc[published["relation"].isin(RELATIONS), "kh"].dropna()) & common

    in_share = bool(eval(reg.tolerance.accept_if, {"__builtins__": {}}, {"x": x}))
    xw_dups = set(xw.loc[xw["duplicate_of"].notna(), "kh"])
    okr = run_relations(build_okr(*(pd.read_parquet(p) for p in inputs[5:8]), exclude=xw_dups))

    summary = {
        "prereg": PREREG,
        "supersedes": reg.supersedes,
        "kfg_files_parsed": int(kk["kh"].nunique()),
        "headline": headline,
        "tolerance": reg.tolerance.accept_if,
        "inside_tolerance": in_share,
        "median_jaccard": median_j,
        "jaccard_criterion": "median >= 0.7",
        "jaccard_ok": median_j >= 0.7,
        "reproduced": in_share and median_j >= 0.7,
        "per_relation": {
            r: {"khipus": int((ours[r] > 0).sum()), "instances": int(ours[r].sum()), **jac[r]}
            for r in RELATIONS
        },
        "comparison_universe": {"kfg_published": len(universe), "mapped": int(
            universe["kh"].notna().sum()), "in_our_corpus": len(common),
            "unmapped_names": unmapped[:50]},
        "kfg_published_any_relation_in_common": {"khipus": len(pub_any), "of": len(common),
                                                 "share": len(pub_any) / len(common)},
        "sensitivity": {
            "okr_values": share(okr, RELATIONS),
            "sum_relations_only_R1_R6": share(ours, RELATIONS[:6]),
            "top_cord_sums": "not computed: top-cord relation not specified in KFG code cells",
        },
        "post_hoc": True,
    }
    ours.to_csv(out / "khipus_kfg.csv", index=False)
    okr.to_csv(out / "khipus_okr.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
