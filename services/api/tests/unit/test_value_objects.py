import pytest

from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus


def test_case_id_rejects_empty_value():
    with pytest.raises(ValueError):
        CaseId("")


def test_case_id_holds_value():
    assert CaseId("case_museum_001").value == "case_museum_001"


def test_difficulty_values():
    assert Difficulty.EASY.value == "easy"
    assert Difficulty.MEDIUM.value == "medium"
    assert Difficulty.HARD.value == "hard"


def test_publish_status_values():
    assert {s.value for s in PublishStatus} == {
        "draft",
        "approved",
        "rejected",
        "live",
        "archived",
    }
