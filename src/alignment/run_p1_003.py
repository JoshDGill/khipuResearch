"""Run pre-registered test P1-003 (Santa Valley recto/verso split) and write results/.

    python -m alignment.run_p1_003

Operational choices the prereg leaves open, fixed before the first run:
  * pendant = cord with CORD_LEVEL 1 (hangs from a primary cord) whose CORD_CLASSIFICATION is
    not a top-cord code ('T', 'TPA');
  * six-cord group = an OKR cord_cluster (cord.CLUSTER_ID) containing exactly six pendants.
"""

from __future__ import annotations

import json
import sys

import pandas as pd
from statsmodels.stats.proportion import proportion_confint

from hypotheses.prereg import load
from khipu import paths
from khipu.runlog import start_run
from steward.okr import OUT_DIR as OKR

PREREG = "P1-003"
SANTA_VALLEY = [f"KH03{i}" for i in range(23, 29)]
TOP_CODES = {"T", "TPA"}
PUBLISHED_SIX_CORD_GROUPS = "132 or 133 (sources conflict; AGENTS.md §4)"


def share(df: pd.DataFrame) -> dict:
    r, v = int((df["ATTACHMENT_TYPE"] == "R").sum()), int((df["ATTACHMENT_TYPE"] == "V").sum())
    n = r + v
    lo, hi = proportion_confint(r, n, method="wilson") if n else (float("nan"),) * 2
    return {"recto": r, "verso": v, "unknown": int(len(df) - n),
            "recto_share": r / n if n else None, "ci95_wilson": [float(lo), float(hi)]}


def main() -> int:
    reg = load(paths.PREREG / f"{PREREG}.yaml")
    inputs = [OKR / "cord.parquet"]
    out = start_run(PREREG, reg.seed, [PREREG], inputs)

    cord = pd.read_parquet(inputs[0])
    sv = cord[cord["kh"].isin(SANTA_VALLEY)].copy()
    is_top = sv["CORD_CLASSIFICATION"].fillna("").isin(TOP_CODES)
    pend = sv[(sv["CORD_LEVEL"] == 1) & ~is_top]

    pooled = share(pend)
    x = pooled["recto_share"]
    per_kh = {kh: share(g) for kh, g in pend.groupby("kh")}
    six = (pend.groupby(["kh", "CLUSTER_ID"]).size() == 6).groupby("kh").sum()

    summary = {
        "prereg": PREREG,
        "pendants": int(len(pend)),
        "pooled": pooled,
        "tolerance": reg.tolerance.accept_if,
        "inside_tolerance": bool(eval(reg.tolerance.accept_if, {"__builtins__": {}}, {"x": x})),
        "per_khipu": per_kh,
        "six_cord_groups": {"per_khipu": {k: int(v) for k, v in six.items()},
                            "total": int(six.sum()),
                            "published": PUBLISHED_SIX_CORD_GROUPS},
        "sensitivity": {
            "excluding_KH0326": share(pend[pend["kh"] != "KH0326"]),
            "all_cords_incl_subsidiaries_and_top": share(sv),
            "kfg_attachment": "pending: KFG download not complete",
        },
        "top_cords_excluded": int(is_top.sum()),
        "subsidiaries_excluded": int((sv["CORD_LEVEL"] > 1).sum()),
    }
    pend[["kh", "CORD_ID", "CLUSTER_ID", "CORD_ORDINAL", "ATTACHMENT_TYPE", "src_row"]].to_csv(
        out / "pendants.csv", index=False)
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
