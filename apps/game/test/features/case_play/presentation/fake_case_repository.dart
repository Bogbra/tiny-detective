import 'package:game/features/case_play/application/case_repository.dart';
import 'package:game/features/case_play/domain/detective_case.dart';
import 'package:game/features/hints/domain/hint_state.dart';
import 'package:game/features/results/domain/case_result.dart';

/// Hand-rolled test double — no mocking package needed for one small interface.
class FakeCaseRepository implements CaseRepository {
  FakeCaseRepository({
    this.player = 'player-1',
    this.dailyCase,
    this.hintState,
    this.result,
    this.throwOnGetDailyCase,
    this.throwOnSubmit,
    this.throwOnHint,
  });

  final String player;
  DetectiveCase? dailyCase;
  HintState? hintState;
  CaseResult? result;
  Object? throwOnGetDailyCase;
  Object? throwOnSubmit;
  Object? throwOnHint;

  int hintCalls = 0;
  int submitCalls = 0;

  @override
  Future<String> createPlayer() async => player;

  @override
  Future<DetectiveCase> getDailyCase() async {
    final failure = throwOnGetDailyCase;
    if (failure != null) throw failure;
    return dailyCase!;
  }

  @override
  Future<CaseResult> submitSolution({
    required String caseId,
    required String playerId,
    required String suspectId,
  }) async {
    submitCalls += 1;
    final failure = throwOnSubmit;
    if (failure != null) throw failure;
    return result!;
  }

  @override
  Future<HintState> requestHint({required String caseId, required String playerId}) async {
    hintCalls += 1;
    final failure = throwOnHint;
    if (failure != null) throw failure;
    return hintState!;
  }
}
