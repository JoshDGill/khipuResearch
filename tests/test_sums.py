import math

from arithmetic.sums import Khipu, r1, r2, r3, r4, r5, r6, r7

NAN = math.nan


def kh(values, groups=None, colours=None, subs=None):
    groups = groups or [list(range(len(values)))]
    return Khipu("KHX", [float(v) for v in values], groups,
                 colours or [None] * len(values), subs or [])


def test_r1_right_and_left_handed():
    assert r1(kh([10, 3, 7])) == {0}
    assert r1(kh([3, 7, 10])) == {2}


def test_r1_rules_out_trivial_and_nan_ranges():
    assert r1(kh([1, 1, 0])) == set()  # 1 = 1 + 0 is not a sum: needs >= 2 non-zero
    assert r1(kh([5, 0, 5])) == set()
    assert r1(kh([10, 3, NAN, 7])) == set()  # ranges never span an uncomputable cord
    assert r1(kh([10, 3, 0, 7])) == {0}  # zeros inside a range are fine


def test_r2_same_colour_subsequence():
    k = kh([10, 3, 9, 7], colours=["W", "R", "B", "R"])
    assert r2(k) == {0}
    assert r2(kh([10, 3, 9, 7], colours=["W", "R", "B", "G"])) == set()


def test_r3_indexed_sum_over_contiguous_groups():
    # three groups of 2; index 0 of group 0 = index 0 of groups 1 + 2
    k = kh([9, 1, 4, 2, 5, 3], groups=[[0, 1], [2, 3], [4, 5]])
    assert 0 in r3(k)
    assert 1 not in r3(k)  # 1 != 2 + 3


def test_r4_subsidiary_sum():
    k = kh([3, 7, 2], subs=[(10.0, 0, 99), (4.0, 0, 98)])
    assert r4(k) == {0}


def test_r5_band_with_off_by_one_split():
    assert r5(kh([1, 2, 3, 3, 3], groups=[[0, 1, 2, 3, 4]])) == {0}  # 1+2+3 = 3+3
    assert r5(kh([1, 2, 3], groups=[[0, 1, 2]])) == set()  # too short


def test_r6_group_pairs_include_subsidiaries():
    k = kh([2, 3, 1, 1], groups=[[0, 1], [2, 3]], subs=[(3.0, 1, 50)])
    assert r6(k) == {0, 1}


def test_r7_strictly_decreasing():
    assert r7(kh([9, 5, 1], groups=[[0, 1, 2]])) == {0}
    assert r7(kh([9, 5, 5], groups=[[0, 1, 2]])) == set()
    assert r7(kh([9, 5, 0], groups=[[0, 1, 2]])) == set()


def test_build_khipus_from_tables():
    import pandas as pd

    from arithmetic.sums import build_khipus

    cord = pd.DataFrame({
        "kh": ["KH1"] * 5, "CORD_ID": [1, 2, 3, 4, 5], "CORD_LEVEL": [1, 1, 1, 2, 1],
        "CORD_CLASSIFICATION": ["", "", "", "", "T"], "CORD_ORDINAL": [2, 3, 4, 1, 1],
        "CLUSTER_ID": [10, 10, 11, 10, None], "PENDANT_FROM": [0, 0, 0, 2, 0],
    })
    knot = pd.DataFrame({"CORD_ID": [1, 2, 3, 4, 5], "knot_value_type": [10, 3, 7, 4, None]})
    color = pd.DataFrame({"CORD_ID": [1, 2], "PCORD_FLAG": [0, 0], "RANGE_BEG": [0, 0],
                          "COLOR_CD_1": ["W", "AB"], "OPERATOR_1": ["", ""]})
    k = build_khipus(cord, knot, color, exclude=set())["KH1"]
    assert k.values == [10.0, 3.0, 7.0]
    assert k.groups == [[0, 1], [2]]
    assert k.colours == ["W", "AB", None]
    assert k.subs == [(4.0, 0, 4)]
    assert len(k.top_values) == 1 and math.isnan(k.top_values[0][0])
    assert r1(k) == {0}
