"""Ascher sum relations R1-R7 following KFG's published search criteria (prereg/P1-002v2.yaml).

Operates on the same ``Khipu`` structure as arithmetic.sums, so it runs on KFG data (primary)
and on OKR data (sensitivity). See the prereg for where each criterion comes from.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from arithmetic.sums import Khipu

WINDOW = 250
RELATIONS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]


def _ok(v: float) -> bool:
    return not (isinstance(v, float) and math.isnan(v))


def _nonzero_segments(positions: list[int], values: list[float]) -> list[list[int]]:
    """Split positions into runs of computable cords, dropping zeros (they never break a run)."""
    segs, cur = [], []
    for p, v in zip(positions, values, strict=True):
        if not _ok(v):
            if cur:
                segs.append(cur)
            cur = []
        elif v != 0:
            cur.append(p)
    if cur:
        segs.append(cur)
    return segs


def _range_index(k: Khipu, segs: list[list[int]], keep=None) -> dict[float, tuple[int, int]]:
    """sum value -> (min end position, max start position) over contiguous runs of >= 2 cords
    (at most WINDOW) inside each segment; `keep(run)` may reject a run."""
    out: dict[float, tuple[int, int]] = {}
    for seg in segs:
        n = len(seg)
        for a in range(n):
            s = k.values[seg[a]]
            for b in range(a + 1, min(n, a + WINDOW)):
                s += k.values[seg[b]]
                if keep is not None and not keep(seg[a:b + 1], s):
                    continue
                lo, hi = out.get(s, (10**9, -1))
                out[s] = (min(lo, seg[b]), max(hi, seg[a]))
    return out


def _excludes(bounds, i: int) -> bool:
    return bounds is not None and (bounds[0] < i or bounds[1] > i)


def r1(k: Khipu) -> set[int]:
    idx = _range_index(k, _nonzero_segments(list(range(len(k.values))), k.values))
    return {i for i, v in enumerate(k.values) if _ok(v) and v >= 11
            and _excludes(idx.get(v), i)}


def _group_of(k: Khipu) -> dict[int, int]:
    return {i: g for g, members in enumerate(k.groups) for i in members}


def r2(k: Khipu) -> set[int]:
    gof = _group_of(k)

    def keep(run, s):
        gs = sorted({gof[i] for i in run})
        return len(gs) >= 2 and gs[-1] - gs[0] + 1 == len(gs) and s > len(run)

    by_colour: dict[str, list[int]] = {}
    for i, c in enumerate(k.colours):
        if c:
            by_colour.setdefault(c, []).append(i)
    hits = set()
    for members in by_colour.values():
        idx = _range_index(k, _nonzero_segments(members, [k.values[i] for i in members]), keep)
        for i in members:
            v = k.values[i]
            if _ok(v) and v >= 11 and _excludes(idx.get(v), i):
                hits.add(i)
    return hits


def _trivial_round(v: float) -> bool:
    return (v < 100 and v % 10 == 0) or (v < 1000 and v % 100 == 0)


def r3(k: Khipu) -> set[int]:
    hits = set()
    for g, members in enumerate(k.groups):
        for idx, i in enumerate(members):
            v = k.values[i]
            if not _ok(v) or v <= 5 or _trivial_round(v):
                continue
            for side in (k.groups[:g], k.groups[g + 1:]):
                cand = [k.values[grp[idx]] for grp in side if len(grp) > idx]
                cand = [x for x in cand if _ok(x) and x > 0]
                if any(sum(cand[a:b]) == v for a in range(len(cand))
                       for b in range(a + 2, len(cand) + 1)):
                    hits.add(i)
                    break
    return hits


def r4(k: Khipu) -> set[int]:
    idx = _range_index(k, _nonzero_segments(list(range(len(k.values))), k.values))
    return {j for j, (v, _, _) in enumerate(k.subs)
            if _ok(v) and v >= 5 and not (v < 100 and v % 10 == 0) and v in idx}


def _groups_values(k: Khipu) -> list[tuple[int, list[float]]]:
    out = []
    for g, members in enumerate(k.groups):
        vals = [k.values[i] for i in members]
        if all(_ok(x) for x in vals):
            out.append((g, vals))
    return out


def r5(k: Khipu) -> set[int]:
    hits = set()
    for g, vals in _groups_values(k):
        n = len(vals)
        if n < 4 or sum(vals) < 5 or len(set(vals)) == 1:
            continue
        if any(sum(vals[:s]) == sum(vals[s:]) for s in range(2, n - 1)):
            hits.add(g)
    return hits


def _significant(t: float) -> bool:
    return t >= 100 or (t >= 11 and t % 10 != 0)


def r6(k: Khipu) -> set[int]:
    totals = {g: sum(vals) for g, vals in _groups_values(k)}
    for v, g, _ in k.subs:
        if g in totals:
            totals[g] = math.nan if not _ok(v) else totals[g] + v
    seen: dict[float, list[int]] = {}
    for g, t in totals.items():
        if _ok(t) and _significant(t):
            seen.setdefault(t, []).append(g)
    return {g for gs in seen.values() if len(gs) > 1 for g in gs}


def roughly_linear_decreasing(values: list[float], tolerance: float = 0.4) -> bool:
    """KFG's roughly_linear_decreasing on points (index, value)."""
    x = np.arange(len(values), dtype=float)
    y = np.asarray(values, dtype=float)
    norm = x.mean() ** 2 - (x ** 2).mean()
    m = ((x.mean() * y.mean()) - (x * y).mean()) / norm if norm != 0 else 0.0
    b = y.mean() - m * x.mean()
    ss_res = ((y - (m * x + b)) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2_ = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    theta = math.degrees(math.atan(m))
    return r2_ > (1 - tolerance) and -87.0 < theta < -5.0


def r7(k: Khipu) -> set[int]:
    return {g for g, vals in _groups_values(k)
            if len(vals) >= 3 and roughly_linear_decreasing(vals)}


DETECTORS = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "R6": r6, "R7": r7}


def khipus_from_kfg(cords: pd.DataFrame, groups: pd.DataFrame) -> dict[str, Khipu]:
    out = {}
    for kh, c in cords.groupby("kh"):
        pend = c[(c["level"] == 1) & (c["attachment"] != "T")].sort_values("pendant_num")
        pend = pend.reset_index(drop=True)
        vals = [float(v) if pd.notna(v) else math.nan for v in pend["value_int"]]
        pos_of_num = dict(zip(pend["pendant_num"].astype(int), pend.index, strict=True))
        grp = groups[groups["kh"] == kh].sort_values("group_index")
        glist = []
        for r in grp.itertuples():
            if pd.isna(r.first_pendant):
                continue
            members = [pos_of_num[n] for n in range(int(r.first_pendant), int(r.last_pendant) + 1)
                       if n in pos_of_num]
            if members:
                glist.append(members)
        gof = {i: g for g, m in enumerate(glist) for i in m}
        subs = []
        for r in c[c["level"] > 1].itertuples():
            p = pos_of_num.get(int(r.pendant_num))
            if p is not None and p in gof:
                v = float(r.value_int) if pd.notna(r.value_int) else math.nan
                subs.append((v, gof[p], r.row_order))
        out[kh] = Khipu(kh=kh, values=vals, groups=glist,
                        colours=[c_ or None for c_ in pend["color"].fillna("")], subs=subs)
    return out
