import 'package:flutter/foundation.dart';

import '../../../core/errors/api_exception.dart';
import '../../case_play/domain/detective_case.dart';
import '../domain/generation_event.dart';
import 'case_generation_repository.dart';

enum CaseGenerationState {
  idle,
  inProgress,
  success,
  quotaExhausted,
  pipelineFailed,
  networkError,
}

/// Drives the "Generate a new case" flow — every state transition here is a
/// direct reaction to a real event from the backend's SSE stream (see
/// case_generation_api_client.dart), never a timer or a synthetic delay.
/// stepStatuses resets on a genuine attempt restart (a fresh "generating:
/// running" with a higher attempt number than currently tracked) so the
/// checklist visibly restarts exactly when the pipeline actually does.
class CaseGenerationViewModel extends ChangeNotifier {
  CaseGenerationViewModel(this._repository);

  final CaseGenerationRepository _repository;

  CaseGenerationState state = CaseGenerationState.idle;
  int attempt = 1;
  Map<String, String> stepStatuses = {};
  String? lastRejectionDetail;
  DetectiveCase? generatedCase;
  String? errorMessage;

  static const _judgedSteps = {'generating', 'logic_check', 'safety_check'};

  Future<void> start() async {
    state = CaseGenerationState.inProgress;
    attempt = 1;
    stepStatuses = {};
    lastRejectionDetail = null;
    generatedCase = null;
    errorMessage = null;
    notifyListeners();

    try {
      await for (final event in _repository.generateCase()) {
        _handleEvent(event);
      }
    } on ApiException catch (e) {
      state = e.statusCode == 429
          ? CaseGenerationState.quotaExhausted
          : CaseGenerationState.networkError;
      errorMessage = e.statusCode == 429 ? null : _friendlyMessage(e);
      notifyListeners();
    } catch (_) {
      state = CaseGenerationState.networkError;
      errorMessage =
          'Could not reach the server. Check your connection and try again.';
      notifyListeners();
    }
  }

  void reset() {
    state = CaseGenerationState.idle;
    notifyListeners();
  }

  void _handleEvent(GenerationEvent event) {
    if (event.attempt != null && event.attempt! > attempt) {
      attempt = event.attempt!;
      stepStatuses = {};
    }

    if (_judgedSteps.contains(event.step)) {
      stepStatuses[event.step] = event.status;
      if (event.status == 'rejected') {
        // Never surface event.detail here — it's the AI judge's/fidelity
        // check's internal reasoning (case-logic token names like
        // "SUSPECT_2", judge-internal vocabulary), meant for logs, not
        // players. A fixed, friendly message instead — same "no raw
        // backend internals in player-facing text" rule as
        // ApiException.fromResponseBody.
        lastRejectionDetail =
            "That attempt didn't pass our quality check — trying again…";
      }
    }

    switch (event.step) {
      case 'quota_check':
        if (event.status == 'rejected') {
          state = CaseGenerationState.quotaExhausted;
        }
      case 'saving':
        stepStatuses[event.step] = event.status;
        if (event.status == 'done') {
          generatedCase = event.generatedCase;
          state = CaseGenerationState.success;
        } else if (event.status == 'rejected') {
          state = CaseGenerationState.quotaExhausted;
        }
      case 'failed':
        state = CaseGenerationState.pipelineFailed;
        errorMessage = event.detail;
    }

    notifyListeners();
  }

  String _friendlyMessage(ApiException e) => e.message.isEmpty
      ? 'Could not generate a case (${e.statusCode}).'
      : e.message;
}
