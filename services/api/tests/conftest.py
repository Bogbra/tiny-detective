import pytest

from app.domain.entities.clue import Clue
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.solution import Solution
from app.domain.entities.suspect import Suspect
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus


@pytest.fixture
def make_case():
    """Returns a factory for a valid, consistent DetectiveCase.

    Mirrors the project spec's "Public Case Response Example" so fixtures stay
    recognizable against the spec. Override any field via kwargs.
    """

    def _make_case(**overrides: object) -> DetectiveCase:
        defaults: dict[str, object] = dict(
            case_id=CaseId("case_museum_001"),
            title="The Missing Museum Key",
            setting="A small town museum after closing time.",
            problem="An old display key disappeared from a locked glass case.",
            suspects=(
                Suspect(
                    suspect_id="suspect_1",
                    name="Mara",
                    role="Curator",
                    public_statement="I was checking inventory in the archive.",
                    is_culprit=False,
                ),
                Suspect(
                    suspect_id="suspect_2",
                    name="Jonas",
                    role="Night Guard",
                    public_statement="I heard a noise near the east hallway.",
                    is_culprit=False,
                ),
                Suspect(
                    suspect_id="suspect_3",
                    name="Lea",
                    role="Visitor",
                    public_statement="I only came back because I lost my phone.",
                    is_culprit=True,
                    private_reasoning="Her story places her beside the display case at the right moment.",
                ),
            ),
            clues=(
                Clue(clue_id="clue_1", text="A visitor wristband was found near the display case."),
                Clue(clue_id="clue_2", text="There were no signs of forced entry."),
                Clue(clue_id="clue_3", text="The archive motion sensor stayed inactive."),
            ),
            solution=Solution(
                culprit_suspect_id="suspect_3",
                explanation=(
                    "The key disappeared without forced entry. The evidence shows Lea was "
                    "near the case after closing."
                ),
            ),
            difficulty=Difficulty.EASY,
            status=PublishStatus.APPROVED,
        )
        defaults.update(overrides)
        return DetectiveCase(**defaults)

    return _make_case
