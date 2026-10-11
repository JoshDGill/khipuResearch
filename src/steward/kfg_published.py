"""Extract the Khipu Field Guide's published per-khipu Ascher-sum results.

KFG's detection code is not public, but its analysis pages embed the per-khipu outputs as plot
data. This module reads those pages from data/raw/kfg/analyses/ (fetched and checksummed by
steward.fetch) and writes one row per (relation, khipu):

    data/interim/kfg/published_relations.csv   relation, kfg_name, count, source_page, plot

These are the published outputs P1-002v2 is compared against. They are data, not ground truth.

    python -m steward.kfg_published
"""

from __future__ import annotations

import json
import re
import sys

import pandas as pd

from khipu import paths

PAGES = {
    "R1": ("pendant_pendant_sum.html", "Matching Khipu"),
    "R2": ("colored_pendant_sum.html", "Matching Khipu"),
    "R3": ("indexed_pendant_sum.html", "Matching Khipu"),
    "R4": ("subsidiary_pendant_sum.html", "Matching Khipu"),
    "R5": ("group_sum_bands.html", "Matching Khipu"),
    "R6": ("group_group_sum.html", "Matching Sum Groups by Khipu"),
    "R7": ("ascher_decreasing_group.html", "Matching Khipu"),
    "top_cord_sums": ("sum_top_cords.html", "Matching Khipu"),
}
PLOT = re.compile(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\])\s*,\s*(\{.*?\})\s*,\s*\{', re.S)
OUT = paths.INTERIM / "kfg" / "published_relations.csv"
OUT_UNIVERSE = paths.INTERIM / "kfg" / "published_universe.csv"  # all khipus KFG analysed


def plots(html: str) -> list[tuple[str, list]]:
    out = []
    for m in PLOT.finditer(html):
        try:
            data, layout = json.loads(m.group(1)), json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        title = layout.get("title")
        title = title.get("text") if isinstance(title, dict) else title
        out.append((title or "", data))
    return out


def extract(relation: str, page: str, title_prefix: str) -> pd.DataFrame:
    html = (paths.RAW / "kfg" / "analyses" / page).read_text(errors="replace")
    for title, data in plots(html):
        if not title.startswith(title_prefix):
            continue
        tr = data[0]
        if relation == "R6":  # scatter over all khipus: x = number of matching group pairs
            names, counts = tr["hovertext"], tr["x"]
        else:  # bar chart of matching khipus: x = name, y = count
            names, counts = tr["x"], tr["y"]
        df = pd.DataFrame({"relation": relation, "kfg_name": names, "count": counts,
                           "source_page": page, "plot": title})
        return df[df["count"] > 0]
    raise ValueError(f"{page}: no plot titled {title_prefix!r}")


def universe() -> pd.DataFrame:
    """The R6 scatter plots every khipu KFG analysed (654), including those with no relation."""
    page, prefix = PAGES["R6"]
    html = (paths.RAW / "kfg" / "analyses" / page).read_text(errors="replace")
    for title, data in plots(html):
        if title.startswith(prefix):
            return pd.DataFrame({"kfg_name": data[0]["hovertext"]}).drop_duplicates()
    raise ValueError("universe plot not found")


def main() -> int:
    universe().to_csv(OUT_UNIVERSE, index=False)
    frames = [extract(r, p, t) for r, (p, t) in PAGES.items()]
    df = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    summary = df.groupby("relation")["kfg_name"].nunique().to_dict()
    sums = df[df["relation"].isin([f"R{i}" for i in range(1, 8)])]
    summary["any_R1_R7"] = int(sums["kfg_name"].nunique())
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
