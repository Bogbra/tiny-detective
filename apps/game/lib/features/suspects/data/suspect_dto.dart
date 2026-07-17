class SuspectDto {
  const SuspectDto({
    required this.suspectId,
    required this.name,
    required this.role,
    required this.publicStatement,
  });

  final String suspectId;
  final String name;
  final String role;
  final String publicStatement;

  factory SuspectDto.fromJson(Map<String, dynamic> json) {
    return SuspectDto(
      suspectId: json['suspectId'] as String,
      name: json['name'] as String,
      role: json['role'] as String,
      publicStatement: json['publicStatement'] as String,
    );
  }
}
