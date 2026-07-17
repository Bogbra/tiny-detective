import '../../clues/domain/clue.dart';
import '../../suspects/domain/suspect.dart';

class DetectiveCase {
  const DetectiveCase({
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
  final List<Suspect> suspects;
  final List<Clue> clues;
  final String difficulty;
}
