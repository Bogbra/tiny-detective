import dataclasses
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.application.errors import CaseNotFoundError, PlayerNotFoundError
from app.application.ports import (
    AttemptRepository,
    CaseRepository,
    HintRequestRepository,
    PlayerRepository,
)
from app.domain.entities.attempt import Attempt
from app.domain.policies.scoring_policy import ScoringPolicy
from app.domain.policies.solution_policy import SolutionPolicy
from app.domain.value_objects.case_id import CaseId


@dataclass(frozen=True, slots=True)
class SubmitSolutionResult:
    correct: bool
    score: int
    feedback: str
    solution_explanation: str
    streak: int


def _next_streak(current_streak: int, correct: bool) -> int:
    return current_streak + 1 if correct else 0


class SubmitSolution:
    def __init__(
        self,
        case_repository: CaseRepository,
        player_repository: PlayerRepository,
        hint_request_repository: HintRequestRepository,
        attempt_repository: AttemptRepository,
        solution_policy: SolutionPolicy | None = None,
        scoring_policy: ScoringPolicy | None = None,
    ) -> None:
        self._case_repository = case_repository
        self._player_repository = player_repository
        self._hint_request_repository = hint_request_repository
        self._attempt_repository = attempt_repository
        self._solution_policy = solution_policy or SolutionPolicy()
        self._scoring_policy = scoring_policy or ScoringPolicy()

    def execute(
        self, case_id: CaseId, player_id: str, submitted_suspect_id: str
    ) -> SubmitSolutionResult:
        case = self._case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"case '{case_id.value}' not found")

        player = self._player_repository.get(player_id)
        if player is None:
            raise PlayerNotFoundError(f"player '{player_id}' not found")

        result = self._solution_policy.evaluate(case, submitted_suspect_id)

        hints_used = self._hint_request_repository.count_for_case(case_id, player_id)
        score = self._scoring_policy.calculate_score(correct=result.correct, hints_used=hints_used)
        new_streak = _next_streak(player.streak, result.correct)

        updated_player = dataclasses.replace(
            player,
            streak=new_streak,
            total_score=player.total_score + score,
            last_played_at=datetime.now(timezone.utc),
        )
        self._player_repository.save(updated_player)

        self._attempt_repository.record(
            Attempt(
                attempt_id=str(uuid.uuid4()),
                player_id=player_id,
                case_id=case_id.value,
                selected_suspect_id=submitted_suspect_id,
                correct=result.correct,
                score=score,
                hints_used=hints_used,
                created_at=datetime.now(timezone.utc),
            )
        )

        feedback = "Correct." if result.correct else "Not quite — review the clues again."

        return SubmitSolutionResult(
            correct=result.correct,
            score=score,
            feedback=feedback,
            solution_explanation=result.explanation,
            streak=new_streak,
        )
