import pandas as pd
import pytest

from steward import crosswalk, okr


def test_split_aliases():
    assert crosswalk.split_aliases("AS070/UR035") == ["AS070", "UR035"]
    assert crosswalk.split_aliases("LL001, UR176") == ["LL001", "UR176"]
    assert crosswalk.split_aliases(None) == []


def test_split_groups_union_and_ignore_merged_in_source():
    rel = pd.DataFrame([
        {"kh_a": "KH1", "kh_b": "KH2", "kind": "shared_accession"},
        {"kh_a": "KH2", "kh_b": "KH3", "kind": "content_match_candidate"},
        {"kh_a": "KH4", "kh_b": "KH4", "kind": "merged_in_source"},
    ])
    g = crosswalk.split_groups(["KH1", "KH2", "KH3", "KH4"], rel)
    assert g["KH1"] == g["KH2"] == g["KH3"] == "G-KH1"
    assert g["KH4"] == "G-KH4"


def _values(seqs):
    return pd.DataFrame([{"kh": k, "value": v} for k, s in seqs.items() for v in s])


def test_content_matches_skip_low_information_sequences():
    ones = [1] * 12
    assert crosswalk.content_matches(_values({"A": ones, "B": ones})) == []


def test_content_matches_find_near_copies():
    a = [5, 12, 7, 300, 41, 9, 66, 18, 2904]
    b = a[:-1] + [2905]
    out = crosswalk.content_matches(_values({"A": a, "B": b}))
    assert [(r["kh_a"], r["kh_b"]) for r in out] == [("A", "B")]


needs_data = pytest.mark.skipif(
    not (okr.OUT_DIR / "khipu_main.parquet").exists(), reason="run `make steward` first"
)


@pytest.fixture(scope="module")
def built():
    return crosswalk.build()


@needs_data
def test_documented_duplicate_is_marked(built):
    xw, _, _ = built
    dup = xw.dropna(subset=["duplicate_of"]).set_index("kh")["duplicate_of"].to_dict()
    assert dup == {"KH0483": "KH0140"}


@needs_data
def test_known_rerecordings_are_single_rows_with_aliases(built):
    xw, rel, _ = built
    aliases = xw.set_index("kh")["aliases"]
    assert {"AS070", "UR035"} <= set(aliases["KH0083"].split(";"))
    assert {"UR176", "LL01"} <= set(aliases["KH0001"].split(";"))
    assert (rel["kind"] == "merged_in_source").sum() == 16


@needs_data
def test_matched_accounts_share_a_split_group(built):
    xw, _, _ = built
    g = xw.set_index("kh")["split_group"]
    assert g["KH0303"] == g["KH0304"]
    assert g["KH0140"] == g["KH0483"]


@needs_data
def test_crosswalk_keys(built):
    xw, _, aliases = built
    assert xw["kh"].is_unique and len(xw) == 702
    assert crosswalk.alias_conflicts(aliases).empty
