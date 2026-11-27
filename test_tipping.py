import random

from tipping import diff_bound, drop_rate, flip_to_ratio, kappa_interval, lift_rate, verdict


def test_lift_rate_is_the_miss_rate_among_negatives_that_reaches_the_target():
    s, t, n = 0.02, 0.10, 1000
    m = lift_rate(s, t)
    assert abs((s * n + m * (1 - s) * n) / n - t) < 1e-12  # 20 positives plus m of the 980 negatives give 100


def test_drop_rate_is_the_false_positive_rate_among_positives_that_reaches_the_target():
    f = drop_rate(0.8, 0.2)
    assert abs(0.8 * (1 - f) - 0.2) < 1e-12 and abs(f - 0.75) < 1e-12


def test_flip_to_ratio_moves_papers_from_numerator_to_denominator():
    x = flip_to_ratio(200, 100, 1.0)
    assert x == 50 and (200 - x) / (100 + x) == 1.0
    x = flip_to_ratio(60, 30, 1.5)
    assert abs((60 - x) / (30 + x) - 1.5) < 1e-12


def test_diff_bound_is_newcombe_and_contains_the_point():
    lo, hi = diff_bound((0.05, 0.03, 0.08), (0.02, 0.01, 0.04))
    assert lo < 0.03 < hi
    assert abs(hi - (0.03 + ((0.08 - 0.05) ** 2 + (0.02 - 0.01) ** 2) ** 0.5)) < 1e-12
    assert abs(lo - (0.03 - ((0.05 - 0.03) ** 2 + (0.04 - 0.02) ** 2) ** 0.5)) < 1e-12


def test_verdict_robust_only_when_the_overturning_error_exceeds_the_observed_upper_bound():
    assert verdict(0.08, 0.03) == "robust"
    assert verdict(0.02, 0.03) == "sensitive"


def test_kappa_interval_brackets_perfect_and_noisy_agreement():
    a = ["x"] * 10 + ["y"] * 10
    assert kappa_interval(a, a, random.Random(0)) == (1.0, 1.0)
    b = a[:]
    b[0], b[15] = "y", "x"
    lo, hi = kappa_interval(a, b, random.Random(0))
    assert lo < 0.8 < hi <= 1.0


def test_rates_count_first_stage_positives_directly_and_bound_slice_estimates():
    from tipping import rates
    m = lambda share, k, lo, hi: {"share": share, "confirmed": k, "lo": lo, "hi": hi}
    t = {"p": {"n": 1000, "several": m(0.05, 40, 0.04, 0.08), "several:cn_sp": m(0.01, 10, 0.01, 0.03), "several:cp_sn": m(0.02, 10, 0.015, 0.05)}}
    r = rates(t, "p", 40, "several")
    assert abs(r["fp_screen"][0] - 10 / 40) < 1e-12 and r["fp_screen"][2] < 0.5  # direct count with a Wilson bound, not the slice bound
    assert abs(r["miss_screen"][0] - 20 / 960) < 1e-12 and abs(r["miss_screen"][2] - 50 / 960) < 1e-12  # slice estimate with its bound


def test_null_seen_takes_point_and_bound_from_the_direction_whose_bound_is_used():
    from tipping import null_seen
    d = {"observed": 0.03, "observed_diff": {"miss_confirmer": (0.0007, -0.0016, 0.0021), "miss_screen": (-0.0029, -0.03, 0.0083)}}
    assert null_seen(d) == (-0.0029, 0.03)
    d = {"observed": 0.021, "observed_diff": {"miss_confirmer": (-0.002, -0.003, 0.001), "miss_screen": (0.0039, -0.010, 0.021)}}
    assert null_seen(d) == (0.0039, 0.021)
