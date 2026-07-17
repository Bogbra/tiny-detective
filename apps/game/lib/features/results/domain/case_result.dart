class CaseResult {
  const CaseResult({
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
}
