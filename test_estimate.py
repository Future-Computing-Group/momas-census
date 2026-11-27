from estimate import inclusion, ht_share


def test_inclusion_combines_independent_strata():
    frame = {"n": 1000, "random": 300, "agent_hits": 400, "agent": 200}
    # not a keyword hit: only the random stratum can draw it
    assert abs(inclusion({"agent": False, "llm_agent": False}, frame, llm_census=False) - 0.3) < 1e-12
    # keyword hit: drawn by random or agent stratum, 1 - 0.7 * 0.5
    assert abs(inclusion({"agent": True, "llm_agent": False}, frame, llm_census=False) - 0.65) < 1e-12
    # 2025 LLM-agent hits are taken in full
    assert inclusion({"agent": True, "llm_agent": True}, frame, llm_census=True) == 1.0
    # a frame with fewer hits than the quota takes every hit
    small = dict(frame, agent_hits=150)
    assert inclusion({"agent": True, "llm_agent": False}, small, llm_census=False) == 1.0


def test_ht_share_reweights_oversampled_items():
    # four oversampled positives (pi=1) and two undersampled negatives (pi=0.1)
    ys = [1, 1, 1, 1, 0, 0]
    pis = [1, 1, 1, 1, 0.1, 0.1]
    assert abs(ht_share(ys, pis) - 4 / 24) < 1e-12
    assert ht_share(ys, [1] * 6) == 4 / 6


def test_main_track_reads_the_openreview_group():
    from estimate import main_track
    assert main_track({"sourceurl": "https://openreview.net/group?id=NeurIPS.cc/2025/Conference"})
    assert main_track({"sourceurl": "https://openreview.net/group?id=ICML.cc/2025/Conference"})
    assert not main_track({"sourceurl": "https://openreview.net/group?id=NeurIPS.cc/2025/Datasets_and_Benchmarks_Track"})
    assert not main_track({"sourceurl": "https://openreview.net/group?id=NeurIPS.cc/2025/Position_Paper_Track"})
    # 2020 lists carry no OpenReview group and are main-track proceedings
    assert main_track({"sourceurl": None})


def test_kish_effective_n_and_flip_leverage():
    from estimate import kish, flip_leverage
    assert kish([1, 1, 1, 1]) == 4
    assert abs(kish([1, 1, 1, 0.1]) - (3 + 10) ** 2 / (3 + 100)) < 1e-12
    # weights 1,1,1,10 (pi 1,1,1,0.1): flipping the heavy zero to one moves the share most
    lev = flip_leverage([0, 0, 0, 0], [1, 1, 1, 0.1])
    assert max(range(4), key=lambda i: lev[i]) == 3 and abs(lev[3] - 10 / 13) < 1e-12
