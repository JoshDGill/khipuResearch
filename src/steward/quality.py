"""Steward step 7: per-khipu quality flags (plan §4.1; AGENTS.md §4 "known data issues").

Flags are recorded, never repaired. Output is a long table, one row per (kh, flag):

    data/clean/quality_flags.csv   kh, flag, value, detail
    data/clean/khipu_quality.parquet  one row per KH with the completeness shares used below

Missing-value conventions (raw values stay untouched in data/interim):
  cord.TWIST (ply)            known = S, Z
  cord.ATTACHMENT_TYPE        known = R, V, H
  knot.DIRECTION              known = S, Z
  colour                      known = cord has an ascher_cord_color row with a non-blank code
  knot type decodable         TYPE_CODE in S, L, E (and L has NUM_TURNS 2-9)

    python -m steward.quality
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import pandas as pd

from khipu import paths
from steward.crosswalk import OUT_CROSSWALK
from steward.okr import OUT_DIR as OKR_INTERIM

KNOWN_TWIST = {"S", "Z"}
KNOWN_ATTACH = {"R", "V", "H"}
KNOWN_DIRECTION = {"S", "Z"}
DECODABLE_TYPES = {"S", "L", "E"}

PARTIAL_BELOW = 0.9  # known share below this (but above 0) => partial_<attribute>

# Issues documented in the brief (AGENTS.md §4) that the data cannot show by itself.
DOCUMENTED = [
    ("KH0082", "suspect_splice", "AGENTS.md §4: ~1,831 cords, missing object, possible splicing "
                                 "error, no ply/spin data"),
    ("KH0083", "spacing_unreliable", "AGENTS.md §4: pendants moved for display"),
]

OUT_FLAGS = paths.CLEAN / "quality_flags.csv"
OUT_TABLE = paths.CLEAN / "khipu_quality.parquet"


def _share(mask: pd.Series, by: pd.Series) -> pd.Series:
    return mask.groupby(by).mean()


def khipu_table() -> pd.DataFrame:
    km = pd.read_parquet(OKR_INTERIM / "khipu_main.parquet")
    cord = pd.read_parquet(OKR_INTERIM / "cord.parquet")
    knot = pd.read_parquet(OKR_INTERIM / "knot.parquet")
    color = pd.read_parquet(OKR_INTERIM / "ascher_cord_color.parquet")
    pcord = pd.read_parquet(OKR_INTERIM / "primary_cord.parquet")

    colored = set(color.loc[color["COLOR_CD_1"].fillna("").str.strip() != "", "CORD_ID"])
    knot = knot[knot["kh"].notna()]  # orphan knots are reported by steward.okr
    turns_ok = knot["NUM_TURNS"].between(2, 9)
    decodable = knot["TYPE_CODE"].isin(DECODABLE_TYPES) & ((knot["TYPE_CODE"] != "L") | turns_ok)

    t = pd.DataFrame(index=pd.Index(sorted(km["kh"]), name="kh"))
    t["n_cords"] = cord.groupby("kh").size()
    t["n_knots"] = knot.groupby("kh").size()
    t = t.fillna(0).astype(int)
    t["twist_known"] = _share(cord["TWIST"].isin(KNOWN_TWIST), cord["kh"])
    t["attachment_known"] = _share(cord["ATTACHMENT_TYPE"].isin(KNOWN_ATTACH), cord["kh"])
    t["colour_known"] = _share(cord["CORD_ID"].isin(colored), cord["kh"])
    t["direction_known"] = _share(knot["DIRECTION"].isin(KNOWN_DIRECTION), knot["kh"])
    t["knots_decodable"] = _share(decodable, knot["kh"])
    t["primary_cord_rows"] = pcord.groupby("kh").size()
    t["primary_cord_rows"] = t["primary_cord_rows"].fillna(0).astype(int)
    t["dup_primary_cord_ids"] = (
        pcord.groupby("kh")["PCORD_ID"].apply(lambda s: int(s.duplicated().sum()))
    )
    t["dup_primary_cord_ids"] = t["dup_primary_cord_ids"].fillna(0).astype(int)
    return t


def flags(t: pd.DataFrame, xw: pd.DataFrame) -> pd.DataFrame:
    rows: list[tuple[str, str, float, str]] = []
    for kh, r in t.iterrows():
        if r.n_cords == 0:
            rows.append((kh, "no_cords", 0, "khipu_main row without cords"))
        if r.n_knots == 0:
            rows.append((kh, "no_knots", 0, "no knots recorded"))
        for col, name, denom in [("twist_known", "ply", r.n_cords),
                                 ("attachment_known", "attachment", r.n_cords),
                                 ("colour_known", "colour", r.n_cords),
                                 ("direction_known", "knot_direction", r.n_knots)]:
            if denom == 0:
                continue
            share = float(r[col])
            if share == 0:
                rows.append((kh, f"missing_{name}", share, f"no {name} recorded on any of {denom}"))
            elif share < PARTIAL_BELOW:
                rows.append((kh, f"partial_{name}", round(share, 4),
                             f"{name} known on {share:.0%} of {denom}"))
        if r.n_knots and r.knots_decodable < 1:
            rows.append((kh, "undecodable_knots", round(1 - float(r.knots_decodable), 4),
                         "knots outside S/L/E or L without 2-9 turns"))
        if r.primary_cord_rows == 0 and r.n_cords:
            rows.append((kh, "no_primary_cord", 0, "cords but no primary_cord row"))
        if r.dup_primary_cord_ids:
            rows.append((kh, "duplicate_primary_cord_rows", int(r.dup_primary_cord_ids),
                         "repeated PCORD_ID rows in primary_cord"))
    for r in xw.itertuples():
        if not r.in_khipu_db:
            rows.append((r.kh, "not_in_khipu_db", 0, "KH number issued; data not in khipu.db"))
        if isinstance(r.duplicate_of, str):
            rows.append((r.kh, "duplicate_record", 0, f"duplicate_of {r.duplicate_of}"))
    for kh, flag, detail in DOCUMENTED:
        rows.append((kh, flag, 0, detail))
    return pd.DataFrame(rows, columns=["kh", "flag", "value", "detail"]).sort_values(
        ["kh", "flag"]).reset_index(drop=True)


def main() -> int:
    t = khipu_table()
    xw = pd.read_csv(OUT_CROSSWALK)
    f = flags(t, xw)
    paths.CLEAN.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT_TABLE)
    f.to_csv(OUT_FLAGS, index=False)
    log = {"step": "steward.quality", "at": datetime.now(UTC).isoformat(timespec="seconds"),
           "flag_counts": f["flag"].value_counts().to_dict()}
    with open(paths.INTERIM / "transform_log.jsonl", "a") as fh:
        fh.write(json.dumps(log) + "\n")
    print(json.dumps(log["flag_counts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
