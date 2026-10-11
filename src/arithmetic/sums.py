"""Ascher sum relations R1-R7, exactly as pre-registered in prereg/P1-002.yaml.

Operational choices the prereg leaves open, fixed before the first corpus run:
  * Cord value = recorder reading (sum of knot.knot_value_type). A knotless cord is 0. A cord
    with any knot lacking knot_value_type is "uncomputable": it can be neither a sum nor a
    summand, and it breaks contiguity (ranges never span it).
  * Pendant = CORD_LEVEL 1 and CORD_CLASSIFICATION not a top-cord code ('T', 'TPA').
    Subsidiary = CORD_LEVEL >= 2.
  * Pendant order = CORD_ORDINAL, ties broken by CORD_ID. Groups = cord.CLUSTER_ID (some IDs
    are missing from cord_cluster, so groups are taken from the cords), ordered by their first
    pendant. Index within a group counts from 0 at its leftmost pendant.
  * R2 colour = the cord's ascher_cord_color rows joined in RANGE_BEG order as
    COLOR_CD_1..5 with operators; cords without colour take no part in R2. The sum cord may be
    any pendant.
  * R3 summand runs obey the same contiguous-range rule as R1 (start and end non-zero,
    >= 2 non-zero), and a group lacking a computable index-i pendant breaks the run.
  * R5-R7 skip any group that contains an uncomputable pendant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TOP_CODES = {"T", "TPA"}
RELATIONS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]


@dataclass
class Khipu:
    kh: str
    values: list[float]  # pendant values in order; NaN = uncomputable
    groups: list[list[int]]  # indices into values, groups in order
    colours: list[str | None]  # per pendant
    subs: list[tuple[float, int, int]] = field(default_factory=list)  # (value, group idx, -)
    top_values: list[tuple[float, int]] = field(default_factory=list)  # (value, adjacent grp)


def _range_sums(vals: list[float]) -> dict[float, tuple[int, int]]:
    """All contiguous ranges (start/end non-zero, >= 2 non-zero, no NaN) -> for each sum value,
    (min end index, max start index), enough to test 'some range excludes position i'."""
    out: dict[float, tuple[int, int]] = {}
    n = len(vals)
    for a in range(n):
        va = vals[a]
        if not va or np.isnan(va):
            continue
        s = va
        for b in range(a + 1, n):
            vb = vals[b]
            if np.isnan(vb):
                break
            s += vb
            if vb:
                lo, hi = out.get(s, (n + 1, -1))
                out[s] = (min(lo, b), max(hi, a))
    return out


def _segment_sums(vals: list[float], positions: list[int]) -> dict[float, tuple[int, int]]:
    """Range sums over a subsequence; returned bounds are in the original position space."""
    sums = _range_sums(vals)
    return {s: (positions[b], positions[a]) for s, (b, a) in sums.items()}


def _excluded(bounds: tuple[int, int] | None, i: int) -> bool:
    if bounds is None:
        return False
    min_end, max_start = bounds
    return min_end < i or max_start > i


def r1(k: Khipu) -> set[int]:
    sums = _range_sums(k.values)
    return {i for i, v in enumerate(k.values) if v and not np.isnan(v)
            and _excluded(sums.get(v), i)}


def r2(k: Khipu) -> set[int]:
    by_colour: dict[str, list[int]] = {}
    for i, c in enumerate(k.colours):
        if c:
            by_colour.setdefault(c, []).append(i)
    hits: set[int] = set()
    for idx in by_colour.values():
        sums = _segment_sums([k.values[j] for j in idx], idx)
        for i, v in enumerate(k.values):
            if v and not np.isnan(v) and _excluded(sums.get(v), i):
                hits.add(i)
    return hits


def r3(k: Khipu) -> set[int]:
    hits: set[int] = set()
    g = k.groups
    for gi, members in enumerate(g):
        for idx, i in enumerate(members):
            v = k.values[i]
            if not v or np.isnan(v):
                continue
            for side in (range(gi - 1, -1, -1), range(gi + 1, len(g))):
                run: list[float] = []
                for gj in side:
                    if idx >= len(g[gj]) or np.isnan(k.values[g[gj][idx]]):
                        break
                    run.append(k.values[g[gj][idx]])
                    nz = [x for x in run if x]
                    if len(run) >= 2 and run[0] and run[-1] and len(nz) >= 2 and sum(run) == v:
                        hits.add(i)
                        break
                if i in hits:
                    break
    return hits


def r4(k: Khipu) -> set[int]:
    sums = _range_sums(k.values)
    return {j for j, (v, _, _) in enumerate(k.subs) if v and not np.isnan(v) and v in sums}


def _clean_groups(k: Khipu) -> list[tuple[int, list[float]]]:
    out = []
    for gi, members in enumerate(k.groups):
        vals = [k.values[i] for i in members]
        if not any(np.isnan(x) for x in vals):
            out.append((gi, vals))
    return out


def r5(k: Khipu) -> set[int]:
    hits = set()
    for gi, vals in _clean_groups(k):
        n = len(vals)
        if n < 4:
            continue
        for cut in {n // 2, (n + 1) // 2}:
            left, right = sum(vals[:cut]), sum(vals[cut:])
            if left == right and left > 0:
                hits.add(gi)
    return hits


def group_totals(k: Khipu) -> dict[int, float]:
    totals = {gi: sum(vals) for gi, vals in _clean_groups(k) if len(vals) >= 2}
    for v, gi, _ in k.subs:
        if gi in totals:
            totals[gi] = np.nan if np.isnan(v) else totals[gi] + v
    return {gi: t for gi, t in totals.items() if not np.isnan(t)}


def r6(k: Khipu) -> set[int]:
    seen: dict[float, list[int]] = {}
    for gi, t in group_totals(k).items():
        if t > 0:
            seen.setdefault(t, []).append(gi)
    return {gi for gs in seen.values() if len(gs) > 1 for gi in gs}


def r7(k: Khipu) -> set[int]:
    return {gi for gi, vals in _clean_groups(k)
            if len(vals) >= 3 and all(x > 0 for x in vals)
            and all(a > b for a, b in zip(vals, vals[1:], strict=False))}


def top_cord_sums(k: Khipu) -> set[int]:
    """Sensitivity: a top cord equals the sum of an adjacent group (incl. subsidiaries)."""
    totals = group_totals(k)
    return {j for j, (v, gi) in enumerate(k.top_values)
            if v and not np.isnan(v) and any(totals.get(g) == v for g in (gi - 1, gi, gi + 1))}


DETECTORS = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "R6": r6, "R7": r7}


def colour_codes(color: pd.DataFrame) -> pd.Series:
    c = color[color["PCORD_FLAG"] == 0].sort_values(["CORD_ID", "RANGE_BEG"])
    parts = []
    for i in range(1, 6):
        cd, op = c.get(f"COLOR_CD_{i}"), c.get(f"OPERATOR_{i}")
        if cd is None:
            continue
        parts.append(cd.fillna("").astype(str) + (op.fillna("").astype(str) if op is not None
                                                  else ""))
    code = parts[0]
    for p in parts[1:]:
        code = code + p
    code = code.str.strip()
    joined = code.groupby(c["CORD_ID"]).agg(lambda s: "|".join(x for x in s if x))
    return joined[joined != ""]


def build_khipus(cord: pd.DataFrame, knot: pd.DataFrame, color: pd.DataFrame,
                 exclude: set[str]) -> dict[str, Khipu]:
    val = knot.groupby("CORD_ID")["knot_value_type"].agg(
        lambda s: np.nan if s.isna().any() else float(s.sum()))
    cord = cord[~cord["kh"].isin(exclude)].assign(
        value=lambda d: d["CORD_ID"].map(val).fillna(0.0).where(
            ~d["CORD_ID"].isin(val[val.isna()].index), np.nan))
    cols = colour_codes(color)
    top = cord["CORD_CLASSIFICATION"].fillna("").isin(TOP_CODES)
    pend = cord[(cord["CORD_LEVEL"] == 1) & ~top].sort_values(["kh", "CORD_ORDINAL", "CORD_ID"])
    subs = cord[cord["CORD_LEVEL"] >= 2]
    tops = cord[top]
    parent = cord.set_index("CORD_ID")["PENDANT_FROM"]
    out = {}
    for kh, p in pend.groupby("kh"):
        p = p.reset_index(drop=True)
        order = list(dict.fromkeys(p["CLUSTER_ID"].fillna(-1)))
        gidx = {g: n for n, g in enumerate(order)}
        groups = [list(p.index[p["CLUSTER_ID"].fillna(-1) == g]) for g in order]
        pos_of = dict(zip(p["CORD_ID"], p.index, strict=True))
        grp_of_cord = dict(zip(p["CORD_ID"], p["CLUSTER_ID"].fillna(-1).map(gidx), strict=True))
        sub_rows = []
        for r in subs[subs["kh"] == kh].itertuples():
            anc = r.CORD_ID
            while anc not in pos_of and anc in parent.index and not pd.isna(parent[anc]):
                anc = parent[anc]
            if anc in pos_of:
                sub_rows.append((r.value, grp_of_cord[anc], int(r.CORD_ID)))
        top_rows = []
        for r in tops[tops["kh"] == kh].itertuples():
            later = p.index[p["CORD_ORDINAL"] > r.CORD_ORDINAL]
            gi = grp_of_cord[p.at[later[0], "CORD_ID"]] if len(later) else len(groups) - 1
            top_rows.append((r.value, gi))
        out[kh] = Khipu(kh=kh, values=p["value"].tolist(), groups=groups,
                        colours=[cols.get(c) for c in p["CORD_ID"]], subs=sub_rows,
                        top_values=top_rows)
    return out
