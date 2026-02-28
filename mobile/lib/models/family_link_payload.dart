class FamilyLinkPayload {
  final String type;
  final String code;
  final String victimId;

  const FamilyLinkPayload({
    required this.type,
    required this.code,
    required this.victimId,
  });

  factory FamilyLinkPayload.fromJson(Map<String, dynamic> json) {
    return FamilyLinkPayload(
      type: (json['type'] ?? '').toString(),
      code: (json['code'] ?? '').toString(),
      victimId: (json['victimId'] ?? '').toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'code': code,
      'victimId': victimId,
    };
  }
}
