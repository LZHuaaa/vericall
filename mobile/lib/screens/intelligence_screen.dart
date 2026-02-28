import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

/// Scam Intelligence Screen - Interactive intelligence feed powered by Gemini Grounding
class IntelligenceScreen extends StatefulWidget {
  const IntelligenceScreen({super.key});

  @override
  State<IntelligenceScreen> createState() => _IntelligenceScreenState();
}

class _IntelligenceScreenState extends State<IntelligenceScreen> {
  bool _isLoading = false;
  String? _error;
  Map<String, dynamic>? _intelligence;
  List<Map<String, dynamic>> _communityReports = [];

  // Stats data
  Map<String, dynamic>? _stats;

  // Filter state
  String _selectedFilter = 'All';

  // Collapsible pattern state
  final Set<int> _expandedPatterns = {};

  // Quiz state
  int _quizIndex = 0;
  bool _quizAnswered = false;
  bool _quizCorrect = false;
  List<Map<String, dynamic>> _quizQuestions = [];

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final apiService = context.read<ApiService>();
      final results = await Future.wait([
        apiService.getDailyIntelligence(region: 'Malaysia'),
        apiService.getScamReports(limit: 10),
        apiService.getScamStats().catchError((_) => <String, dynamic>{}),
      ]);
      if (!mounted) return;
      final intel = results[0];
      final reportsResponse = results[1];
      final stats = results[2];
      final reports = (reportsResponse['reports'] as List<dynamic>?) ?? [];
      setState(() {
        _intelligence = intel;
        _communityReports =
            reports.map((r) => Map<String, dynamic>.from(r as Map)).toList();
        _stats = stats;
        _isLoading = false;
        _quizQuestions = _generateQuizQuestions(intel);
        _quizIndex = 0;
        _quizAnswered = false;
        _expandedPatterns.clear();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  // ── Helpers ──

  bool _matchesFilter(String scamType) {
    if (_selectedFilter == 'All') return true;
    return scamType.toLowerCase() == _selectedFilter.toLowerCase();
  }

  /// Maps intelligence scam_type to a vaccine scenario key.
  String? _mapToVaccineKey(String scamType) {
    final t = scamType.toLowerCase();
    if (t.contains('lhdn') || t.contains('tax') || t.contains('cukai')) {
      return 'lhdn';
    }
    if (t.contains('police') || t.contains('polis') || t.contains('pdrm')) {
      return 'police';
    }
    if (t.contains('bank') || t.contains('maybank') || t.contains('cimb') ||
        t.contains('financial') || t.contains('fraud')) {
      return 'bank';
    }
    if (t.contains('parcel') || t.contains('courier') || t.contains('pos') ||
        t.contains('customs') || t.contains('kastam')) {
      return 'parcel';
    }
    return null;
  }

  // ── Quiz Question Generation ──

  List<Map<String, dynamic>> _generateQuizQuestions(
      Map<String, dynamic> intel) {
    final questions = <Map<String, dynamic>>[];
    final patterns = (intel['new_patterns'] as List<dynamic>?) ?? [];

    // Generate "SCAM" questions from real patterns (all of them)
    for (final p in patterns) {
      final pattern = Map<String, dynamic>.from(p as Map);
      final desc = (pattern['description'] ?? '').toString();
      if (desc.isEmpty) continue;
      final scamType = (pattern['scam_type'] ?? 'unknown').toString();
      questions.add({
        'scenario':
            desc.length > 150 ? '${desc.substring(0, 150)}...' : desc,
        'is_scam': true,
        'explanation':
            'This matches a known $scamType scam pattern '
                'recently reported in Malaysia.',
        'scam_type': scamType,
      });
    }

    // Generate "LEGIT" counterparts dynamically based on scam types found
    final seenLegitTypes = <String>{};
    for (final p in patterns) {
      final pattern = Map<String, dynamic>.from(p as Map);
      final scamType = (pattern['scam_type'] ?? '').toString().toLowerCase();
      if (scamType.isEmpty || seenLegitTypes.contains(scamType)) continue;
      seenLegitTypes.add(scamType);

      final legit = _generateLegitCounterpart(scamType);
      if (legit != null) questions.add(legit);
    }

    // If we got fewer than 4 questions total, add generic legit fallbacks
    if (questions.where((q) => q['is_scam'] == false).isEmpty) {
      questions.addAll(_fallbackLegitQuestions());
    }

    questions.shuffle();
    return questions;
  }

  /// Generate a "LEGIT" quiz question that mirrors a real scam type,
  /// showing what the legitimate version looks like.
  Map<String, dynamic>? _generateLegitCounterpart(String scamType) {
    final t = scamType.toLowerCase();

    if (t.contains('lhdn') || t.contains('tax') || t.contains('cukai')) {
      return {
        'scenario':
            'LHDN sends a physical letter to your registered address '
                'with your tax assessment reference number, directing you '
                'to log in to the official MyTax portal at mytax.hasil.gov.my.',
        'is_scam': false,
        'explanation':
            'Official LHDN communications come via post or the MyTax '
                'portal. They never call demanding immediate payment.',
        'scam_type': 'lhdn',
      };
    }

    if (t.contains('police') || t.contains('polis') || t.contains('pdrm')) {
      return {
        'scenario':
            'A police officer in uniform visits your house with an '
                'official warrant bearing a court seal, asking you to '
                'come to the station during office hours to give a statement.',
        'is_scam': false,
        'explanation':
            'Real police serve warrants in person with proper documentation. '
                'They never demand money transfers over the phone.',
        'scam_type': 'police',
      };
    }

    if (t.contains('bank') || t.contains('maybank') || t.contains('cimb') ||
        t.contains('financial') || t.contains('fraud')) {
      return {
        'scenario':
            'Your bank calls from their published hotline number to '
                'confirm a large transaction you just made, asks you to '
                'verify the amount but does NOT ask for PIN or TAC.',
        'is_scam': false,
        'explanation':
            'Banks may call to verify large transactions but they will '
                'never ask for your PIN, TAC, OTP, or password.',
        'scam_type': 'bank',
      };
    }

    if (t.contains('parcel') || t.contains('courier') || t.contains('pos') ||
        t.contains('customs') || t.contains('kastam')) {
      return {
        'scenario':
            'Pos Malaysia sends an SMS with a tracking number for a '
                'parcel you ordered yesterday, linking to pos.com.my to '
                'track your delivery status.',
        'is_scam': false,
        'explanation':
            'Legitimate delivery notifications reference real orders. '
                'Always verify the URL matches the official domain.',
        'scam_type': 'parcel',
      };
    }

    if (t.contains('investment') || t.contains('money game') || t.contains('forex')) {
      return {
        'scenario':
            'A licensed securities firm listed on SC Malaysia website '
                'sends you their annual investment report via email with '
                'their SC license number for verification.',
        'is_scam': false,
        'explanation':
            'Legitimate investment firms are licensed by Securities '
                'Commission Malaysia. Always verify at sc.com.my.',
        'scam_type': 'investment',
      };
    }

    if (t.contains('love') || t.contains('romance') || t.contains('dating')) {
      return {
        'scenario':
            'Someone you met on a dating app suggests meeting at a '
                'public cafe this weekend. They share their social media '
                'profiles and video call you before the meetup.',
        'is_scam': false,
        'explanation':
            'Genuine people are willing to meet in person and video '
                'call. Scammers avoid face-to-face contact and rush into '
                'financial topics.',
        'scam_type': 'romance',
      };
    }

    // Generic fallback for unknown scam types
    return {
      'scenario':
          'A government agency sends an official letter by registered '
              'mail to your address with a reference number, asking you '
              'to visit their office during business hours with your IC.',
      'is_scam': false,
      'explanation':
          'Legitimate agencies communicate via official channels and '
              'give you time to respond. They never demand immediate '
              'payment over the phone.',
      'scam_type': scamType,
    };
  }

  List<Map<String, dynamic>> _fallbackLegitQuestions() {
    return [
      {
        'scenario':
            'Your bank sends an SMS with a link to update the banking app '
                'via the official Google Play Store or Apple App Store.',
        'is_scam': false,
        'explanation':
            'Banks do send app update reminders. Always verify the link '
                'goes to the official store page.',
        'scam_type': 'bank',
      },
      {
        'scenario':
            'TNB sends a physical bill to your address with meter reading '
                'details and payment due date next month.',
        'is_scam': false,
        'explanation':
            'Utility companies send bills by post with reasonable payment '
                'deadlines. They do not threaten immediate disconnection by phone.',
        'scam_type': 'utility',
      },
    ];
  }

  // ── Build ──

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scam Intelligence')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.error_outline,
                            size: 48, color: Colors.red[300]),
                        const SizedBox(height: 12),
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _loadAll,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadAll,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _buildHeader(),
                      const SizedBox(height: 12),
                      _buildFilterTabs(),
                      const SizedBox(height: 16),
                      _buildStats(),
                      const SizedBox(height: 16),
                      _buildTrendingTypes(),
                      const SizedBox(height: 16),
                      _buildQuizCard(),
                      _buildNewPatterns(),
                      const SizedBox(height: 16),
                      _buildAdvisories(),
                      const SizedBox(height: 16),
                      _buildCommunityReports(),
                    ],
                  ),
                ),
    );
  }

  // ── Header ──

  Widget _buildHeader() {
    final intel = _intelligence ?? {};
    final date =
        (intel['intelligence_date'] ?? intel['timestamp'] ?? '').toString();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          colors: [Color(0xFF0d1b2a), Color(0xFF415a77)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.shield, color: Colors.white, size: 28),
              const SizedBox(width: 10),
              const Text(
                'Scam Intelligence',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 20,
                ),
              ),
              const Spacer(),
              IconButton(
                onPressed: _loadAll,
                icon: const Icon(Icons.refresh, color: Colors.white70),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Region: Malaysia',
            style: TextStyle(
                color: Colors.white.withOpacity(0.8), fontSize: 13),
          ),
          if (date.isNotEmpty)
            Text(
              'Updated: $date',
              style: TextStyle(
                  color: Colors.white.withOpacity(0.6), fontSize: 12),
            ),
        ],
      ),
    );
  }

  // ── Filter Tabs ──

  Widget _buildFilterTabs() {
    final intel = _intelligence ?? {};
    final patterns = (intel['new_patterns'] as List<dynamic>?) ?? [];
    final types = <String>{'All'};
    for (final p in patterns) {
      final m = p as Map;
      final t = (m['scam_type'] ?? '').toString();
      if (t.isNotEmpty) types.add(t);
    }
    for (final r in _communityReports) {
      final t = (r['scam_type'] ?? '').toString();
      if (t.isNotEmpty) types.add(t);
    }

    return SizedBox(
      height: 40,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: types.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final type = types.elementAt(index);
          final isSelected = type == _selectedFilter;
          final color =
              type == 'All' ? Colors.deepPurple : _scamTypeColor(type);
          return GestureDetector(
            onTap: () => setState(() => _selectedFilter = type),
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: isSelected ? color : Colors.grey[100],
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? color : Colors.grey[300]!,
                ),
              ),
              child: Text(
                type == 'All' ? 'All Types' : type.toUpperCase(),
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: isSelected ? Colors.white : Colors.grey[700],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  // ── Visual Stats ──

  Widget _buildStats() {
    final stats = _stats;
    if (stats == null || stats.containsKey('error') || stats.isEmpty) {
      return const SizedBox.shrink();
    }

    final total = (stats['total'] as num?)?.toInt() ?? 0;
    final last24h = (stats['last_24h'] as num?)?.toInt() ?? 0;
    final byType = (stats['by_type'] as Map<String, dynamic>?) ?? {};
    final intel = _intelligence ?? {};
    final patternCount =
        ((intel['new_patterns'] as List<dynamic>?) ?? []).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Scam Overview',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            _buildStatCard(
              icon: Icons.report_problem,
              value: '$total',
              label: 'Total Reports',
              color: Colors.red,
            ),
            const SizedBox(width: 10),
            _buildStatCard(
              icon: Icons.access_time,
              value: '$last24h',
              label: 'Last 24h',
              color: Colors.orange,
            ),
            const SizedBox(width: 10),
            _buildStatCard(
              icon: Icons.trending_up,
              value: '$patternCount',
              label: 'New Patterns',
              color: Colors.blue,
            ),
          ],
        ),
        if (byType.isNotEmpty && total > 0) ...[
          const SizedBox(height: 10),
          _buildTypeDistribution(byType, total),
        ],
      ],
    );
  }

  Widget _buildStatCard({
    required IconData icon,
    required String value,
    required String label,
    required Color color,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            Text(label,
                style: TextStyle(fontSize: 11, color: Colors.grey[600])),
          ],
        ),
      ),
    );
  }

  Widget _buildTypeDistribution(
      Map<String, dynamic> byType, int total) {
    final entries = byType.entries.toList()
      ..sort(
          (a, b) => (b.value as int).compareTo(a.value as int));

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Top Scam Type: ${entries.first.key.toUpperCase()}',
            style:
                const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              height: 12,
              child: Row(
                children: entries.take(5).map((e) {
                  final ratio = (e.value as int) / total;
                  return Expanded(
                    flex: (ratio * 100).round().clamp(1, 100),
                    child: Container(color: _scamTypeColor(e.key)),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 12,
            runSpacing: 4,
            children: entries.take(5).map((e) {
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _scamTypeColor(e.key),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text('${e.key} (${e.value})',
                      style: const TextStyle(fontSize: 10)),
                ],
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  // ── Trending Types ──

  Widget _buildTrendingTypes() {
    final intel = _intelligence ?? {};
    final trending =
        (intel['trending_scam_types'] as List<dynamic>?) ?? [];
    if (trending.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Trending Scam Types',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 6,
          children: trending.map((type) {
            final label = type is Map
                ? (type['type'] ?? type.toString()).toString()
                : type.toString();
            return GestureDetector(
              onTap: () => setState(() => _selectedFilter = label),
              child: Chip(
                label: Text(label, style: const TextStyle(fontSize: 12)),
                backgroundColor:
                    _scamTypeColor(label).withOpacity(0.15),
                side: BorderSide(
                    color: _scamTypeColor(label).withOpacity(0.4)),
                padding: const EdgeInsets.symmetric(horizontal: 4),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ── Quiz Card ──

  Widget _buildQuizCard() {
    if (_quizQuestions.isEmpty) return const SizedBox.shrink();

    if (_quizIndex >= _quizQuestions.length) {
      return Container(
        margin: const EdgeInsets.only(bottom: 16),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Colors.deepPurple.withOpacity(0.1),
              Colors.deepPurple.withOpacity(0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(14),
          border:
              Border.all(color: Colors.deepPurple.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            const Icon(Icons.emoji_events,
                color: Colors.deepPurple, size: 32),
            const SizedBox(height: 8),
            const Text('Quiz Complete!',
                style:
                    TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 4),
            Text(
                'You reviewed all ${_quizQuestions.length} scenarios.',
                style:
                    TextStyle(color: Colors.grey[600], fontSize: 13)),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => setState(() {
                _quizIndex = 0;
                _quizAnswered = false;
                _quizQuestions.shuffle();
              }),
              child: const Text('Restart Quiz'),
            ),
          ],
        ),
      );
    }

    final q = _quizQuestions[_quizIndex];
    final scenario = q['scenario'] as String;
    final isScam = q['is_scam'] as bool;
    final explanation = q['explanation'] as String;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF0d1b2a).withOpacity(0.06),
            Colors.white,
          ],
        ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
            color: const Color(0xFF415a77).withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.quiz,
                  color: Color(0xFF415a77), size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text('Scam or Legit?',
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 15)),
              ),
              Text(
                  '${_quizIndex + 1}/${_quizQuestions.length}',
                  style: TextStyle(
                      fontSize: 12, color: Colors.grey[500])),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'Based on latest intelligence data',
            style: TextStyle(fontSize: 10, color: Colors.grey[500]),
          ),
          const SizedBox(height: 12),
          Text('"$scenario"',
              style: const TextStyle(
                  fontSize: 13, fontStyle: FontStyle.italic)),
          const SizedBox(height: 12),
          if (!_quizAnswered) ...[
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _answerQuiz(true),
                    icon: const Icon(Icons.warning, size: 16),
                    label: const Text('SCAM'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red[50],
                      foregroundColor: Colors.red[700],
                      elevation: 0,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _answerQuiz(false),
                    icon:
                        const Icon(Icons.check_circle, size: 16),
                    label: const Text('LEGIT'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green[50],
                      foregroundColor: Colors.green[700],
                      elevation: 0,
                    ),
                  ),
                ),
              ],
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _quizCorrect
                    ? Colors.green.withOpacity(0.08)
                    : Colors.red.withOpacity(0.08),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: _quizCorrect
                      ? Colors.green.withOpacity(0.3)
                      : Colors.red.withOpacity(0.3),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        _quizCorrect
                            ? Icons.check_circle
                            : Icons.cancel,
                        color: _quizCorrect
                            ? Colors.green
                            : Colors.red,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _quizCorrect ? 'Correct!' : 'Not quite!',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: _quizCorrect
                              ? Colors.green[700]
                              : Colors.red[700],
                        ),
                      ),
                      const Spacer(),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: isScam
                              ? Colors.red.withOpacity(0.15)
                              : Colors.green.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          isScam ? 'WAS A SCAM' : 'WAS LEGIT',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            color: isScam
                                ? Colors.red[700]
                                : Colors.green[700],
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(explanation,
                      style: const TextStyle(fontSize: 12)),
                ],
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: TextButton(
                onPressed: () => setState(() {
                  _quizIndex++;
                  _quizAnswered = false;
                }),
                child: Text(
                  _quizIndex + 1 < _quizQuestions.length
                      ? 'Next Question'
                      : 'See Results',
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  void _answerQuiz(bool userSaidScam) {
    final q = _quizQuestions[_quizIndex];
    final isScam = q['is_scam'] as bool;
    setState(() {
      _quizAnswered = true;
      _quizCorrect = (userSaidScam == isScam);
    });
  }

  // ── New Patterns (Collapsible + Practice) ──

  Widget _buildNewPatterns() {
    final intel = _intelligence ?? {};
    final patterns = (intel['new_patterns'] as List<dynamic>?) ?? [];
    if (patterns.isEmpty) return const SizedBox.shrink();

    final filtered = patterns.where((p) {
      final scamType = ((p as Map)['scam_type'] ?? '').toString();
      return _matchesFilter(scamType);
    }).toList();

    if (filtered.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'New Scam Patterns',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        ...filtered
            .take(8)
            .toList()
            .asMap()
            .entries
            .map((entry) {
          final idx = entry.key;
          final pattern =
              Map<String, dynamic>.from(entry.value as Map);
          final isExpanded = _expandedPatterns.contains(idx);
          return _buildCollapsiblePatternCard(
              pattern, idx, isExpanded);
        }),
      ],
    );
  }

  Widget _buildCollapsiblePatternCard(
    Map<String, dynamic> pattern,
    int index,
    bool isExpanded,
  ) {
    final scamType = (pattern['scam_type'] ?? 'unknown').toString();
    final description = (pattern['description'] ?? '').toString();
    final source = (pattern['source'] ?? '').toString();
    final phoneNumbers =
        (pattern['phone_numbers'] as List<dynamic>?) ?? [];
    final keywords =
        (pattern['keywords'] as List<dynamic>?) ?? [];

    final summary = description.length > 60
        ? '${description.substring(0, 60)}...'
        : description;

    return GestureDetector(
      onTap: () {
        setState(() {
          if (isExpanded) {
            _expandedPatterns.remove(index);
          } else {
            _expandedPatterns.add(index);
          }
        });
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey[200]!),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Always visible: type badge + summary + chevron
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color:
                        _scamTypeColor(scamType).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    scamType.toUpperCase(),
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: _scamTypeColor(scamType),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    summary,
                    style: TextStyle(
                        fontSize: 12, color: Colors.grey[600]),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Icon(
                  isExpanded
                      ? Icons.expand_less
                      : Icons.expand_more,
                  color: Colors.grey[400],
                  size: 22,
                ),
              ],
            ),

            // Expanded content
            if (isExpanded) ...[
              const SizedBox(height: 10),
              if (description.isNotEmpty)
                Text(description,
                    style: const TextStyle(fontSize: 13)),
              if (source.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text('Source: $source',
                    style: TextStyle(
                        fontSize: 11, color: Colors.grey[500])),
              ],
              if (phoneNumbers.isNotEmpty) ...[
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  children: phoneNumbers
                      .take(3)
                      .map((n) => Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.red.withOpacity(0.1),
                              borderRadius:
                                  BorderRadius.circular(6),
                            ),
                            child: Text(
                              n.toString(),
                              style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.red[700]),
                            ),
                          ))
                      .toList(),
                ),
              ],
              if (keywords.isNotEmpty) ...[
                const SizedBox(height: 6),
                Wrap(
                  spacing: 4,
                  runSpacing: 2,
                  children: keywords
                      .take(5)
                      .map((k) => Text(
                            '#${k.toString()}',
                            style: TextStyle(
                                fontSize: 11,
                                color: Colors.blue[600]),
                          ))
                      .toList(),
                ),
              ],
              const SizedBox(height: 10),
              // "Practice This Scam" button
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    final vaccineKey =
                        _mapToVaccineKey(scamType);
                    Navigator.pushNamed(
                      context,
                      '/scam_vaccine',
                      arguments: vaccineKey != null
                          ? {'scam_type': vaccineKey}
                          : null,
                    );
                  },
                  icon: const Icon(Icons.vaccines, size: 16),
                  label: Text(
                    'Practice "$scamType" Scam',
                    style: const TextStyle(fontSize: 12),
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.deepPurple,
                    side: const BorderSide(
                        color: Colors.deepPurple),
                    padding: const EdgeInsets.symmetric(
                        vertical: 10),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ── Advisories ──

  Widget _buildAdvisories() {
    final intel = _intelligence ?? {};
    final advisories =
        (intel['government_advisories'] as List<dynamic>?) ?? [];
    if (advisories.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Government Advisories',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        ...advisories.take(5).map((a) {
          final text = a is Map
              ? (a['title'] ??
                      a['description'] ??
                      a.toString())
                  .toString()
              : a.toString();
          final source =
              a is Map ? (a['source'] ?? '').toString() : '';
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.06),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                  color: Colors.blue.withOpacity(0.2)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline,
                    color: Colors.blue[600], size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(text,
                          style: const TextStyle(fontSize: 13)),
                      if (source.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(source,
                            style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey[500])),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          );
        }),
      ],
    );
  }

  // ── Community Reports (with filter) ──

  Widget _buildCommunityReports() {
    if (_communityReports.isEmpty) return const SizedBox.shrink();

    final filtered = _communityReports.where((r) {
      final t = (r['scam_type'] ?? '').toString();
      return _matchesFilter(t);
    }).toList();

    if (filtered.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Community Reports',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 8),
        ...filtered.take(8).map((report) {
          final scamType =
              (report['scam_type'] ?? 'unknown').toString();
          final phone =
              (report['phone_number'] ?? '').toString();
          final timestamp = (report['timestamp'] ??
                  report['created_at'] ??
                  '')
              .toString();
          final signals =
              (report['detected_signals'] as List<dynamic>?) ??
                  [];

          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.grey[200]!),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: _scamTypeColor(scamType)
                        .withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(Icons.report,
                      color: _scamTypeColor(scamType),
                      size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(
                        scamType.toUpperCase(),
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                          color: _scamTypeColor(scamType),
                        ),
                      ),
                      if (phone.isNotEmpty)
                        Text(phone,
                            style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[700])),
                      if (signals.isNotEmpty)
                        Text(
                          signals.take(2).join(', '),
                          style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey[500]),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                if (timestamp.isNotEmpty)
                  Text(
                    _formatTimestamp(timestamp),
                    style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[400]),
                  ),
              ],
            ),
          );
        }),
      ],
    );
  }

  // ── Utilities ──

  Color _scamTypeColor(String type) {
    final t = type.toLowerCase();
    if (t.contains('lhdn') || t.contains('tax')) return Colors.orange;
    if (t.contains('police') || t.contains('polis')) return Colors.red;
    if (t.contains('bank')) return Colors.blue;
    if (t.contains('family') || t.contains('emergency')) {
      return Colors.purple;
    }
    if (t.contains('investment') || t.contains('crypto')) {
      return Colors.teal;
    }
    if (t.contains('love') || t.contains('romance')) return Colors.pink;
    if (t.contains('courier') || t.contains('parcel')) return Colors.brown;
    return Colors.grey;
  }

  String _formatTimestamp(String raw) {
    try {
      final dt = DateTime.parse(raw);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${dt.day}/${dt.month}';
    } catch (_) {
      return raw.length > 10 ? raw.substring(0, 10) : raw;
    }
  }
}
