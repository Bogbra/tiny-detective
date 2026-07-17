class HintState {
  const HintState({
    required this.text,
    required this.hintsUsed,
    required this.hintsRemaining,
  });

  final String text;
  final int hintsUsed;
  final int hintsRemaining;

  bool get canRequestMore => hintsRemaining > 0;
}
