import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

/// Family Link Screen - Victim/guardian handshake via QR or one-time code
class FamilyLinkScreen extends StatefulWidget {
  const FamilyLinkScreen({super.key});

  @override
  State<FamilyLinkScreen> createState() => _FamilyLinkScreenState();
}

class _FamilyLinkScreenState extends State<FamilyLinkScreen>
    with SingleTickerProviderStateMixin {
  String? _linkCode;
  String? _qrUrl;
  bool _isLoading = false;
  String? _error;
  String? _userId;
  List<Map<String, dynamic>> _linkedFamily = [];
  final TextEditingController _codeController = TextEditingController();
  bool _isConsuming = false;

  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _initializeUser();
  }

  Future<void> _initializeUser() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final auth = FirebaseAuth.instance;
      if (auth.currentUser == null) {
        await auth.signInAnonymously();
      }

      _userId = auth.currentUser?.uid;
      if (_userId == null || _userId!.isEmpty) {
        throw Exception('Unable to identify user');
      }

      await _loadFamilyMembers();
      setState(() => _isLoading = false);
    } catch (e) {
      setState(() {
        _error = 'Failed to initialize: ${e.toString().replaceFirst('Exception: ', '')}';
        _isLoading = false;
      });
    }
  }

  Future<void> _loadFamilyMembers() async {
    if (_userId == null) return;

    try {
      final apiService = context.read<ApiService>();
      final members = await apiService.getFamilyMembers(_userId!);
      setState(() => _linkedFamily = members);
    } catch (e) {
      setState(() {
        _error = 'Failed to load family members: ${e.toString().replaceFirst('Exception: ', '')}';
      });
    }
  }

  Future<void> _generateLinkCode() async {
    if (_userId == null) return;

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final result = await apiService.generateFamilyLinkCode(
        victimId: _userId!,
        victimName: 'Protected User',
      );

      final qrData = jsonEncode({
        'type': 'vericall_family_link',
        'code': result['code'],
        'victimId': _userId,
      });

      setState(() {
        _linkCode = result['code'] as String?;
        _qrUrl =
            'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${Uri.encodeComponent(qrData)}';
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to generate code: ${e.toString().replaceFirst('Exception: ', '')}';
        _isLoading = false;
      });
    }
  }

  Future<void> _linkWithCode(String rawCode) async {
    if (_userId == null || _isConsuming) return;

    final code = rawCode.trim().toUpperCase();
    if (code.length != 6) {
      setState(() => _error = 'Please enter a valid 6-character code');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    _isConsuming = true;
    try {
      final apiService = context.read<ApiService>();
      await apiService.consumeFamilyLinkCode(
        code: code,
        guardianId: _userId!,
        guardianName: 'Family Guardian',
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Family linked successfully'),
          backgroundColor: Colors.green,
        ),
      );

      _codeController.clear();
      await _loadFamilyMembers();
    } catch (e) {
      setState(() {
        _error = 'Failed to link: ${e.toString().replaceFirst('Exception: ', '')}';
      });
    } finally {
      _isConsuming = false;
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _openQrScanner() async {
    bool handled = false;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return SizedBox(
          height: MediaQuery.of(context).size.height * 0.72,
          child: Column(
            children: [
              const SizedBox(height: 12),
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[400],
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Scan Parent QR Code',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: MobileScanner(
                  onDetect: (capture) {
                    if (handled) return;
                    final raw = capture.barcodes.first.rawValue;
                    if (raw == null || raw.trim().isEmpty) return;

                    final code = _extractCodeFromQr(raw);
                    if (code == null) {
                      setState(() => _error = 'Invalid QR code format');
                      return;
                    }

                    handled = true;
                    Navigator.of(context).pop();
                    _codeController.text = code;
                    _linkWithCode(code);
                  },
                ),
              ),
              const SizedBox(height: 12),
            ],
          ),
        );
      },
    );
  }

  String? _extractCodeFromQr(String rawValue) {
    try {
      final parsed = jsonDecode(rawValue);
      if (parsed is Map<String, dynamic> &&
          parsed['type'] == 'vericall_family_link') {
        final code = parsed['code']?.toString().toUpperCase();
        if (code != null && code.length == 6) {
          return code;
        }
      }
    } catch (_) {
      // fallback below
    }

    final plain = rawValue.trim().toUpperCase();
    if (plain.length == 6) {
      return plain;
    }
    return null;
  }

  @override
  void dispose() {
    _tabController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Family Protection'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.qr_code), text: "I'm the Parent"),
            Tab(icon: Icon(Icons.qr_code_scanner), text: "I'm the Guardian"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildVictimTab(),
          _buildGuardianTab(),
        ],
      ),
    );
  }

  Widget _buildVictimTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.blue[100]!, Colors.blue[50]!],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Column(
              children: [
                Icon(Icons.elderly, size: 48, color: Colors.blue),
                SizedBox(height: 12),
                Text(
                  'For Protected Family Member',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                SizedBox(height: 8),
                Text(
                  'Show this QR code to your family guardian.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.black54),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          if (_qrUrl != null)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Image.network(
                    _qrUrl!,
                    width: 250,
                    height: 250,
                    errorBuilder: (context, error, stackTrace) {
                      return Container(
                        width: 250,
                        height: 250,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.orange[50],
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.orange.shade200),
                        ),
                        child: const Center(
                          child: Text(
                            'QR image unavailable.\nUse the 6-character code below or regenerate.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 13),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Code: $_linkCode',
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 4,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Expires in 10 minutes',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                  TextButton.icon(
                    onPressed: _isLoading ? null : _generateLinkCode,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Regenerate Code'),
                  ),
                ],
              ),
            )
          else
            ElevatedButton.icon(
              onPressed: _isLoading ? null : _generateLinkCode,
              icon: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.qr_code),
              label: Text(_isLoading ? 'Generating...' : 'Generate QR Code'),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 24),
          _buildLinkedMembers('Linked Family Members', _linkedFamily),
        ],
      ),
    );
  }

  Widget _buildGuardianTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [Colors.green[100]!, Colors.green[50]!],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Column(
              children: [
                Icon(Icons.shield, size: 48, color: Colors.green),
                SizedBox(height: 12),
                Text(
                  'For Family Guardian',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                SizedBox(height: 8),
                Text(
                  'Scan the QR code from parent phone or enter the code manually.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Colors.black54),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              color: Colors.grey[100],
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey[300]!),
            ),
            child: Column(
              children: [
                Icon(Icons.qr_code_scanner, size: 64, color: Colors.grey[500]),
                const SizedBox(height: 14),
                ElevatedButton.icon(
                  onPressed: _isLoading ? null : _openQrScanner,
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Scan QR Code'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Or enter code manually:',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          _buildCodeInput(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
        ],
      ),
    );
  }

  Widget _buildCodeInput() {
    return Row(
      children: [
        Expanded(
          child: TextField(
            controller: _codeController,
            textCapitalization: TextCapitalization.characters,
            maxLength: 6,
            enabled: !_isLoading,
            decoration: const InputDecoration(
              hintText: 'ABC123',
              border: OutlineInputBorder(),
              counterText: '',
            ),
            style: const TextStyle(
              fontSize: 24,
              letterSpacing: 8,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(width: 12),
        ElevatedButton(
          onPressed: _isLoading ? null : () => _linkWithCode(_codeController.text),
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.all(16),
          ),
          child: _isLoading
              ? const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.link),
        ),
      ],
    );
  }

  Widget _buildLinkedMembers(String title, List<Map<String, dynamic>> members) {
    if (members.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        ...members.map(
          (member) => Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: Colors.green[100],
                child: const Icon(Icons.shield, color: Colors.green),
              ),
              title: Text((member['name'] ?? 'Family Member').toString()),
              subtitle: Text('ID: ${member['id'] ?? 'unknown'}'),
              trailing: const Icon(Icons.check_circle, color: Colors.green),
            ),
          ),
        ),
      ],
    );
  }
}
