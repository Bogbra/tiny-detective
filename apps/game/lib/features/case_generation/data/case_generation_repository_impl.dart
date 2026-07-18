import '../../case_play/data/dtos/case_dto.dart';
import '../../case_play/domain/detective_case.dart';
import '../../clues/domain/clue.dart';
import '../../suspects/domain/suspect.dart';
import '../application/case_generation_repository.dart';
import '../domain/generation_event.dart';
import 'case_generation_api_client.dart';
import 'dtos/generation_event_dto.dart';

class CaseGenerationRepositoryImpl implements CaseGenerationRepository {
  CaseGenerationRepositoryImpl(this._apiClient);

  final CaseGenerationApiClient _apiClient;

  @override
  Stream<GenerationEvent> generateCase() {
    return _apiClient.generateCase().map(_toGenerationEvent);
  }

  GenerationEvent _toGenerationEvent(GenerationEventDto dto) {
    return GenerationEvent(
      step: dto.step,
      status: dto.status,
      detail: dto.detail,
      attempt: dto.attempt,
      generatedCase: dto.caseDto != null
          ? _toDetectiveCase(dto.caseDto!)
          : null,
    );
  }

  DetectiveCase _toDetectiveCase(CaseDto dto) {
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
}
