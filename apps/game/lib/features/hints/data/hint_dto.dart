class HintDto {
  const HintDto({
    required this.text,
    required this.hintsUsed,
    required this.hintsRemaining,
  });

  final String text;
  final int hintsUsed;
  final int hintsRemaining;

  factory HintDto.fromJson(Map<String, dynamic> json) {
    return HintDto(
      text: json['text'] as String,
      hintsUsed: json['hintsUsed'] as int,
      hintsRemaining: json['hintsRemaining'] as int,
    );
  }
}
