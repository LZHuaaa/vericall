class AlertItem {
  final String id;
  final String protectedUserId;
  final String protectedUserName;
  final String scamType;
  final String riskLevel;
  final DateTime timestamp;

  const AlertItem({
    required this.id,
    required this.protectedUserId,
    required this.protectedUserName,
    required this.scamType,
    required this.riskLevel,
    required this.timestamp,
  });

  factory AlertItem.fromJson(Map<String, dynamic> json) {
    final tsRaw = json['timestamp']?.toString();
    final ts = DateTime.tryParse(tsRaw ?? '') ?? DateTime.now();

    return AlertItem(
      id: (json['id'] ?? '').toString(),
      protectedUserId: (json['protected_user_id'] ?? '').toString(),
      protectedUserName: (json['protected_user_name'] ?? 'Protected User').toString(),
      scamType: (json['scam_type'] ?? 'unknown').toString(),
      riskLevel: (json['risk_level'] ?? 'medium').toString(),
      timestamp: ts,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'protected_user_id': protectedUserId,
      'protected_user_name': protectedUserName,
      'scam_type': scamType,
      'risk_level': riskLevel,
      'timestamp': timestamp.toIso8601String(),
    };
  }
}
