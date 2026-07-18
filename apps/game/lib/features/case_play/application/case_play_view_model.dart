import 'package:flutter/foundation.dart';

import '../../../core/errors/api_exception.dart';
import '../../hints/domain/hint_state.dart';
import '../../results/domain/case_result.dart';
import '../domain/detective_case.dart';
import 'case_repository.dart';

enum CasePlayStatus { loading, error, playing, solved }

class CasePlayViewModel extends ChangeNotifier {
  CasePlayViewModel(this._repository);

  final CaseRepository _repository;

  CasePlayStatus status = CasePlayStatus.loading;
  String? errorMessage;
  DetectiveCase? detectiveCase;
  String? playerId;
  String? selectedSuspectId;
  HintState? hint;
  CaseResult? result;
  bool isSubmitting = false;
  bool isRequestingHint = false;

  Future<void> start() async {
    status = CasePlayStatus.loading;
    errorMessage = null;
    notifyListeners();

    try {
      final id = await _repository.createPlayer();
      final dailyCase = await _repository.getDailyCase();
      playerId = id;
      detectiveCase = dailyCase;
      status = CasePlayStatus.playing;
    } on ApiException catch (e) {
      errorMessage = e.message.isEmpty
          ? 'Something went wrong (${e.statusCode}).'
          : e.message;
      status = CasePlayStatus.error;
    } catch (_) {
      errorMessage =
          'Could not reach the server. Check your connection and try again.';
      status = CasePlayStatus.error;
    }

    notifyListeners();
  }

  void selectSuspect(String suspectId) {
    selectedSuspectId = suspectId;
    notifyListeners();
  }

  /// Swaps in a freshly live-generated case (see the case_generation
  /// feature) without a network round-trip — the case already arrived
  /// fully formed in the SSE stream's final event. Resets exactly the same
  /// per-case state start() resets, so playing a generated case looks and
  /// behaves identically to playing the daily case.
  void loadGeneratedCase(DetectiveCase generatedCase) {
    detectiveCase = generatedCase;
    selectedSuspectId = null;
    hint = null;
    result = null;
    errorMessage = null;
    status = CasePlayStatus.playing;
    notifyListeners();
  }

  Future<void> requestHint() async {
    final currentCase = detectiveCase;
    final id = playerId;
    if (currentCase == null || id == null || isRequestingHint) return;
    if (hint != null && !hint!.canRequestMore) return;

    isRequestingHint = true;
    notifyListeners();

    try {
      hint = await _repository.requestHint(
        caseId: currentCase.caseId,
        playerId: id,
      );
    } on ApiException {
      // Hint limit reached (409) or a transient error — leave existing hint
      // state as-is; the panel simply won't show a new hint this time.
    } finally {
      isRequestingHint = false;
      notifyListeners();
    }
  }

  Future<void> submitSolution() async {
    final currentCase = detectiveCase;
    final id = playerId;
    final suspectId = selectedSuspectId;
    if (currentCase == null ||
        id == null ||
        suspectId == null ||
        isSubmitting) {
      return;
    }

    isSubmitting = true;
    errorMessage = null;
    notifyListeners();

    try {
      result = await _repository.submitSolution(
        caseId: currentCase.caseId,
        playerId: id,
        suspectId: suspectId,
      );
      status = CasePlayStatus.solved;
    } on ApiException catch (e) {
      errorMessage = e.message.isEmpty
          ? 'Could not submit your answer (${e.statusCode}).'
          : e.message;
    } finally {
      isSubmitting = false;
      notifyListeners();
    }
  }
}
