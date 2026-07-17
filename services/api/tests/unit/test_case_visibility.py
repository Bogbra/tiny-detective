import dataclasses

from app.domain.entities.public_views import PublicClue, PublicSuspect


def test_public_view_excludes_solution_and_private_suspect_fields(make_case):
    case = make_case()

    public_case = case.public_view()

    public_case_fields = {f.name for f in dataclasses.fields(public_case)}
    assert "solution" not in public_case_fields

    for suspect in public_case.suspects:
        assert isinstance(suspect, PublicSuspect)
        suspect_fields = {f.name for f in dataclasses.fields(suspect)}
        assert "is_culprit" not in suspect_fields
        assert "private_reasoning" not in suspect_fields
        assert "personality" not in suspect_fields


def test_public_view_clues_expose_only_id_and_text(make_case):
    case = make_case()

    public_case = case.public_view()

    for clue in public_case.clues:
        assert isinstance(clue, PublicClue)
        clue_fields = {f.name for f in dataclasses.fields(clue)}
        assert clue_fields == {"clue_id", "text"}


def test_public_view_preserves_case_identity_and_content(make_case):
    case = make_case()

    public_case = case.public_view()

    assert public_case.case_id == case.case_id.value
    assert public_case.title == case.title
    assert len(public_case.suspects) == len(case.suspects)
    assert len(public_case.clues) == len(case.clues)
