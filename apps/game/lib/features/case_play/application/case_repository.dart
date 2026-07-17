import '../../hints/domain/hint_state.dart';
import '../../results/domain/case_result.dart';
import '../domain/detective_case.dart';

abstract class CaseRepository {
  Future<String> createPlayer();

  Future<DetectiveCase> getDailyCase();

  Future<CaseResult> submitSolution({
    required String caseId,
    required String playerId,
    required String suspectId,
  });

  Future<HintState> requestHint({required String caseId, required String playerId});
}
