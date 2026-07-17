class CaseResultDto {
  const CaseResultDto({
    required this.correct,
    required this.score,
    required this.feedback,
    required this.solutionExplanation,
    required this.streak,
  });

  final bool correct;
  final int score;
  final String feedback;
  final String solutionExplanation;
  final int streak;

  factory CaseResultDto.fromJson(Map<String, dynamic> json) {
    return CaseResultDto(
      correct: json['correct'] as bool,
      score: json['score'] as int,
      feedback: json['feedback'] as String,
      solutionExplanation: json['solutionExplanation'] as String,
      streak: json['streak'] as int,
    );
  }
}
