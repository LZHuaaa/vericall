import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

/// Alerts Screen - View family alerts and scam notifications
class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  bool _isLoading = false;
  String? _error;
  List<Map<String, dynamic>> _alerts = [];
  String? _userId;

  @override
  void initState() {
    super.initState();
    _initializeAndLoad();
  }

  Future<void> _initializeAndLoad() async {
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
        throw Exception('Unable to resolve current user');
      }

      final apiService = context.read<ApiService>();
      final alerts = await apiService.getAlerts(userId, limit: 30);

      setState(() {
        _userId = userId;
        _alerts = alerts;
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
    final newCount = _alerts.where((a) => _isRecent(a['timestamp']?.toString())).length;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Alerts'),
        actions: [
          IconButton(
            onPressed: _initializeAndLoad,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _initializeAndLoad,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _buildSummaryCard(newCount),
            const SizedBox(height: 20),
            if (_isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.only(top: 32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_error != null)
              _buildErrorCard(_error!)
            else if (_alerts.isEmpty)
              _buildEmptyState()
            else
              ..._alerts.map(_buildAlertItem),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(int newCount) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFFFF6B6B), Color(0xFFFF8E53)],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(
              Icons.warning_amber,
              color: Colors.white,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$newCount Recent Alerts',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  _userId == null ? 'Loading user...' : 'Live backend feed',
                  style: TextStyle(color: Colors.white.withOpacity(0.9)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard(String error) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red[200]!),
      ),
      child: Text(
        error,
        style: const TextStyle(color: Colors.red),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: const Column(
        children: [
          Icon(Icons.notifications_none, size: 48, color: Colors.grey),
          SizedBox(height: 12),
          Text(
            'No alerts yet',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 6),
          Text(
            'Alerts will appear here when suspicious calls are detected.',
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildAlertItem(Map<String, dynamic> alert) {
    final risk = (alert['risk_level'] ?? 'medium').toString().toLowerCase();
    final scamType = (alert['scam_type'] ?? 'unknown').toString();
    final protectedName = (alert['protected_user_name'] ?? 'Family member').toString();
    final timeText = _formatTimestamp(alert['timestamp']?.toString());

    final riskColor = switch (risk) {
      'critical' => Colors.red.shade700,
      'high' => Colors.red.shade500,
      'medium' => Colors.orange.shade700,
      'low' => Colors.amber.shade700,
      _ => Colors.blueGrey,
    };

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: riskColor.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: riskColor.withOpacity(0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: riskColor.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(Icons.warning_amber_rounded, color: riskColor, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${scamType.toUpperCase()} risk for $protectedName',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  'Risk level: ${risk.toUpperCase()}',
                  style: TextStyle(color: Colors.grey[700], fontSize: 13),
                ),
              ],
            ),
          ),
          Text(
            timeText,
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }

  bool _isRecent(String? isoTimestamp) {
    if (isoTimestamp == null || isoTimestamp.isEmpty) return false;
    final ts = DateTime.tryParse(isoTimestamp);
    if (ts == null) return false;
    return DateTime.now().difference(ts).inHours <= 24;
  }

  String _formatTimestamp(String? isoTimestamp) {
    if (isoTimestamp == null || isoTimestamp.isEmpty) {
      return 'Unknown';
    }

    final ts = DateTime.tryParse(isoTimestamp);
    if (ts == null) {
      return isoTimestamp;
    }

    final now = DateTime.now();
    final diff = now.difference(ts);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return DateFormat('dd/MM, HH:mm').format(ts);
  }
}
