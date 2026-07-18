import '../../case_play/domain/detective_case.dart';

/// One real pipeline-progress event from POST /cases/generate's SSE stream
/// (see services/api/app/application/use_cases/generate_case.py). `step` is
/// one of "generating" | "logic_check" | "safety_check" | "saving" |
/// "quota_check" | "failed"; `status` is one of "running" | "passed" |
/// "rejected" | "done". Plain strings, not enums — matches how
/// DetectiveCase.difficulty is already a plain String in this codebase
/// rather than a parsed enum.
class GenerationEvent {
  const GenerationEvent({
    required this.step,
    required this.status,
    this.detail,
    this.attempt,
    this.generatedCase,
  });

  final String step;
  final String status;
  final String? detail;
  final int? attempt;
  final DetectiveCase? generatedCase;
}
