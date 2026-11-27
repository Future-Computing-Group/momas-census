from deploy import org_level, shares


def test_org_level_takes_widest_reach():
    rows = [("Acme", "internal"), ("Acme", "cross-owner"), ("Beta", "customer"), ("Gamma", "na")]
    assert org_level(rows) == {"acme": "cross-owner", "beta": "customer"}


def test_shares_exclude_na_and_non_agents():
    coded = [{"agent": "yes", "reach": "internal"}, {"agent": "yes", "reach": "cross-owner"}, {"agent": "no", "reach": "na"}, {"agent": "yes", "reach": "na"}]
    s = shares(coded)
    assert s["n"] == 2 and s["internal"] == 1 and s["cross-owner"] == 1 and s["customer"] == 0


def test_crosstab_maps_v3_counterparty_to_v2_customer_label_and_counts_moves():
    from deploy import crosstab
    v2 = {"a": {"reach": "customer"}, "b": {"reach": "cross-owner"}, "c": {"reach": "internal"}}
    v3 = {"a": {"reach": "counterparty"}, "b": {"reach": "counterparty"}, "c": {"reach": "internal"}}
    t = crosstab(v2, v3)
    assert t[("customer", "customer")] == 1 and t[("cross-owner", "customer")] == 1 and t[("internal", "internal")] == 1
    assert sum(t.values()) == 3
