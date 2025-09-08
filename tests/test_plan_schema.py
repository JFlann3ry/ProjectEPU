from app.services.plan_schema import can_create_event, guest_cap_info, parse_plan_features


def test_parse_defaults():
    pf = parse_plan_features(None)
    assert pf["max_events"] == 0
    assert pf["max_guests_per_event"] == 0
    assert pf["branding"] is False


def test_limits_and_caps():
    pf = parse_plan_features({"max_events": 2, "max_guests_per_event": 5})
    ok, msg = can_create_event(1, pf)
    assert ok and msg is None
    ok, msg = can_create_event(2, pf)
    assert not ok and "Event limit" in msg

    limit, capped, ratio = guest_cap_info(4, pf)
    assert limit == 5 and capped is False
    limit, capped, ratio = guest_cap_info(5, pf)
    assert capped is True and ratio == 1.0
