import random

import pytest

from ai_content.logic_builder import (
    SUSPECT_TOKENS,
    ClueLogic,
    LogicBuildError,
    build_case_logic,
    solve,
)
from ai_content.scenario_templates import SCENARIO_TEMPLATES

FUZZ_SEEDS = range(1000)


def test_fuzz_every_seed_produces_a_uniquely_solvable_case():
    # The core guarantee this whole redesign rests on: build_case_logic()
    # never raises (it self-checks via solve() internally), across a wide
    # spread of random seeds — proven offline, for free, before any LLM
    # call ever happens. See ADR-0007's redesign addendum.
    for seed in FUZZ_SEEDS:
        rng = random.Random(seed)
        case_logic = build_case_logic(rng)
        assert solve(case_logic) == case_logic.culprit_token


def test_exactly_one_culprit_among_three_suspects():
    rng = random.Random(42)
    case_logic = build_case_logic(rng)
    culprits = [s for s in case_logic.suspects if s.is_culprit]
    assert len(culprits) == 1
    assert culprits[0].token == case_logic.culprit_token
    assert {s.token for s in case_logic.suspects} == set(SUSPECT_TOKENS)


def test_innocent_suspects_have_distinct_real_locations_off_incident():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    innocents = [s for s in case_logic.suspects if not s.is_culprit]
    locations = [s.real_location for s in innocents]
    assert len(set(locations)) == 2
    assert case_logic.template.incident_location not in locations


def test_culprit_claimed_location_differs_from_real_location():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    assert culprit.claimed_location != culprit.real_location
    assert culprit.real_location == case_logic.template.incident_location


def test_innocent_suspects_claimed_location_matches_real_location():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    for s in case_logic.suspects:
        if not s.is_culprit:
            assert s.claimed_location == s.real_location


def test_identifying_clue_anchors_on_culprit_signature_item_and_incident_location():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    identifying = next(c for c in case_logic.clues if c.kind == "identifying")
    assert identifying.subject_token == culprit.token
    assert culprit.signature_item in identifying.required_phrases
    assert case_logic.template.incident_location in identifying.required_phrases


def test_every_innocent_suspect_has_exactly_one_alibi_clue():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    innocents = [s.token for s in case_logic.suspects if not s.is_culprit]
    alibi_clue_subjects = [c.subject_token for c in case_logic.clues if c.kind == "alibi"]
    assert sorted(alibi_clue_subjects) == sorted(innocents)


def test_culprit_never_gets_an_alibi_clue():
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    alibi_subjects = {c.subject_token for c in case_logic.clues if c.kind == "alibi"}
    assert case_logic.culprit_token not in alibi_subjects


def test_clue_count_within_existing_rule_validator_range():
    # rule_validator.py requires 3-6 clues — the deterministic builder
    # always produces exactly 4 (1 identifying + 2 alibi + 1 neutral),
    # comfortably inside range regardless of which scenario is picked.
    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    assert len(case_logic.clues) == 4


def test_solve_detects_two_suspects_at_the_incident_location():
    from dataclasses import replace

    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    # Corrupt the case: put an innocent suspect at the incident location too
    # (simulating a construction bug) — solve() should refuse to pick a
    # single culprit rather than silently guessing.
    innocent = next(s for s in case_logic.suspects if not s.is_culprit)
    corrupted_innocent = replace(innocent, real_location=case_logic.template.incident_location)
    broken_suspects = tuple(
        corrupted_innocent if s.token == innocent.token else s for s in case_logic.suspects
    )
    # Also drop their alibi clue — otherwise they'd still be excluded by it,
    # masking the corruption this test means to exercise.
    broken_clues = tuple(c for c in case_logic.clues if c.clue_id != f"clue_alibi_{innocent.token}")
    broken = replace(case_logic, suspects=broken_suspects, clues=broken_clues)
    with pytest.raises(LogicBuildError):
        solve(broken)


def test_solve_detects_culprit_wrongly_given_an_alibi_clue():
    from dataclasses import replace

    rng = random.Random(7)
    case_logic = build_case_logic(rng)
    # Corrupt the case: give the culprit an alibi clue too (simulating a
    # construction bug) — solve() should find zero candidates rather than
    # silently proceeding.
    bogus_alibi = ClueLogic(
        clue_id="clue_alibi_bogus",
        kind="alibi",
        subject_token=case_logic.culprit_token,
        required_phrases=(),
    )
    broken = replace(case_logic, clues=case_logic.clues + (bogus_alibi,))
    with pytest.raises(LogicBuildError):
        solve(broken)


def test_all_scenario_templates_are_reachable():
    seen_keys = set()
    for seed in range(200):
        rng = random.Random(seed)
        case_logic = build_case_logic(rng)
        seen_keys.add(case_logic.template.key)
    assert seen_keys == {t.key for t in SCENARIO_TEMPLATES}
