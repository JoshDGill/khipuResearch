"""Reconstruction counts (AGENTS.md §10; plan §4.2): how much of the khipu record is usable.

Definitions are written into the report before the numbers, and each tier lists its exclusion
rules. The brief's approximate figures are targets to compare against, not inputs.

    python -m steward.reconstruction_counts   # writes reports/reconstruction_counts.md
"""

from __future__ import annotations

import re
import sys

import pandas as pd

from khipu import paths
from steward.crosswalk import OUT_CROSSWALK
from steward.quality import OUT_FLAGS, OUT_TABLE

KH = re.compile(r"^KH\d{4}[A-Z]?\b")  # KBCR codes look like "KH0263 = UR028"
COMPLETE_AT = 0.9  # attribute "known" on at least this share of cords/knots

TARGETS = {
    "T1": "~1,650-1,721",
    "T2": "~650-703",
    "T3": "~640 (range 619-703)",
    "T4": "~637",
    "T5": "~460",
    "T6": "~135+",
    "T7": "~1,000",
}


def kbcr_counts() -> dict[str, int]:
    conn = pd.read_csv(paths.RAW / "kbcr" / "KBCR_v09__3_KhipuConnections.csv",
                       dtype=str, encoding="utf-8-sig")
    codes = conn["KFG_Khipu_Code"].dropna().str.strip()
    codes = codes[(codes != "") & (codes != "-")]
    unique = set(codes) - {"Challa_grp"}  # KBCR notes: remove Challa_grp from unique count
    with_kh = {c for c in unique if KH.match(c)}
    return {"literature_unique": len(unique), "literature_with_kh": len(with_kh),
            "literature_without_kh": len(unique - with_kh)}


def tiers() -> tuple[list[dict], dict]:
    xw = pd.read_csv(OUT_CROSSWALK)
    q = pd.read_parquet(OUT_TABLE)
    flags = pd.read_csv(OUT_FLAGS)
    kb = kbcr_counts()

    dup = set(xw.loc[xw["duplicate_of"].notna(), "kh"])
    in_db = set(xw.loc[xw["in_khipu_db"], "kh"]) - dup
    q = q[q.index.isin(in_db)]

    t3 = q[(q["n_cords"] > 0) & (q["primary_cord_rows"] > 0)]
    t4 = t3[(t3["n_knots"] > 0) & (t3["knots_decodable"] > 0)]
    complete = (
        (t4["twist_known"] >= COMPLETE_AT) & (t4["attachment_known"] >= COMPLETE_AT)
        & (t4["colour_known"] >= COMPLETE_AT) & (t4["direction_known"] >= COMPLETE_AT)
    )
    t5 = t4[complete]
    repair_flags = {"no_cords", "no_knots", "no_primary_cord", "duplicate_primary_cord_rows",
                    "suspect_splice", "undecodable_knots"}
    t6 = set(flags.loc[flags["flag"].isin(repair_flags), "kh"]) & in_db
    t6_structural = set(flags.loc[flags["flag"].isin(repair_flags - {"undecodable_knots"}),
                                  "kh"]) & in_db

    rows = [
        {"tier": "T1", "name": "Known surviving khipus", "computed": None,
         "how": "Not computable from open data. Thompson (2025) census; KBCR lists "
                f"{kb['literature_unique']:,} distinct khipus or bundles named in literature."},
        {"tier": "T2", "name": "With any public digital record", "computed": len(xw) - len(dup),
         "how": "KH numbers issued by OKR (issued only for khipus with public data), minus "
                "duplicate records."},
        {"tier": "T3", "name": "Cord-level data in khipu.db, structurally loadable",
         "computed": len(t3),
         "how": "In khipu.db, not a duplicate record, ≥1 cord and ≥1 primary_cord row."},
        {"tier": "T4", "name": "Numerical values computable", "computed": len(t4),
         "how": "T3 and ≥1 knot of a decodable type (S, L with 2-9 turns, E)."},
        {"tier": "T5", "name": "Attribute-complete", "computed": len(t5),
         "how": f"T4 and ply, attachment and colour known on ≥{COMPLETE_AT:.0%} of cords and "
                f"knot direction on ≥{COMPLETE_AT:.0%} of knots."},
        {"tier": "T6", "name": "Partially documented or needing repair", "computed": len(t6),
         "how": "In khipu.db (not duplicate) with any of: " + ", ".join(sorted(repair_flags))
                + "."},
        {"tier": "T7", "name": "No public digital data", "computed": None,
         "how": f"Not computable exactly. KBCR names {kb['literature_without_kh']:,} khipus or "
                "bundles in literature without a KFG/KH code (a lower bound on undigitised "
                "objects that are documented in print)."},
    ]
    detail = {
        "kbcr": kb,
        "issued_not_in_db": int((~xw["in_khipu_db"]).sum()),
        "t6_structural": len(t6_structural),
        "t5_by_attribute": {
            col: int((t4[col] >= COMPLETE_AT).sum())
            for col in ["twist_known", "attachment_known", "colour_known", "direction_known"]
        },
        "t5_without_attachment": int((
            (t4["twist_known"] >= COMPLETE_AT) & (t4["colour_known"] >= COMPLETE_AT)
            & (t4["direction_known"] >= COMPLETE_AT)).sum()),
        "t5_at_100pct": int(((t4[["twist_known", "attachment_known", "colour_known",
                                  "direction_known"]] >= 1.0).all(axis=1)).sum()),
        "t5_at_50pct": int(((t4[["twist_known", "attachment_known", "colour_known",
                                 "direction_known"]] >= 0.5).all(axis=1)).sum()),
    }
    return rows, detail


def write(rows: list[dict], d: dict) -> None:
    fmt = lambda v: "n/a" if v is None else f"{v:,}"  # noqa: E731
    lines = [
        "# Reconstruction counts",
        "",
        "Generated by `python -m steward.reconstruction_counts`. **Source: OKR v2.1.0 and KBCR "
        "v6 only.** KFG reconciliation is not yet included, so tiers that depend on KFG repairs "
        "(the KFG reports ~703 well-formed khipus) are expected to be lower here.",
        "",
        "## Definitions and results",
        "",
        "\"Reconstructable\" means a khipu whose cords and knots can be loaded as a structure "
        "(T3). Each later tier is a subset of the one it names. Targets come from AGENTS.md §10 "
        "and are compared, not copied.",
        "",
        "| Tier | Measure | Computed | Brief target | Definition and exclusions |",
        "|---|---|---:|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['tier']} | {r['name']} | {fmt(r['computed'])} | "
                     f"{TARGETS[r['tier']]} | {r['how']} |")
    a = d["t5_by_attribute"]
    lines += [
        "",
        "## Notes",
        "",
        f"- {d['issued_not_in_db']} KH numbers are issued but have no rows in khipu.db (mostly "
        "post-2017 spreadsheets, PDFs and images in the OKR archive). They count in T2 only.",
        f"- T5 is limited by attachment. Of the T4 khipus, ply is ≥{COMPLETE_AT:.0%} known on "
        f"{a['twist_known']}, colour on {a['colour_known']}, knot direction on "
        f"{a['direction_known']}, but attachment on only {a['attachment_known']}. Without the "
        f"attachment requirement T5 would be {d['t5_without_attachment']}.",
        f"- T6 counts a khipu with even one knot outside S/L/E. Structural problems alone "
        f"(no cords or knots, no or duplicated primary cord rows, suspect splice) affect "
        f"{d['t6_structural']}.",
        f"- T5 sensitivity: {d['t5_at_100pct']} khipus at a 100% threshold, "
        f"{d['t5_at_50pct']} at 50%.",
        f"- KBCR v6: {d['kbcr']['literature_unique']:,} distinct khipu codes in literature, "
        f"{d['kbcr']['literature_with_kh']:,} with KH numbers and "
        f"{d['kbcr']['literature_without_kh']:,} without. The brief cites ~504 "
        "literature-mentioned khipus absent from open databases.",
        "- The duplicate record KH0483 (= KH0140) is excluded from every tier.",
        "",
    ]
    (paths.REPORTS / "reconstruction_counts.md").write_text("\n".join(lines))


def main() -> int:
    rows, detail = tiers()
    write(rows, detail)
    for r in rows:
        print(r["tier"], r["name"], r["computed"])
    print(detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
