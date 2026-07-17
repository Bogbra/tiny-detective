from app.domain.policies.hint_policy import HintPolicy


def test_hint_allowed_below_limit():
    policy = HintPolicy(max_hints=3)

    assert policy.can_request_hint(hints_used=0) is True
    assert policy.can_request_hint(hints_used=2) is True


def test_hint_denied_at_limit():
    policy = HintPolicy(max_hints=3)

    assert policy.can_request_hint(hints_used=3) is False


def test_remaining_hints_never_negative():
    policy = HintPolicy(max_hints=3)

    assert policy.remaining_hints(hints_used=0) == 3
    assert policy.remaining_hints(hints_used=5) == 0
