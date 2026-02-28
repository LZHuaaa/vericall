class HomeOverview {
  final int threatsSeen;
  final int familyLinked;
  final int highRiskAlerts24h;

  const HomeOverview({
    required this.threatsSeen,
    required this.familyLinked,
    required this.highRiskAlerts24h,
  });

  HomeOverview copyWith({
    int? threatsSeen,
    int? familyLinked,
    int? highRiskAlerts24h,
  }) {
    return HomeOverview(
      threatsSeen: threatsSeen ?? this.threatsSeen,
      familyLinked: familyLinked ?? this.familyLinked,
      highRiskAlerts24h: highRiskAlerts24h ?? this.highRiskAlerts24h,
    );
  }
}
