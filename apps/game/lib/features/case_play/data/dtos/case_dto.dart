import '../../../clues/data/clue_dto.dart';
import '../../../suspects/data/suspect_dto.dart';

class CaseDto {
  const CaseDto({
    required this.caseId,
    required this.title,
    required this.setting,
    required this.problem,
    required this.suspects,
    required this.clues,
    required this.difficulty,
  });

  final String caseId;
  final String title;
  final String setting;
  final String problem;
  final List<SuspectDto> suspects;
  final List<ClueDto> clues;
  final String difficulty;

  factory CaseDto.fromJson(Map<String, dynamic> json) {
    return CaseDto(
      caseId: json['caseId'] as String,
      title: json['title'] as String,
      setting: json['setting'] as String,
      problem: json['problem'] as String,
      suspects: (json['suspects'] as List<dynamic>)
          .map((e) => SuspectDto.fromJson(e as Map<String, dynamic>))
          .toList(),
      clues: (json['clues'] as List<dynamic>)
          .map((e) => ClueDto.fromJson(e as Map<String, dynamic>))
          .toList(),
      difficulty: json['difficulty'] as String,
    );
  }
}
