import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

/// Home Screen - Dashboard showing protection status and live backend metrics
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isProtectionActive = true;
  bool _isLoading = false;
  String? _error;

  int _threatsBlocked = 0;
  int _familyMembers = 0;
  int _highRiskAlerts24h = 0;
  List<_ActivityItem> _activities = [];

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final auth = FirebaseAuth.instance;
      if (auth.currentUser == null) {
        await auth.signInAnonymously();
      }
      final userId = auth.currentUser?.uid;
      if (userId == null || userId.isEmpty) {
        throw Exception('Unable to resolve user identity');
      }

      final apiService = context.read<ApiService>();

      final stats = await apiService.getScamStats();
      final family = await apiService.getFamilyMembers(userId);
      final alerts = await apiService.getAlerts(userId, limit: 20);
      final reportsResponse = await apiService.getScamReports(limit: 5);

      final highRisk24h = alerts.where((a) {
        final risk = (a['risk_level'] ?? '').toString().toLowerCase();
        if (risk != 'high' && risk != 'critical') return false;
        final ts = DateTime.tryParse((a['timestamp'] ?? '').toString());
        if (ts == null) return false;
        return DateTime.now().difference(ts).inHours <= 24;
      }).length;

      final activities = <_ActivityItem>[];
      for (final alert in alerts.take(4)) {
        activities.add(
          _ActivityItem(
            icon: Icons.warning_amber_rounded,
            title: '${(alert['scam_type'] ?? 'Unknown').toString().toUpperCase()} alert',
            subtitle: 'Risk: ${(alert['risk_level'] ?? 'medium').toString().toUpperCase()}',
            time: _relativeTime((alert['timestamp'] ?? '').toString()),
            color: Colors.orange,
          ),
        );
      }

      final reports = (reportsResponse['reports'] as List<dynamic>? ?? []);
      for (final report in reports.take(3)) {
        final data = Map<String, dynamic>.from(report as Map);
        activities.add(
          _ActivityItem(
            icon: Icons.report,
            title: 'Community report: ${data['scam_type'] ?? 'unknown'}',
            subtitle: data['phone_number']?.toString() ?? 'Unknown caller',
            time: _relativeTime(data['timestamp']?.toString() ?? ''),
            color: Colors.red,
          ),
        );
      }

      setState(() {
        _threatsBlocked = (stats['total'] as num?)?.toInt() ?? 0;
        _familyMembers = family.length;
        _highRiskAlerts24h = highRisk24h;
        _activities = activities;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadDashboard,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(),
                const SizedBox(height: 24),
                _buildProtectionCard(),
                const SizedBox(height: 20),
                _buildStatsRow(),
                const SizedBox(height: 24),
                Text(
                  'Quick Actions',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 12),
                _buildQuickActions(),
                const SizedBox(height: 24),
                Text(
                  'Recent Activity',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 12),
                if (_isLoading)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.only(top: 24),
                      child: CircularProgressIndicator(),
                    ),
                  )
                else if (_error != null)
                  Text(_error!, style: const TextStyle(color: Colors.red))
                else
                  _buildRecentActivity(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'VeriCall',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Theme.of(context).colorScheme.primary,
                  ),
            ),
            Text(
              'Live protection status',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
        IconButton(
          onPressed: _loadDashboard,
          icon: const Icon(Icons.refresh),
        ),
      ],
    );
  }

  Widget _buildProtectionCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: _isProtectionActive
              ? [const Color(0xFF0066FF), const Color(0xFF00D4AA)]
              : [Colors.grey[400]!, Colors.grey[600]!],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        children: [
          Icon(
            _isProtectionActive ? Icons.shield : Icons.shield_outlined,
            size: 64,
            color: Colors.white,
          ),
          const SizedBox(height: 16),
          Text(
            _isProtectionActive ? 'Protection Active' : 'Protection Disabled',
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _isProtectionActive
                ? 'Your app is monitoring scam indicators'
                : 'Enable protection before taking calls',
            style: TextStyle(fontSize: 14, color: Colors.white.withOpacity(0.9)),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: () {
              setState(() => _isProtectionActive = !_isProtectionActive);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor:
                  _isProtectionActive ? const Color(0xFF0066FF) : Colors.grey[700],
            ),
            child: Text(_isProtectionActive ? 'Disable' : 'Enable Protection'),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsRow() {
    return Row(
      children: [
        Expanded(
          child: _StatCard(
            icon: Icons.block,
            value: '$_threatsBlocked',
            label: 'Threats Seen',
            color: Colors.red,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatCard(
            icon: Icons.family_restroom,
            value: '$_familyMembers',
            label: 'Family Linked',
            color: Colors.green,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _StatCard(
            icon: Icons.warning_amber_rounded,
            value: '$_highRiskAlerts24h',
            label: 'High Risk 24h',
            color: Colors.orange,
          ),
        ),
      ],
    );
  }

  Widget _buildQuickActions() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _ActionButton(
                icon: Icons.phone,
                label: 'Call Check',
                color: const Color(0xFF0066FF),
                onTap: () => Navigator.pushNamed(context, '/call'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionButton(
                icon: Icons.search,
                label: 'Scam Intel',
                color: const Color(0xFF00D4AA),
                onTap: () => Navigator.pushNamed(context, '/intelligence'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _ActionButton(
                icon: Icons.warning_amber,
                label: 'Report Scam',
                color: Colors.orange,
                onTap: () => Navigator.pushNamed(context, '/call'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _ActionButton(
                icon: Icons.vaccines,
                label: 'Scam Vaccine',
                color: Colors.deepPurple,
                onTap: () => Navigator.pushNamed(context, '/scam_vaccine'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildRecentActivity() {
    if (_activities.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey[50],
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey[200]!),
        ),
        child: const Text('No activity yet'),
      );
    }

    return Column(
      children: _activities.map((item) {
        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.grey[50],
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.grey[200]!),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: item.color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(item.icon, color: item.color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.title,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    Text(
                      item.subtitle,
                      style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
              Text(
                item.time,
                style: TextStyle(fontSize: 12, color: Colors.grey[500]),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  String _relativeTime(String raw) {
    final ts = DateTime.tryParse(raw);
    if (ts == null) return 'Unknown';
    final diff = DateTime.now().difference(ts);
    if (diff.inMinutes < 1) return 'now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: TextStyle(fontSize: 11, color: Colors.grey[600]),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: color.withOpacity(0.3)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 8),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActivityItem {
  final IconData icon;
  final String title;
  final String subtitle;
  final String time;
  final Color color;

  const _ActivityItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.time,
    required this.color,
  });
}
