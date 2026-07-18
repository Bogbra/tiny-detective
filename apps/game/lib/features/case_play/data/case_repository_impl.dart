import '../../clues/domain/clue.dart';
import '../../hints/domain/hint_state.dart';
import '../../results/domain/case_result.dart';
import '../../suspects/domain/suspect.dart';
import '../application/case_repository.dart';
import '../domain/detective_case.dart';
import 'case_api_client.dart';

class CaseRepositoryImpl implements CaseRepository {
  CaseRepositoryImpl(this._apiClient);

  final CaseApiClient _apiClient;

  @override
  Future<String> createPlayer() async {
    final dto = await _apiClient.createPlayer();
    return dto.playerId;
  }

  @override
  Future<DetectiveCase> getDailyCase() async {
    final dto = await _apiClient.getDailyCase();
    return DetectiveCase(
      caseId: dto.caseId,
      title: dto.title,
      setting: dto.setting,
      problem: dto.problem,
      suspects: dto.suspects
          .map(
            (s) => Suspect(
              suspectId: s.suspectId,
              name: s.name,
              role: s.role,
              publicStatement: s.publicStatement,
            ),
          )
          .toList(),
      clues: dto.clues
          .map((c) => Clue(clueId: c.clueId, text: c.text))
          .toList(),
      difficulty: dto.difficulty,
    );
  }

  @override
  Future<CaseResult> submitSolution({
    required String caseId,
    required String playerId,
    required String suspectId,
  }) async {
    final dto = await _apiClient.submitSolution(
      caseId: caseId,
      playerId: playerId,
      suspectId: suspectId,
    );
    return CaseResult(
      correct: dto.correct,
      score: dto.score,
      feedback: dto.feedback,
      solutionExplanation: dto.solutionExplanation,
      streak: dto.streak,
      alreadySolved: dto.alreadySolved,
    );
  }

  @override
  Future<HintState> requestHint({
    required String caseId,
    required String playerId,
  }) async {
    final dto = await _apiClient.requestHint(
      caseId: caseId,
      playerId: playerId,
    );
    return HintState(
      text: dto.text,
      hintsUsed: dto.hintsUsed,
      hintsRemaining: dto.hintsRemaining,
    );
  }
}
