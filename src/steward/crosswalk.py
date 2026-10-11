"""Steward steps 4-5: ID crosswalk, duplicate register and leakage split groups (plan §4.1).

Outputs (small, committed for review):
  data/clean/id_crosswalk.csv  one row per KH number: aliases, museum data, split_group
  data/clean/duplicates.csv    every relation between two records, with evidence
  reports/steward_duplicates.md

Relation kinds:
  merged_in_source         OKR already holds re-recordings as one KH row (e.g. AS070/UR035)
  duplicate_record         two KH rows that OKR itself documents as the same physical khipu;
                           the less complete one gets ``duplicate_of`` and leaves the corpus
  shared_accession         separate khipus sharing one museum accession number
  content_match_candidate  distinct khipus with near-identical cord values (e.g. Puruchuco
                           matched accounts); not merged, flagged for human review

Every relation except merged_in_source puts both khipus in the same ``split_group``, so no
train/test split can separate them (AGENTS.md §9.7).

    python -m steward.crosswalk
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from khipu import paths
from steward.okr import OUT_DIR as OKR_INTERIM

# Duplicates documented in okr-kh-numbers.csv Comments but still stored as two KH rows.
DOCUMENTED_DUPLICATES = [("KH0140", "KH0483")]

CONTENT_JACCARD = 0.8  # multiset Jaccard of non-zero pendant values
MIN_NONZERO = 8  # sequences below this carry too little information to compare
MIN_DISTINCT = 4  # e.g. all-1 sequences match each other by coincidence

UNNUMBERED = {"", "n/a", "na", "none", "unknown", "?", "s/n", "unnumbered", "sin numero"}

OUT_CROSSWALK = paths.CLEAN / "id_crosswalk.csv"
OUT_DUPLICATES = paths.CLEAN / "duplicates.csv"
OUT_REPORT = paths.REPORTS / "steward_duplicates.md"


def split_aliases(text: str | None) -> list[str]:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return []
    return [a.strip() for a in re.split(r"[,;/]", str(text)) if a.strip()]


def alias_table(km: pd.DataFrame, kh_list: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in km.itertuples():
        for a in split_aliases(r.INVESTIGATOR_NUM):
            rows.append((r.kh, a, "khipu_main.INVESTIGATOR_NUM"))
    for r in kh_list.itertuples():
        kh = str(r[1]).strip()
        for a in split_aliases(r[2]):
            rows.append((kh, a, "okr-kh-numbers.csv:Other Names"))
    df = pd.DataFrame(rows, columns=["kh", "alias", "alias_source"])
    return df.drop_duplicates(["kh", "alias"]).reset_index(drop=True)


def cord_values(cord: pd.DataFrame, knot: pd.DataFrame) -> pd.DataFrame:
    """Recorder reading per cord (sum of knot_value_type), pendants in ordinal order.

    Used only to detect duplicates. Phase 1 value work lives in src/arithmetic/.
    """
    v = knot.groupby("CORD_ID")["knot_value_type"].sum()
    c = cord.assign(value=cord["CORD_ID"].map(v).fillna(0).astype("int64"))
    return c.sort_values(["kh", "CORD_ORDINAL"])


def content_matches(values: pd.DataFrame) -> list[dict]:
    sigs = {}
    for kh, s in values.groupby("kh")["value"]:
        nz = [int(x) for x in s if x > 0]
        if len(nz) >= MIN_NONZERO and len(set(nz)) >= MIN_DISTINCT:
            sigs[kh] = Counter(nz)
    keys, out = sorted(sigs), []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            inter = sum((sigs[a] & sigs[b]).values())
            union = sum((sigs[a] | sigs[b]).values())
            j = inter / union
            if j >= CONTENT_JACCARD:
                out.append({"kh_a": a, "kh_b": b, "kind": "content_match_candidate",
                            "evidence": f"multiset Jaccard {j:.3f} over non-zero cord values "
                                        f"(n={sum(sigs[a].values())}/{sum(sigs[b].values())})"})
    return out


def shared_accessions(km: pd.DataFrame) -> list[dict]:
    key = (km["MUSEUM_NAME"].fillna("").str.strip().str.strip('"').str.lower() + " · "
           + km["MUSEUM_NUM"].fillna("").str.strip().str.lower())
    num = km["MUSEUM_NUM"].fillna("").str.strip().str.lower()
    km = km.assign(_key=key)[~num.isin(UNNUMBERED)]
    out = []
    for k, g in km.groupby("_key"):
        khs = sorted(g["kh"])
        for other in khs[1:]:
            out.append({"kh_a": khs[0], "kh_b": other, "kind": "shared_accession",
                        "evidence": f"same museum and accession: {k}"})
    return out


def merged_in_source(km: pd.DataFrame) -> list[dict]:
    out = []
    for r in km.itertuples():
        names = split_aliases(r.INVESTIGATOR_NUM)
        if len(names) > 1:
            out.append({"kh_a": r.kh, "kh_b": r.kh, "kind": "merged_in_source",
                        "evidence": f"single KH row for recordings {'/'.join(names)}"})
    return out


def documented_duplicates(values: pd.DataFrame, knot: pd.DataFrame) -> list[dict]:
    n_cords = values.groupby("kh").size()
    n_knots = knot.groupby("kh").size()
    out = []
    for a, b in DOCUMENTED_DUPLICATES:
        # Canonical = more cords, then more knots, then lower KH number.
        rank = sorted([a, b], key=lambda k: (-n_cords.get(k, 0), -n_knots.get(k, 0), k))
        va = values.loc[values["kh"] == a, "value"].tolist()
        vb = values.loc[values["kh"] == b, "value"].tolist()
        diffs = [i for i, (x, y) in enumerate(zip(va, vb, strict=False)) if x != y]
        out.append({"kh_a": rank[0], "kh_b": rank[1], "kind": "duplicate_record",
                    "evidence": f"okr-kh-numbers.csv Comments; cords {len(va)}/{len(vb)}, "
                                f"differing positions {diffs}",
                    "canonical": rank[0]})
    return out


def split_groups(khs: list[str], relations: pd.DataFrame) -> dict[str, str]:
    parent = {k: k for k in khs}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for r in relations.itertuples():
        if r.kind != "merged_in_source" and r.kh_a in parent and r.kh_b in parent:
            ra, rb = find(r.kh_a), find(r.kh_b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    return {k: f"G-{find(k)}" for k in khs}


def build() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    km = pd.read_parquet(OKR_INTERIM / "khipu_main.parquet")
    cord = pd.read_parquet(OKR_INTERIM / "cord.parquet")
    knot = pd.read_parquet(OKR_INTERIM / "knot.parquet")
    kh_list = pd.read_parquet(OKR_INTERIM / "okr_kh_numbers.parquet")

    aliases = alias_table(km, kh_list)
    values = cord_values(cord, knot)
    relations = pd.DataFrame(
        merged_in_source(km) + documented_duplicates(values, knot)
        + shared_accessions(km) + content_matches(values),
        columns=["kh_a", "kh_b", "kind", "evidence", "canonical"],
    )

    listed = kh_list.rename(columns={"OKR Number": "kh"}).assign(kh=lambda d: d["kh"].str.strip())
    xw = listed[["kh", "Collection / Location", "Collection Number", "Country"]].merge(
        km[["kh", "KHIPU_ID", "INVESTIGATOR_NUM", "MUSEUM_NAME", "MUSEUM_NUM", "PROVENANCE",
            "REGION"]], on="kh", how="outer")
    xw["in_khipu_db"] = xw["KHIPU_ID"].notna()
    xw["aliases"] = xw["kh"].map(aliases.groupby("kh")["alias"].apply(lambda s: ";".join(s)))
    dup_of = {r.kh_b: r.kh_a for r in relations.itertuples() if r.kind == "duplicate_record"}
    xw["duplicate_of"] = xw["kh"].map(dup_of)
    xw["split_group"] = xw["kh"].map(split_groups(sorted(xw["kh"]), relations))
    xw = xw.sort_values("kh").reset_index(drop=True)
    return xw, relations, aliases


def alias_conflicts(aliases: pd.DataFrame) -> pd.DataFrame:
    n = aliases.groupby("alias")["kh"].nunique()
    return aliases[aliases["alias"].isin(n[n > 1].index)].sort_values(["alias", "kh"])


def write_report(xw: pd.DataFrame, rel: pd.DataFrame, conflicts: pd.DataFrame) -> None:
    counts = rel["kind"].value_counts()
    groups = xw.groupby("split_group").size()
    lines = [
        "# Steward: crosswalk, duplicates and split groups",
        "",
        "Generated by `python -m steward.crosswalk` from OKR v2.1.0 interim tables.",
        "",
        "## Summary",
        "",
        "| Item | Count |",
        "|---|---:|",
        f"| KH numbers (KH list ∪ khipu.db) | {len(xw)} |",
        f"| KH numbers with data in khipu.db | {int(xw['in_khipu_db'].sum())} |",
        *[f"| relation: {k} | {v} |" for k, v in counts.items()],
        f"| records marked duplicate_of (leave the analysis corpus) | "
        f"{int(xw['duplicate_of'].notna().sum())} |",
        f"| split groups with more than one khipu | {int((groups > 1).sum())} |",
        f"| aliases pointing to more than one KH | {conflicts['alias'].nunique()} |",
        "",
        "## Decisions",
        "",
        "- **merged_in_source:** OKR v2.1.0 already stores these re-recordings as one KH row. "
        "These are the brief's \"15 duplicate re-recordings\" (16 rows here; KH0033 combines "
        "three). Nothing to merge; aliases go into the crosswalk.",
        "- **duplicate_record:** KH0140 (AS125) and KH0483 (UR247) are documented by OKR as the "
        "same khipu but stored twice. The more complete record stays; the other is marked "
        "`duplicate_of` and leaves the analysis corpus. The pair is kept as an estimate of "
        "recording error between two recorders.",
        "- **shared_accession:** khipus catalogued under one accession number are separate "
        "objects (often tied together). They are not merged, but they share a split group.",
        f"- **content_match_candidate:** distinct khipus whose non-zero cord values overlap with "
        f"multiset Jaccard ≥ {CONTENT_JACCARD} (only sequences with ≥ {MIN_NONZERO} non-zero "
        f"values and ≥ {MIN_DISTINCT} distinct values are compared). These are **not** merged. "
        "They may be matched accounts (as described for Puruchuco), so they need human review "
        "and must stay on the same side of any split.",
        "",
        "## Relations",
        "",
        "| A | B | Kind | Evidence |",
        "|---|---|---|---|",
    ]
    for r in rel[rel["kind"] != "merged_in_source"].itertuples():
        lines.append(f"| {r.kh_a} | {r.kh_b} | {r.kind} | {r.evidence} |")
    lines += ["", "## Merged in source", "", "| KH | Evidence |", "|---|---|"]
    for r in rel[rel["kind"] == "merged_in_source"].itertuples():
        lines.append(f"| {r.kh_a} | {r.evidence} |")
    if len(conflicts):
        lines += ["", "## Alias conflicts", "", "| Alias | KH | Source |", "|---|---|---|"]
        for r in conflicts.itertuples():
            lines.append(f"| {r.alias} | {r.kh} | {r.alias_source} |")
    OUT_REPORT.write_text("\n".join(lines) + "\n")


def main() -> int:
    xw, rel, aliases = build()
    conflicts = alias_conflicts(aliases)
    paths.CLEAN.mkdir(parents=True, exist_ok=True)
    xw.to_csv(OUT_CROSSWALK, index=False)
    rel.to_csv(OUT_DUPLICATES, index=False)
    write_report(xw, rel, conflicts)
    log = {"step": "steward.crosswalk", "at": datetime.now(UTC).isoformat(timespec="seconds"),
           "kh_numbers": len(xw), "relations": rel["kind"].value_counts().to_dict(),
           "duplicate_of": xw.dropna(subset=["duplicate_of"])
                             .set_index("kh")["duplicate_of"].to_dict(),
           "alias_conflicts": int(conflicts["alias"].nunique())}
    with open(paths.INTERIM / "transform_log.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")
    print(json.dumps(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
