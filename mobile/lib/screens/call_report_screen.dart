import 'package:flutter/material.dart';
import 'package:share_plus/share_plus.dart';

/// Post-call report screen shown after auto-hangup or call end.
/// Displays threat summary, hangup reason, transcript, and PDRM report.
class CallReportScreen extends StatelessWidget {
  final String sessionId;
  final String callerName;
  final String callerNumber;
  final int scamProbability;
  final Map<String, dynamic>? threatSummary;
  final List<Map<String, dynamic>> transcript;
  final List<Map<String, dynamic>> events;
  final String? endedBy;
  final String? endedAtIso;
  final String? startTimeIso;
  final VoidCallback onDismiss;

  const CallReportScreen({
    super.key,
    required this.sessionId,
    required this.callerName,
    required this.callerNumber,
    required this.scamProbability,
    this.threatSummary,
    required this.transcript,
    required this.events,
    this.endedBy,
    this.endedAtIso,
    this.startTimeIso,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final riskLevel = (threatSummary?['risk_level'] ?? 'unknown').toString();
    final riskScore = (threatSummary?['risk_score'] as num?)?.toDouble() ?? 0;
    final confidence = (threatSummary?['confidence'] as num?)?.toDouble() ?? 0;
    final reasonCodes = _extractReasonCodes();
    final callActionCodes = _extractCallActionReasonCodes();
    final riskColor = _getRiskColor(riskLevel);

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              riskColor.withOpacity(0.15),
              Colors.white,
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Header
              _buildHeader(context, riskLevel, riskColor),

              // Scrollable content
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Auto-hangup reason
                      if (callActionCodes.isNotEmpty)
                        _buildHangupReasonCard(callActionCodes),

                      const SizedBox(height: 12),

                      // Threat summary
                      _buildThreatSummaryCard(
                        riskLevel: riskLevel,
                        riskScore: riskScore,
                        confidence: confidence,
                        riskColor: riskColor,
                        reasonCodes: reasonCodes,
                      ),

                      const SizedBox(height: 12),

                      // Transcript
                      if (transcript.isNotEmpty) _buildTranscriptCard(),

                      const SizedBox(height: 12),

                      // PDRM Report
                      _buildPdrmReportCard(
                        riskLevel: riskLevel,
                        riskScore: riskScore,
                        reasonCodes: reasonCodes,
                      ),

                      const SizedBox(height: 12),

                      // Event timeline
                      if (events.isNotEmpty) _buildEventTimeline(),

                      const SizedBox(height: 20),

                      // Actions
                      _buildActionButtons(context, riskLevel, riskScore, reasonCodes),

                      const SizedBox(height: 16),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, String riskLevel, Color riskColor) {
    final endedByLabel = _humanizeEndedBy(endedBy);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      decoration: BoxDecoration(
        color: riskColor.withOpacity(0.1),
        border: Border(bottom: BorderSide(color: riskColor.withOpacity(0.3))),
      ),
      child: Column(
        children: [
          Icon(
            riskLevel == 'critical' || riskLevel == 'high'
                ? Icons.warning_amber_rounded
                : Icons.check_circle_outline,
            color: riskColor,
            size: 48,
          ),
          const SizedBox(height: 8),
          const Text(
            'Call Ended',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: riskColor.withOpacity(0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: riskColor.withOpacity(0.4)),
            ),
            child: Text(
              riskLevel.toUpperCase(),
              style: TextStyle(
                color: riskColor,
                fontSize: 12,
                fontWeight: FontWeight.bold,
                letterSpacing: 1,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            endedByLabel,
            style: TextStyle(color: Colors.grey[600], fontSize: 13),
          ),
          Text(
            '$callerName  |  $callerNumber',
            style: TextStyle(color: Colors.grey[500], fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildHangupReasonCard(List<String> codes) {
    return Card(
      elevation: 0,
      color: Colors.red.withOpacity(0.06),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.red.withOpacity(0.2)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.gpp_bad, color: Colors.red, size: 20),
                SizedBox(width: 8),
                Text(
                  'Auto-Hangup Triggered',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Colors.red,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            ...codes.map((code) {
              final humanized = _humanizeReasonCode(code);
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        humanized,
                        style: const TextStyle(fontSize: 13, height: 1.3),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildThreatSummaryCard({
    required String riskLevel,
    required double riskScore,
    required double confidence,
    required Color riskColor,
    required List<String> reasonCodes,
  }) {
    final hasDeepfake = reasonCodes.any((c) => c.contains('deepfake'));

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.analytics, size: 20),
                SizedBox(width: 8),
                Text(
                  'Threat Analysis',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Score bars
            _buildScoreRow('Scam Risk', riskScore * 100, riskColor),
            const SizedBox(height: 8),
            _buildScoreRow('Confidence', confidence * 100, Colors.blue),
            const SizedBox(height: 8),
            _buildScoreRow('Scam Probability', scamProbability.toDouble(), _getScamColor()),
            const SizedBox(height: 12),
            // Detection flags
            Row(
              children: [
                _buildDetectionChip(
                  'Deepfake',
                  hasDeepfake,
                  hasDeepfake ? Colors.red : Colors.green,
                ),
                const SizedBox(width: 8),
                _buildDetectionChip(
                  riskLevel.toUpperCase(),
                  riskLevel == 'high' || riskLevel == 'critical',
                  riskColor,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildScoreRow(String label, double value, Color color) {
    return Row(
      children: [
        SizedBox(
          width: 100,
          child: Text(label, style: TextStyle(fontSize: 12, color: Colors.grey[600])),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (value / 100).clamp(0.0, 1.0),
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation(color),
              minHeight: 8,
            ),
          ),
        ),
        const SizedBox(width: 8),
        SizedBox(
          width: 40,
          child: Text(
            '${value.toStringAsFixed(0)}%',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 13,
              color: color,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDetectionChip(String label, bool detected, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            detected ? Icons.warning : Icons.check,
            color: color,
            size: 14,
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTranscriptCard() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.chat, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Call Transcript',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
                const Spacer(),
                Text(
                  '${transcript.length} messages',
                  style: TextStyle(color: Colors.grey[500], fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...transcript.take(20).map((msg) {
              final text = (msg['text'] ?? '').toString();
              final isUser = msg['isUser'] == true;
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 24,
                      height: 24,
                      decoration: BoxDecoration(
                        color: isUser
                            ? Colors.red.withOpacity(0.15)
                            : Colors.green.withOpacity(0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        isUser ? Icons.person : Icons.support_agent,
                        color: isUser ? Colors.red : Colors.green,
                        size: 12,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isUser ? 'Scammer' : 'Uncle Ah Hock',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: isUser ? Colors.red : Colors.green[700],
                            ),
                          ),
                          Text(text, style: const TextStyle(fontSize: 13, height: 1.3)),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            }),
            if (transcript.length > 20)
              Text(
                '... and ${transcript.length - 20} more messages',
                style: TextStyle(color: Colors.grey[500], fontSize: 12),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPdrmReportCard({
    required String riskLevel,
    required double riskScore,
    required List<String> reasonCodes,
  }) {
    // Detect scam type from reason codes
    final scamType = reasonCodes
        .where((c) => c.startsWith('llm_scam_type_'))
        .map((c) => c.replaceFirst('llm_scam_type_', '').replaceAll('_', ' '))
        .join(', ');

    return Card(
      elevation: 0,
      color: const Color(0xFFF0F4FF),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.blue[900]!.withOpacity(0.2)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.local_police, color: Colors.blue[900], size: 22),
                const SizedBox(width: 8),
                Text(
                  'PDRM SCAM REPORT',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Colors.blue[900],
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
            const Divider(height: 20),
            _buildReportRow('Case ID', sessionId),
            _buildReportRow('Date', _formatDate()),
            _buildReportRow('Caller', '$callerName ($callerNumber)'),
            _buildReportRow('Risk Level', riskLevel.toUpperCase()),
            _buildReportRow('Risk Score', '${(riskScore * 100).toStringAsFixed(0)}%'),
            if (scamType.isNotEmpty) _buildReportRow('Scam Type', scamType),
            _buildReportRow('Messages', '${transcript.length}'),
            if (reasonCodes.isNotEmpty)
              _buildReportRow('Signals', reasonCodes.map(_humanizeReasonCode).join('; ')),
          ],
        ),
      ),
    );
  }

  Widget _buildReportRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEventTimeline() {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.timeline, size: 20),
                SizedBox(width: 8),
                Text(
                  'Event Timeline',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...events.take(10).map((event) {
              final type = (event['type'] ?? '').toString();
              final actor = (event['actor'] ?? '').toString();
              final ts = (event['ts'] ?? '').toString();
              final timeStr = ts.length >= 19 ? ts.substring(11, 19) : ts;
              final icon = _getEventIcon(type);
              final color = _getEventColor(type);

              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(icon, color: color, size: 14),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '$type${actor.isNotEmpty ? ' ($actor)' : ''}',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                    Text(
                      timeStr,
                      style: TextStyle(
                        fontSize: 10,
                        color: Colors.grey[500],
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButtons(
    BuildContext context,
    String riskLevel,
    double riskScore,
    List<String> reasonCodes,
  ) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () => _shareReport(riskLevel, riskScore, reasonCodes),
            icon: const Icon(Icons.share),
            label: const Text('Share Report'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue[800],
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: onDismiss,
            icon: const Icon(Icons.home),
            label: const Text('Back to Home'),
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ),
      ],
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  void _shareReport(String riskLevel, double riskScore, List<String> reasonCodes) {
    final buf = StringBuffer();
    buf.writeln('=== VERICALL MALAYSIA - SCAM REPORT ===');
    buf.writeln('');
    buf.writeln('Case ID: $sessionId');
    buf.writeln('Date: ${_formatDate()}');
    buf.writeln('Caller: $callerName ($callerNumber)');
    buf.writeln('Risk Level: ${riskLevel.toUpperCase()}');
    buf.writeln('Risk Score: ${(riskScore * 100).toStringAsFixed(0)}%');
    buf.writeln('Scam Probability: $scamProbability%');
    buf.writeln('');

    if (reasonCodes.isNotEmpty) {
      buf.writeln('--- Detected Signals ---');
      for (final code in reasonCodes) {
        buf.writeln('  * ${_humanizeReasonCode(code)}');
      }
      buf.writeln('');
    }

    if (transcript.isNotEmpty) {
      buf.writeln('--- Transcript (${transcript.length} messages) ---');
      for (final msg in transcript) {
        final speaker = msg['isUser'] == true ? 'Scammer' : 'Uncle Ah Hock';
        buf.writeln('[$speaker] ${msg['text'] ?? ''}');
      }
      buf.writeln('');
    }

    buf.writeln('Generated by VeriCall Malaysia');
    buf.writeln('Report to NSRC: https://www.nsrc.org.my');

    Share.share(buf.toString());
  }

  List<String> _extractReasonCodes() {
    final raw = threatSummary?['reason_codes'];
    if (raw is List) {
      return raw.map((e) => e.toString()).toList();
    }
    return [];
  }

  List<String> _extractCallActionReasonCodes() {
    final raw = threatSummary?['call_action_reason_codes'];
    if (raw is List) {
      return raw.map((e) => e.toString()).toList();
    }
    return [];
  }

  String _formatDate() {
    final now = DateTime.now();
    return '${now.day}/${now.month}/${now.year} ${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
  }

  Color _getRiskColor(String level) {
    switch (level) {
      case 'critical':
        return Colors.red[900]!;
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.amber[700]!;
      case 'safe':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }

  Color _getScamColor() {
    if (scamProbability < 30) return Colors.green;
    if (scamProbability < 60) return Colors.orange;
    return Colors.red;
  }

  String _humanizeEndedBy(String? by) {
    switch (by) {
      case 'threat_engine':
        return 'Auto-terminated by VeriCall AI';
      case 'mobile_client':
        return 'Ended by you';
      case 'web_client':
        return 'Ended from web panel';
      default:
        return 'Call ended';
    }
  }

  String _humanizeReasonCode(String code) {
    if (code.contains('auto_hangup_rule_d')) return 'Synthetic/cloned voice detected while speaking';
    if (code.contains('auto_hangup_rule_c')) return 'Automated bot caller detected';
    if (code.contains('auto_hangup_rule_b')) return 'High deepfake score + high scam risk';
    if (code.contains('auto_hangup_rule_a')) return 'Extended silence from caller';
    if (code.contains('challenge_rule')) return 'Challenge prompt issued';
    if (code.contains('deepfake_signal_active')) return 'Voice cloning technology detected';
    if (code.contains('human_speech_resumed')) return 'Human speech resumed';
    if (code.startsWith('llm_scam_type_')) {
      return 'Scam type: ${code.replaceFirst('llm_scam_type_', '').replaceAll('_', ' ')}';
    }
    if (code.startsWith('llm_urgency_')) {
      return 'Urgency level: ${code.replaceFirst('llm_urgency_', '').replaceAll('_', ' ')}';
    }
    if (code.startsWith('llm_red_flag_')) {
      return 'Red flag: ${code.replaceFirst('llm_red_flag_', '').replaceAll('_', ' ')}';
    }
    return code.replaceAll('_', ' ');
  }

  IconData _getEventIcon(String type) {
    switch (type) {
      case 'ringing':
        return Icons.ring_volume;
      case 'connected':
        return Icons.phone_in_talk;
      case 'hangup':
        return Icons.call_end;
      case 'ended':
        return Icons.stop_circle;
      case 'warning':
        return Icons.warning;
      default:
        return Icons.circle;
    }
  }

  Color _getEventColor(String type) {
    switch (type) {
      case 'ringing':
        return Colors.blue;
      case 'connected':
        return Colors.green;
      case 'hangup':
        return Colors.red;
      case 'ended':
        return Colors.red[900]!;
      case 'warning':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }
}
