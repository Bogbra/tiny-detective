import '../../../case_play/data/dtos/case_dto.dart';

class GenerationEventDto {
  const GenerationEventDto({
    required this.step,
    required this.status,
    this.detail,
    this.attempt,
    this.caseDto,
  });

  final String step;
  final String status;
  final String? detail;
  final int? attempt;
  final CaseDto? caseDto;

  factory GenerationEventDto.fromJson(Map<String, dynamic> json) {
    final caseJson = json['case'] as Map<String, dynamic>?;
    return GenerationEventDto(
      step: json['step'] as String,
      status: json['status'] as String,
      detail: json['detail'] as String?,
      attempt: json['attempt'] as int?,
      caseDto: caseJson != null ? CaseDto.fromJson(caseJson) : null,
    );
  }
}
