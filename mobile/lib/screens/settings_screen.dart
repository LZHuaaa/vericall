import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_service.dart';

/// Settings Screen
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _autoProtection = true;
  bool _familyAlerts = true;
  bool _soundAlerts = true;
  bool _isLoading = false;
  String? _error;
  String? _userId;

  final TextEditingController _nameController =
      TextEditingController(text: 'Protected User');
  final TextEditingController _phoneController =
      TextEditingController(text: '+60');

  @override
  void initState() {
    super.initState();
    _initializeSettings();
  }

  Future<void> _initializeSettings() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final prefs = await SharedPreferences.getInstance();
      _autoProtection = prefs.getBool('auto_protection') ?? true;
      _familyAlerts = prefs.getBool('family_alerts') ?? true;
      _soundAlerts = prefs.getBool('sound_alerts') ?? true;

      final auth = FirebaseAuth.instance;
      if (auth.currentUser == null) {
        await auth.signInAnonymously();
      }
      _userId = auth.currentUser?.uid;

      if (_userId != null) {
        final apiService = context.read<ApiService>();
        try {
          final profile = await apiService.getUserProfile(_userId!);
          _nameController.text =
              (profile['name'] as String?)?.trim().isNotEmpty == true
                  ? profile['name'].toString()
                  : _nameController.text;
          _phoneController.text =
              (profile['phone'] as String?)?.trim().isNotEmpty == true
                  ? profile['phone'].toString()
                  : _phoneController.text;
        } catch (_) {
          await apiService.upsertUserProfile(
            userId: _userId!,
            name: _nameController.text.trim(),
            phone: _phoneController.text.trim(),
            isProtected: _autoProtection,
          );
        }
      }

      setState(() => _isLoading = false);
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  Future<void> _updateToggle(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);

    if (_userId != null) {
      try {
        await context.read<ApiService>().upsertUserProfile(
              userId: _userId!,
              name: _nameController.text.trim(),
              phone: _phoneController.text.trim(),
              isProtected: _autoProtection,
            );
      } catch (_) {
        // UI state is still persisted locally.
      }
    }
  }

  Future<void> _saveProfile() async {
    if (_userId == null) return;

    setState(() => _isLoading = true);
    try {
      await context.read<ApiService>().upsertUserProfile(
            userId: _userId!,
            name: _nameController.text.trim(),
            phone: _phoneController.text.trim(),
            isProtected: _autoProtection,
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile updated')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _editProfileDialog() async {
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Profile'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Phone'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              await _saveProfile();
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (mounted) {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              children: [
                _buildProfileCard(),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Text(_error!, style: const TextStyle(color: Colors.red)),
                  ),
                const SizedBox(height: 12),
                _buildSectionHeader('Protection'),
                _buildSwitchTile(
                  icon: Icons.shield,
                  title: 'Auto Protection',
                  subtitle: 'Automatically analyze incoming calls',
                  value: _autoProtection,
                  onChanged: (v) async {
                    setState(() => _autoProtection = v);
                    await _updateToggle('auto_protection', v);
                  },
                ),
                _buildSectionHeader('Notifications'),
                _buildSwitchTile(
                  icon: Icons.family_restroom,
                  title: 'Family Alerts',
                  subtitle: 'Get notified when family is targeted',
                  value: _familyAlerts,
                  onChanged: (v) async {
                    setState(() => _familyAlerts = v);
                    await _updateToggle('family_alerts', v);
                  },
                ),
                _buildSwitchTile(
                  icon: Icons.volume_up,
                  title: 'Sound Alerts',
                  subtitle: 'Play sound for scam detection',
                  value: _soundAlerts,
                  onChanged: (v) async {
                    setState(() => _soundAlerts = v);
                    await _updateToggle('sound_alerts', v);
                  },
                ),
                _buildSectionHeader('Family Network'),
                _buildListTile(
                  icon: Icons.group_add,
                  title: 'Add Family Member',
                  subtitle: 'Protect your loved ones',
                  onTap: () => Navigator.pushNamed(context, '/family_link'),
                ),
                _buildListTile(
                  icon: Icons.people,
                  title: 'Manage Family',
                  subtitle: 'Open family linking dashboard',
                  onTap: () => Navigator.pushNamed(context, '/family_link'),
                ),
                _buildSectionHeader('Account'),
                _buildListTile(
                  icon: Icons.person,
                  title: 'Profile',
                  subtitle: 'Edit your information',
                  onTap: _editProfileDialog,
                ),
                _buildListTile(
                  icon: Icons.info,
                  title: 'About VeriCall',
                  subtitle: 'Version 1.0.0',
                  onTap: () {
                    showAboutDialog(
                      context: context,
                      applicationName: 'VeriCall Malaysia',
                      applicationVersion: '1.0.0',
                      applicationLegalese: 'Internal pilot build',
                      children: const [
                        SizedBox(height: 8),
                        Text(
                          'AI-assisted voice scam detection and family protection alerts.',
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 24),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: OutlinedButton(
                    onPressed: () async {
                      await FirebaseAuth.instance.signOut();
                      if (!mounted) return;
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Signed out')),
                      );
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red,
                      side: const BorderSide(color: Colors.red),
                    ),
                    child: const Text('Log Out'),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
    );
  }

  Widget _buildProfileCard() {
    final initials = _nameController.text.trim().isEmpty
        ? 'U'
        : _nameController.text.trim().split(' ').where((s) => s.isNotEmpty).take(2).map((s) => s[0]).join().toUpperCase();

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0066FF), Color(0xFF00D4AA)],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 32,
            backgroundColor: Colors.white,
            child: Text(
              initials,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _nameController.text.trim().isEmpty
                      ? 'Protected User'
                      : _nameController.text.trim(),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  _phoneController.text.trim().isEmpty
                      ? '+60'
                      : _phoneController.text.trim(),
                  style: TextStyle(color: Colors.white.withOpacity(0.9)),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: _editProfileDialog,
            icon: const Icon(Icons.edit, color: Colors.white),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title.toUpperCase(),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Colors.grey[500],
          letterSpacing: 1,
        ),
      ),
    );
  }

  Widget _buildSwitchTile({
    required IconData icon,
    required String title,
    String? subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.primary.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: Theme.of(context).colorScheme.primary),
      ),
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle) : null,
      trailing: Switch(value: value, onChanged: onChanged),
    );
  }

  Widget _buildListTile({
    required IconData icon,
    required String title,
    String? subtitle,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.grey[100],
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: Colors.grey[700]),
      ),
      title: Text(title),
      subtitle: subtitle != null ? Text(subtitle) : null,
      trailing: const Icon(Icons.chevron_right),
      onTap: onTap,
    );
  }
}
