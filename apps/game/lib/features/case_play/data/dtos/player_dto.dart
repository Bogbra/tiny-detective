class PlayerDto {
  const PlayerDto({required this.playerId});

  final String playerId;

  factory PlayerDto.fromJson(Map<String, dynamic> json) {
    return PlayerDto(playerId: json['playerId'] as String);
  }
}
