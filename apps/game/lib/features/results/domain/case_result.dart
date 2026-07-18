class CaseResult {
  const CaseResult({
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

  /// True when this wasn't the player's first submission for this case —
  /// score/streak are unaffected server-side (see SubmitSolution's
  /// already_solved gate), so the UI shouldn't play the full "you scored!"
  /// juice a second time either.
  final bool alreadySolved;
}
