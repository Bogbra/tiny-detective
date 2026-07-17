"""Local/demo starter data for the in-memory case repository.

Reuses the two worked examples from the project spec ("Public Case Response Example"
and "AI Case Data Example") so the running API demonstrates a real case
lifecycle without needing the Phase 5 AI generation pipeline. Not used once
Phase 7 wires up Firestore.
"""

from app.domain.entities.clue import Clue
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.solution import Solution
from app.domain.entities.suspect import Suspect
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus


def seed_cases() -> list[DetectiveCase]:
    return [_museum_key_case(), _bake_sale_case()]


def _museum_key_case() -> DetectiveCase:
    return DetectiveCase(
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


def _bake_sale_case() -> DetectiveCase:
    return DetectiveCase(
        case_id=CaseId("case_bakesale_001"),
        title="The Vanishing Cupcake",
        setting="A cozy school bake sale.",
        problem="The last strawberry cupcake vanished before the raffle.",
        suspects=(
            Suspect(
                suspect_id="suspect_1",
                name="Nora",
                role="Student Helper",
                public_statement="I was stacking napkins near the entrance.",
                is_culprit=False,
            ),
            Suspect(
                suspect_id="suspect_2",
                name="Ben",
                role="Class Treasurer",
                public_statement="I counted coins at the front desk.",
                is_culprit=False,
            ),
            Suspect(
                suspect_id="suspect_3",
                name="Mia",
                role="Poster Designer",
                public_statement="I went back to fix a poster beside the dessert table.",
                is_culprit=True,
                private_reasoning="Her story places her beside the dessert table at the right moment.",
            ),
        ),
        clues=(
            Clue(clue_id="clue_1", text="A pink frosting mark was found on the poster tape."),
            Clue(clue_id="clue_2", text="The coin box stayed closed the entire time."),
            Clue(clue_id="clue_3", text="Napkins were stacked neatly near the entrance."),
        ),
        solution=Solution(
            culprit_suspect_id="suspect_3",
            explanation=(
                "Mia was beside the dessert table and the frosting mark on the poster "
                "tape connects her to the cupcake."
            ),
        ),
        difficulty=Difficulty.EASY,
        status=PublishStatus.DRAFT,
    )
