class CaseResultDto {
  const CaseResultDto({
    required this.correct,
    required this.score,
    required this.feedback,
    required this.solutionExplanation,
    required this.streak,
    required this.alreadySolved,
  });

  final bool correct;
  final int score;
  final String feedback;
  final String solutionExplanation;
  final int streak;
  final bool alreadySolved;

  factory CaseResultDto.fromJson(Map<String, dynamic> json) {
    return CaseResultDto(
      correct: json['correct'] as bool,
      score: json['score'] as int,
      feedback: json['feedback'] as String,
      solutionExplanation: json['solutionExplanation'] as String,
      streak: json['streak'] as int,
      // Defaults false for backward compatibility if an older cached
      // response or test fixture omits it — not something the real
      // backend does, but a safe default to have regardless.
      alreadySolved: json['alreadySolved'] as bool? ?? false,
    );
  }
}
