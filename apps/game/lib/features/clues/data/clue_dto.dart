class ClueDto {
  const ClueDto({required this.clueId, required this.text});

  final String clueId;
  final String text;

  factory ClueDto.fromJson(Map<String, dynamic> json) {
    return ClueDto(clueId: json['clueId'] as String, text: json['text'] as String);
  }
}
