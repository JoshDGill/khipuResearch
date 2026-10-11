import math

from arithmetic.sums import Khipu
from arithmetic.sums_kfg import r1, r2, r3, r4, r5, r6, r7, roughly_linear_decreasing


def kh(values, groups=None, colours=None, subs=None):
    groups = groups or [list(range(len(values)))]
    return Khipu("KHX", [float(v) for v in values], groups,
                 colours or [None] * len(values), subs or [])


def test_r1_threshold_and_zero_skipping():
    assert r1(kh([30, 10, 0, 20])) == {0}  # zero inside the range is skipped
    assert r1(kh([10, 4, 6])) == set()  # sum cord below 11
    assert r1(kh([30, 10, math.nan, 20])) == set()  # uncomputable cord breaks contiguity


def test_r2_needs_two_adjacent_groups_of_same_colour():
    vals = [30, 10, 20, 5]
    groups = [[0, 1], [2, 3]]
    colours = ["W", "W", "W", "R"]
    assert r2(kh(vals, groups, colours)) == {0}
    # summands within one group only: rejected
    assert r2(kh([30, 10, 20, 5], [[0], [1, 2, 3]], colours)) == set()


def test_r3_kfg_indexed_rules():
    # index 0: 17 = 8 + 9 from the two groups to its right
    k = kh([17, 1, 8, 1, 9, 1], groups=[[0, 1], [2, 3], [4, 5]])
    assert r3(k) == {0}
    # 30 is a multiple of 10 below 100: removed
    assert r3(kh([30, 1, 10, 1, 20, 1], groups=[[0, 1], [2, 3], [4, 5]])) == set()


def test_r4_subsidiary_rules():
    assert r4(kh([7, 8], subs=[(15.0, 0, 1)])) == {0}
    assert r4(kh([10, 10], subs=[(20.0, 0, 1)])) == set()  # multiple of 10 below 100


def test_r5_split_rules():
    assert r5(kh([2, 3, 4, 1], groups=[[0, 1, 2, 3]])) == {0}  # 2+3 = 4+1
    assert r5(kh([5, 5, 5, 5], groups=[[0, 1, 2, 3]])) == set()  # one repeated value


def test_r6_significance():
    assert r6(kh([7, 6, 13], groups=[[0, 1], [2]])) == {0, 1}
    assert r6(kh([10, 10, 20], groups=[[0, 1], [2]])) == set()  # 20: multiple of 10 below 100


def test_r7_roughly_linear_decreasing():
    assert roughly_linear_decreasing([30, 20, 10])  # slope -10 per cord: about -84 degrees
    # KFG's angle rule on (index, value) rejects slopes steeper than -87 degrees (> ~19/cord)
    assert not roughly_linear_decreasing([90, 60, 30])
    assert not roughly_linear_decreasing([10, 30, 5])  # not linear
    assert r7(kh([30, 20, 10], groups=[[0, 1, 2]])) == {0}
