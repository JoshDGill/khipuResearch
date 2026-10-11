"""Locke base-10 decoder, exactly as pre-registered in prereg/P1-001.yaml.

The decoder reads only knot type, number of turns, cluster membership and cluster position
(START_POS, distance down the cord from its attachment). It never reads the recorder's place
values (knot.knot_value_type) or knot_cluster.TOTAL_VALUE; those are the reference.

Implementation choices the prereg leaves open, fixed here before the first corpus run:
  * "round" is round-half-up.
  * A cord with an L or E knot outside its lowest cluster is ineligible ("le_above_units"),
    because the prereg's walk only places S-knot clusters above the units position.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

DECODABLE = {"S", "L", "E"}


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


@dataclass(frozen=True)
class Cluster:
    pos: float  # START_POS, larger = lower on the cord
    types: tuple[str, ...]
    turns: tuple[float | None, ...]

    @property
    def is_units(self) -> bool:
        return any(t in ("L", "E") for t in self.types)


def ineligibility(clusters: list[Cluster]) -> str | None:
    """Return the reason a cord cannot be decoded, or None if it can."""
    if not clusters:
        return "no_knots"
    for c in clusters:
        if math.isnan(c.pos):
            return "cluster_position_missing"
        for t, n in zip(c.types, c.turns, strict=True):
            if t not in DECODABLE:
                return "undecodable_knot_type"
            if t == "L" and (n is None or (isinstance(n, float) and math.isnan(n))
                             or not 2 <= n <= 9):
                return "long_knot_turns_invalid"
    ordered = sorted(clusters, key=lambda c: c.pos)
    lowest, above = ordered[-1], ordered[:-1]
    if any(c.is_units for c in above):
        return "le_above_units"
    if lowest.is_units:
        le = [t for t in lowest.types if t in ("L", "E")]
        if len(le) > 1:
            return "units_multiple_le"
        if len(le) != len(lowest.types):
            return "units_mixed_s_and_le"
    return None


def units_digit(c: Cluster) -> int:
    t, n = c.types[0], c.turns[0]
    return 1 if t == "E" else int(n)


def decode(clusters: list[Cluster], spacing: float, units_pos: float | None,
           infer_gaps: bool = True) -> tuple[int, list[int]]:
    """Decode an eligible cord. Returns (value, exponent per S cluster from bottom up).

    infer_gaps=False is the pre-registered "consecutive-place" sensitivity variant.
    """
    ordered = sorted(clusters, key=lambda c: c.pos, reverse=True)  # bottom first
    value, exps = 0, []
    if ordered[0].is_units:
        value += units_digit(ordered[0])
        prev_pos, prev_exp = ordered[0].pos, 0
        s_clusters = ordered[1:]
    else:
        first = ordered[0]
        if infer_gaps and units_pos is not None and spacing > 0:
            exp = max(1, round_half_up((units_pos - first.pos) / spacing))
        else:
            exp = 1
        value += len(first.types) * 10 ** exp
        exps.append(exp)
        prev_pos, prev_exp = first.pos, exp
        s_clusters = ordered[1:]
    for c in s_clusters:
        skipped = 0
        if infer_gaps and spacing > 0:
            skipped = max(0, round_half_up((prev_pos - c.pos) / spacing) - 1)
        exp = prev_exp + 1 + skipped
        value += len(c.types) * 10 ** exp
        exps.append(exp)
        prev_pos, prev_exp = c.pos, exp
    return value, exps


def cord_clusters(knot: pd.DataFrame, knot_cluster: pd.DataFrame) -> dict[int, list[Cluster]]:
    """Group knots into Cluster objects per CORD_ID using knot_cluster.START_POS."""
    pos = knot_cluster.set_index("CLUSTER_ID")["START_POS"]
    k = knot.assign(pos=knot["CLUSTER_ID"].map(pos).astype(float))
    k = k.sort_values(["CORD_ID", "CLUSTER_ID", "KNOT_ORDINAL"])
    out: dict[int, list[Cluster]] = {}
    for (cord_id, _), g in k.groupby(["CORD_ID", "CLUSTER_ID"], sort=False, dropna=False):
        turns = tuple(None if pd.isna(x) else float(x) for x in g["NUM_TURNS"])
        p = g["pos"].iloc[0]
        out.setdefault(int(cord_id), []).append(
            Cluster(pos=float("nan") if pd.isna(p) else float(p),
                    types=tuple(str(t) for t in g["TYPE_CODE"]), turns=turns))
    return out


def gaps(clusters: list[Cluster]) -> list[float]:
    ps = sorted(c.pos for c in clusters)
    return [b - a for a, b in zip(ps, ps[1:], strict=False)]


def spacing_by(groups: dict[str, list[float]], fallback: float, min_n: int = 10) -> dict:
    return {k: (float(np.median(v)) if len(v) >= min_n else fallback) for k, v in groups.items()}


# --- P1-001v2: group-aligned place bands (prereg/P1-001v2.yaml) ---------------------------


def make_bands(positions: list[float], delta: float) -> list[tuple[float, float]]:
    """Single-linkage 1-D bands: split sorted positions where the gap exceeds delta.

    Returns (top, bottom) bounds per band, ordered from the top of the cord downwards.
    """
    ps = sorted(positions)
    if not ps:
        return []
    bands, start = [], ps[0]
    for a, b in zip(ps, ps[1:], strict=False):
        if b - a > delta:
            bands.append((start, a))
            start = b
    bands.append((start, ps[-1]))
    return bands


def units_band_index(bands: list[tuple[float, float]], u: float) -> int:
    for i, (top, bottom) in enumerate(bands):
        if top <= u <= bottom:
            return i
    return min(range(len(bands)), key=lambda i: abs((bands[i][0] + bands[i][1]) / 2 - u))


def band_exponent(pos: float, bands: list[tuple[float, float]], units_idx: int) -> int:
    for i, (top, bottom) in enumerate(bands):
        if top <= pos <= bottom:
            return max(0, units_idx - i)
    raise ValueError(f"position {pos} is not in any band")


def decode_banded(clusters: list[Cluster], bands: list[tuple[float, float]],
                  units_idx: int) -> tuple[int, list[int]]:
    ordered = sorted(clusters, key=lambda c: c.pos, reverse=True)  # bottom first
    value, exps, prev = 0, [], None
    if ordered[0].is_units:
        value += units_digit(ordered[0])
        prev = 0
        ordered = ordered[1:]
    for c in ordered:
        e = band_exponent(c.pos, bands, units_idx)
        if prev is not None:
            e = max(e, prev + 1)
        value += len(c.types) * 10 ** e
        exps.append(e)
        prev = e
    return value, exps
