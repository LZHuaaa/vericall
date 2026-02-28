class AnalysisPipelineResult {
  final String verdict;
  final double confidence;
  final double deepfakeScore;
  final bool isFake;
  final bool isScam;
  final String scamType;
  final String recommendation;
  final List<String> redFlags;

  const AnalysisPipelineResult({
    required this.verdict,
    required this.confidence,
    required this.deepfakeScore,
    required this.isFake,
    required this.isScam,
    required this.scamType,
    required this.recommendation,
    required this.redFlags,
  });

  factory AnalysisPipelineResult.fromJson(Map<String, dynamic> json) {
    final deepfake = (json['deepfake'] as Map<String, dynamic>?) ?? {};
    final scam = (json['scam'] as Map<String, dynamic>?) ?? {};
    final flags = (scam['red_flags'] as List<dynamic>? ?? const [])
        .map((e) => e.toString())
        .toList();

    return AnalysisPipelineResult(
      verdict: (json['verdict'] ?? 'unknown').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      deepfakeScore: (deepfake['score'] as num?)?.toDouble() ?? 0.0,
      isFake: deepfake['is_fake'] == true,
      isScam: scam['is_scam'] == true,
      scamType: (scam['scam_type'] ?? 'unknown').toString(),
      recommendation: (json['recommendation'] ?? '').toString(),
      redFlags: flags,
    );
  }
}
