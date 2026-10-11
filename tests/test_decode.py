from arithmetic.decode import Cluster, decode, ineligibility, round_half_up


def S(pos, n):
    return Cluster(pos, ("S",) * n, (0.0,) * n)


def L(pos, turns):
    return Cluster(pos, ("L",), (float(turns),))


def E(pos):
    return Cluster(pos, ("E",), (0.0,))


def test_round_half_up():
    assert [round_half_up(x) for x in (0.5, 1.5, 2.5, 2.49)] == [1, 2, 3, 2]


def test_plain_value():
    # 2 hundreds at 8 cm, 2 tens at 14 cm, L2 at 21.5 cm -> 222 (the OKR sample cord)
    cl = [S(8, 2), S(14, 2), L(21.5, 2)]
    assert ineligibility(cl) is None
    assert decode(cl, spacing=6.5, units_pos=None) == (222, [1, 2])


def test_zero_place_from_spacing():
    # 1 hundred, empty tens, units 5: gap is two spacings -> 105
    cl = [S(5, 1), L(17, 5)]
    assert decode(cl, spacing=6.0, units_pos=None)[0] == 105
    assert decode(cl, spacing=6.0, units_pos=None, infer_gaps=False)[0] == 15


def test_figure_eight_is_one():
    assert decode([S(10, 3), E(16)], spacing=6.0, units_pos=None)[0] == 31


def test_no_units_cluster_uses_group_units_position():
    # 4 tens at 14 cm, group units at 20 cm, spacing 6 -> exponent 1 -> 40
    assert decode([S(14, 4)], spacing=6.0, units_pos=20.0)[0] == 40
    # same knots two places above units -> 400
    assert decode([S(8, 4)], spacing=6.0, units_pos=20.0)[0] == 400


def test_ineligibility_reasons():
    assert ineligibility([]) == "no_knots"
    assert ineligibility([Cluster(5, ("SP",), (0.0,))]) == "undecodable_knot_type"
    assert ineligibility([L(10, 1)]) == "long_knot_turns_invalid"
    assert ineligibility([L(5, 3), S(10, 1)]) == "le_above_units"
    assert ineligibility([Cluster(10, ("L", "L"), (2.0, 3.0))]) == "units_multiple_le"
    assert ineligibility([Cluster(10, ("S", "L"), (0.0, 3.0))]) == "units_mixed_s_and_le"
    assert ineligibility([Cluster(float("nan"), ("S",), (0.0,))]) == "cluster_position_missing"
