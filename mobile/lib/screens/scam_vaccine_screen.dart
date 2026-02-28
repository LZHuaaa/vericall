import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:provider/provider.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../services/api_service.dart';

/// Scam Vaccine - Interactive call-based training to recognise scam calls
class ScamVaccineScreen extends StatefulWidget {
  const ScamVaccineScreen({super.key});

  @override
  State<ScamVaccineScreen> createState() => _ScamVaccineScreenState();
}

enum _VaccineStep { intro, ringing, training, results }

class _CallMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  _CallMessage({required this.text, required this.isUser})
      : timestamp = DateTime.now();
}

const _presetResponses = [
  'Hello, who is this?',
  'Can you give me your badge number?',
  "I'll call the official number to verify.",
  'I need to discuss with my family first.',
  'Please send me official documentation.',
  "I don't believe you. This sounds like a scam.",
];

class _ScamVaccineScreenState extends State<ScamVaccineScreen>
    with SingleTickerProviderStateMixin {
  _VaccineStep _step = _VaccineStep.intro;
  String? _sessionId;
  String? _scamLabel;
  bool _isLoading = false;
  String? _error;

  // Training state
  final List<_CallMessage> _messages = [];
  final TextEditingController _customResponseController =
      TextEditingController();
  final List<String> _flaggedRedFlags = [];
  bool _isSending = false;

  // Call timer
  int _callDuration = 0;
  Timer? _durationTimer;

  // Ringing animation
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  Timer? _vibrationTimer;

  // Results state
  Map<String, dynamic>? _results;

  // TTS/STT for voice interaction
  final FlutterTts _tts = FlutterTts();
  final stt.SpeechToText _sttInstance = stt.SpeechToText();
  bool _sttAvailable = false;
  bool _isListening = false;
  String _recognizedText = '';
  bool _isSpeaking = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _initTts();
    _initStt();
  }

  Future<void> _initTts() async {
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(0.5);
    await _tts.setPitch(0.9);
    _tts.setStartHandler(() {
      if (mounted) setState(() => _isSpeaking = true);
    });
    _tts.setCompletionHandler(() {
      if (mounted) setState(() => _isSpeaking = false);
    });
    _tts.setCancelHandler(() {
      if (mounted) setState(() => _isSpeaking = false);
    });
  }

  Future<void> _initStt() async {
    _sttAvailable = await _sttInstance.initialize(
      onStatus: (status) {
        if (status == 'notListening' && mounted) {
          setState(() => _isListening = false);
        }
      },
      onError: (error) {
        if (mounted) setState(() => _isListening = false);
      },
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _vibrationTimer?.cancel();
    _durationTimer?.cancel();
    _customResponseController.dispose();
    _tts.stop();
    _sttInstance.stop();
    super.dispose();
  }

  // ── Start session ──

  Future<void> _startSession() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiService>();
      final targetType =
          (ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?)?['scam_type'] as String?;
      final result = await api.startVaccineSession(scamType: targetType);
      final sessionId = (result['session_id'] ?? '').toString();
      final greeting = (result['greeting'] ?? '').toString();
      final scamLabel = (result['scam_label'] ?? 'Scam Call').toString();

      if (sessionId.isEmpty) {
        throw Exception('No session ID returned');
      }

      setState(() {
        _sessionId = sessionId;
        _scamLabel = scamLabel;
        _step = _VaccineStep.ringing;
        _isLoading = false;
        _messages.clear();
        _flaggedRedFlags.clear();
        if (greeting.isNotEmpty) {
          _messages.add(_CallMessage(text: greeting, isUser: false));
        }
      });

      // Start ringing animation and haptics
      _pulseController.repeat(reverse: true);
      _startVibration();
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  void _startVibration() {
    _vibrationTimer?.cancel();
    _vibrationTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      if (_step == _VaccineStep.ringing) {
        HapticFeedback.heavyImpact();
      } else {
        timer.cancel();
      }
    });
    HapticFeedback.heavyImpact();
  }

  void _answerCall() {
    _pulseController.stop();
    _vibrationTimer?.cancel();
    HapticFeedback.mediumImpact();

    setState(() {
      _step = _VaccineStep.training;
      _callDuration = 0;
    });

    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => _callDuration++);
    });

    // Speak the greeting aloud via TTS
    if (_messages.isNotEmpty && !_messages.first.isUser) {
      _speakText(_messages.first.text);
    }
  }

  void _declineCall() {
    _pulseController.stop();
    _vibrationTimer?.cancel();
    HapticFeedback.mediumImpact();
    _endSession();
  }

  // ── Send response ──

  Future<void> _sendResponse(String text) async {
    if (text.isEmpty || _sessionId == null || _isSending) return;

    setState(() {
      _messages.add(_CallMessage(text: text, isUser: true));
      _isSending = true;
    });

    try {
      final api = context.read<ApiService>();
      final result = await api.vaccineRespond(
        sessionId: _sessionId!,
        userResponse: text,
      );

      final response = (result['response'] ?? '').toString();
      if (response.isNotEmpty && mounted) {
        setState(() {
          _messages.add(_CallMessage(text: response, isUser: false));
        });
        // Speak scammer's response via TTS
        _speakText(response);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  // ── TTS / STT ──

  Future<void> _speakText(String text) async {
    await _tts.stop();
    await _tts.speak(text);
  }

  void _startListening() async {
    if (!_sttAvailable || _isListening || _isSending) return;

    // Stop TTS if speaking
    await _tts.stop();

    setState(() {
      _isListening = true;
      _recognizedText = '';
    });

    await _sttInstance.listen(
      onResult: (result) {
        if (!mounted) return;
        setState(() {
          _recognizedText = result.recognizedWords;
        });
        if (result.finalResult && _recognizedText.isNotEmpty) {
          setState(() => _isListening = false);
          _sendResponse(_recognizedText);
        }
      },
      listenFor: const Duration(seconds: 15),
      pauseFor: const Duration(seconds: 3),
      localeId: 'en_US',
    );
  }

  void _stopListening() async {
    await _sttInstance.stop();
    if (mounted) {
      setState(() => _isListening = false);
      if (_recognizedText.isNotEmpty) {
        _sendResponse(_recognizedText);
      }
    }
  }

  void _showResponseSheet() {
    _customResponseController.clear();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Choose your response',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Text(
                'Select a preset or type your own:',
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 12),
              ..._presetResponses.map((response) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: SizedBox(
                    width: double.infinity,
                    child: OutlinedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        _sendResponse(response);
                      },
                      style: OutlinedButton.styleFrom(
                        alignment: Alignment.centerLeft,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                      ),
                      child: Text(response),
                    ),
                  ),
                );
              }),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _customResponseController,
                      decoration: InputDecoration(
                        hintText: 'Type custom response...',
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 10),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                        ),
                        filled: true,
                        fillColor: Colors.grey[50],
                      ),
                      textInputAction: TextInputAction.send,
                      onSubmitted: (text) {
                        if (text.trim().isNotEmpty) {
                          Navigator.pop(context);
                          _sendResponse(text.trim());
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: () {
                      final text = _customResponseController.text.trim();
                      if (text.isNotEmpty) {
                        Navigator.pop(context);
                        _sendResponse(text);
                      }
                    },
                    icon: const Icon(Icons.send),
                    color: Colors.deepPurple,
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  // ── Flag Red Flags ──

  void _showFlagSheet() {
    final flags = <String, bool>{
      'Urgency / time pressure': false,
      'Money transfer request': false,
      'Personal info request': false,
      'Impersonation of authority': false,
      'Threats or intimidation': false,
    };

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return StatefulBuilder(builder: (context, setModalState) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Flag Red Flags',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  'Select the red flags you noticed:',
                  style: TextStyle(color: Colors.grey[600]),
                ),
                const SizedBox(height: 12),
                ...flags.entries.map((entry) {
                  return CheckboxListTile(
                    title: Text(entry.key),
                    value: entry.value,
                    onChanged: (v) {
                      setModalState(() => flags[entry.key] = v ?? false);
                    },
                    controlAffinity: ListTileControlAffinity.leading,
                    dense: true,
                    activeColor: Colors.deepPurple,
                  );
                }),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      final selected = flags.entries
                          .where((e) => e.value)
                          .map((e) => e.key)
                          .toList();
                      for (final flag in selected) {
                        if (!_flaggedRedFlags.contains(flag)) {
                          _flaggedRedFlags.add(flag);
                        }
                      }
                      Navigator.pop(context);
                      if (selected.isNotEmpty && mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content:
                                Text('${selected.length} red flag(s) recorded'),
                            backgroundColor: Colors.deepPurple,
                          ),
                        );
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.deepPurple,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Confirm'),
                  ),
                ),
              ],
            ),
          );
        });
      },
    );
  }

  // ── End session ──

  Future<void> _endSession() async {
    if (_sessionId == null) return;
    _durationTimer?.cancel();

    setState(() => _isLoading = true);
    try {
      final api = context.read<ApiService>();
      final result = await api.endVaccineSession(_sessionId!);
      if (mounted) {
        setState(() {
          _results = result;
          _step = _VaccineStep.results;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  void _reset() {
    _durationTimer?.cancel();
    _pulseController.stop();
    _vibrationTimer?.cancel();
    _tts.stop();
    _sttInstance.stop();
    setState(() {
      _step = _VaccineStep.intro;
      _sessionId = null;
      _scamLabel = null;
      _messages.clear();
      _flaggedRedFlags.clear();
      _results = null;
      _error = null;
      _callDuration = 0;
      _isListening = false;
      _recognizedText = '';
      _isSpeaking = false;
    });
  }

  String _formatDuration(int seconds) {
    final mins = seconds ~/ 60;
    final secs = seconds % 60;
    return '${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  // ── Build ──

  @override
  Widget build(BuildContext context) {
    final showAppBar =
        _step == _VaccineStep.intro || _step == _VaccineStep.results;

    return Scaffold(
      appBar: showAppBar
          ? AppBar(title: const Text('Scam Vaccine'))
          : null,
      body: switch (_step) {
        _VaccineStep.intro => _buildIntro(),
        _VaccineStep.ringing => _buildRinging(),
        _VaccineStep.training => _buildTraining(),
        _VaccineStep.results => _buildResults(),
      },
    );
  }

  // ── Intro ──

  Widget _buildIntro() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const SizedBox(height: 20),
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: Colors.deepPurple.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.vaccines,
                size: 50, color: Colors.deepPurple),
          ),
          const SizedBox(height: 24),
          const Text(
            'Scam Vaccine Training',
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Text(
            'Practice identifying scam calls in a safe environment. '
            'An AI will simulate a scammer calling you -- try to spot '
            'the red flags and flag them during the call.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 15, color: Colors.grey[700]),
          ),
          const SizedBox(height: 16),
          _buildInfoCard(
            icon: Icons.phone_callback,
            title: 'Receive a Scam Call',
            description:
                'A simulated scam call will ring -- answer to begin training.',
          ),
          _buildInfoCard(
            icon: Icons.flag_outlined,
            title: 'Flag Red Flags',
            description:
                'Tap the flag button when you spot manipulation tactics.',
          ),
          _buildInfoCard(
            icon: Icons.score,
            title: 'Get Your Score',
            description:
                'Hang up when ready to see how well you identified threats.',
          ),
          const SizedBox(height: 24),
          if (_error != null) ...[
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 12),
          ],
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _isLoading ? null : _startSession,
              icon: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.play_arrow),
              label: Text(_isLoading ? 'Starting...' : 'Start Training'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.deepPurple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoCard({
    required IconData icon,
    required String title,
    required String description,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.deepPurple.withOpacity(0.04),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.deepPurple.withOpacity(0.15)),
      ),
      child: Row(
        children: [
          Icon(icon, color: Colors.deepPurple, size: 28),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 14)),
                const SizedBox(height: 2),
                Text(description,
                    style: TextStyle(fontSize: 13, color: Colors.grey[600])),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── Ringing (Simulated Incoming Call) ──

  Widget _buildRinging() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF1a1a2e),
            Color(0xFF16213e),
            Color(0xFF0f3460),
          ],
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 60),

            // Caller info with animated rings
            Column(
              children: [
                Stack(
                  alignment: Alignment.center,
                  children: [
                    AnimatedBuilder(
                      animation: _pulseAnimation,
                      builder: (context, child) {
                        return Container(
                          width: 140 * _pulseAnimation.value,
                          height: 140 * _pulseAnimation.value,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: Colors.red.withOpacity(0.3),
                              width: 2,
                            ),
                          ),
                        );
                      },
                    ),
                    Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: Colors.red.withOpacity(0.5),
                          width: 3,
                        ),
                      ),
                    ),
                    Container(
                      width: 100,
                      height: 100,
                      decoration: const BoxDecoration(
                        shape: BoxShape.circle,
                        color: Color(0xFFe94560),
                      ),
                      child: const Icon(Icons.person,
                          size: 50, color: Colors.white),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                const Text(
                  'Unknown Caller',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '+60-XXX-XXXXXX',
                  style: TextStyle(
                    fontSize: 18,
                    color: Colors.white.withOpacity(0.7),
                    letterSpacing: 1.5,
                  ),
                ),
                const SizedBox(height: 12),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.phone_callback,
                          color: Colors.white70, size: 16),
                      SizedBox(width: 8),
                      Text(
                        'Incoming Call',
                        style: TextStyle(color: Colors.white70, fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const Spacer(),

            // Training mode badge
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 32),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.deepPurple.withOpacity(0.3),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.deepPurple.withOpacity(0.5)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.vaccines, color: Colors.deepPurple, size: 28),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'TRAINING MODE',
                          style: TextStyle(
                            color: Colors.deepPurple,
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'This is a simulated scam call for training',
                          style:
                              TextStyle(color: Colors.white70, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const Spacer(),

            // Answer / Decline buttons
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  // Decline
                  _buildCallButton(
                    icon: Icons.call_end,
                    label: 'Decline',
                    color: Colors.red,
                    onTap: _declineCall,
                  ),
                  // Answer (animated)
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _pulseAnimation.value,
                        child: _buildCallButton(
                          icon: Icons.call,
                          label: 'Answer',
                          color: Colors.green,
                          onTap: _answerCall,
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),

            const SizedBox(height: 60),
          ],
        ),
      ),
    );
  }

  Widget _buildCallButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Column(
      children: [
        GestureDetector(
          onTap: onTap,
          child: Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: color.withOpacity(0.4),
                  blurRadius: 20,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: Icon(icon, color: Colors.white, size: 32),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          label,
          style: const TextStyle(color: Colors.white70, fontSize: 14),
        ),
      ],
    );
  }

  // ── Training (In-Call UI) ──

  Widget _buildTraining() {
    final latestScammerMsg = _messages.lastWhere(
      (m) => !m.isUser,
      orElse: () => _CallMessage(text: '', isUser: false),
    );
    final exchanges = _messages.where((m) => m.isUser).length;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF0d1b2a),
            Color(0xFF1b263b),
            Color(0xFF415a77),
          ],
        ),
      ),
      child: SafeArea(
        child: Column(
          children: [
            // Call header
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Container(
                    width: 50,
                    height: 50,
                    decoration: BoxDecoration(
                      color: Colors.red.withOpacity(0.3),
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.red, width: 2),
                    ),
                    child:
                        const Icon(Icons.person, color: Colors.white),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _scamLabel ?? 'Scam Call',
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                        Text(
                          '+60-XXX-XXXXXX',
                          style: TextStyle(
                            fontSize: 14,
                            color: Colors.white.withOpacity(0.7),
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Duration
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: const BoxDecoration(
                            color: Colors.red,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _formatDuration(_callDuration),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Training mode banner
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 20),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.deepPurple.withOpacity(0.3),
                    Colors.deepPurple.withOpacity(0.2),
                  ],
                ),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                    color: Colors.deepPurple.withOpacity(0.5)),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.deepPurple,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Text(
                      'TRAINING',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    '$exchanges response${exchanges == 1 ? '' : 's'}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 12,
                    ),
                  ),
                  const Spacer(),
                  if (_flaggedRedFlags.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${_flaggedRedFlags.length} flag${_flaggedRedFlags.length == 1 ? '' : 's'}',
                        style: const TextStyle(
                          color: Colors.red,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                ],
              ),
            ),

            const Spacer(),

            // Scammer's latest message (what you're "hearing")
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 20),
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.3),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Icon(Icons.hearing, color: Colors.white.withOpacity(0.6), size: 18),
                      const SizedBox(width: 8),
                      Text(
                        'Caller is saying:',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_isSending)
                    Row(
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white.withOpacity(0.5),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Caller speaking...',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    )
                  else if (latestScammerMsg.text.isNotEmpty)
                    Text(
                      latestScammerMsg.text,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.9),
                        fontSize: 15,
                        height: 1.4,
                      ),
                    )
                  else
                    Text(
                      'Waiting for caller...',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.5),
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                ],
              ),
            ),

            const Spacer(),

            // Listening indicator / recognized text
            if (_isListening || _recognizedText.isNotEmpty && _isSending) ...[
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 20),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.blue.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    if (_isListening) ...[
                      const SizedBox(
                        width: 16, height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.blue,
                        ),
                      ),
                      const SizedBox(width: 10),
                    ],
                    Expanded(
                      child: Text(
                        _isListening
                            ? (_recognizedText.isEmpty
                                ? 'Listening... speak now'
                                : _recognizedText)
                            : _recognizedText,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.85),
                          fontSize: 13,
                          fontStyle: _recognizedText.isEmpty
                              ? FontStyle.italic
                              : FontStyle.normal,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
            ],

            // Speaking indicator
            if (_isSpeaking)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 20),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.amber.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.volume_up, color: Colors.amber, size: 16),
                    const SizedBox(width: 8),
                    Text(
                      'Scammer speaking...',
                      style: TextStyle(
                        color: Colors.amber,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),

            const SizedBox(height: 8),

            // Action buttons (call-style)
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildActionButton(
                    icon: Icons.flag,
                    label: 'Flag',
                    color: Colors.orange,
                    onTap: _showFlagSheet,
                  ),
                  // Mic button (primary interaction)
                  GestureDetector(
                    onTap: _isSending ? null : (_isListening ? _stopListening : _startListening),
                    child: Column(
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: _isListening ? Colors.blue : Colors.green,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: (_isListening ? Colors.blue : Colors.green)
                                    .withOpacity(0.4),
                                blurRadius: 12,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                          child: Icon(
                            _isListening ? Icons.stop : Icons.mic,
                            color: Colors.white,
                            size: 28,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isListening ? 'Stop' : 'Speak',
                          style: TextStyle(
                            color: _isListening ? Colors.blue : Colors.green[300],
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  _buildActionButton(
                    icon: Icons.reply,
                    label: 'Type',
                    color: Colors.blue,
                    onTap: _isSending ? null : _showResponseSheet,
                  ),
                  // Hang up button
                  GestureDetector(
                    onTap: _isLoading ? null : _endSession,
                    child: Column(
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: Colors.red,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.red.withOpacity(0.4),
                                blurRadius: 12,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                          child: const Icon(Icons.call_end,
                              color: Colors.white, size: 28),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Hang Up',
                          style: TextStyle(
                            color: Colors.red,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback? onTap,
  }) {
    final enabled = onTap != null;
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              color: enabled
                  ? Colors.white.withOpacity(0.12)
                  : Colors.white.withOpacity(0.05),
              shape: BoxShape.circle,
            ),
            child: Icon(icon,
                color: enabled ? color : Colors.white38, size: 26),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              color: enabled ? Colors.white70 : Colors.white38,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  // ── Results ──

  Widget _buildResults() {
    final result = _results ?? {};
    final exchanges =
        (result['exchanges'] as num?)?.toInt() ?? _messages.length;
    final timeFormatted =
        (result['time_wasted_formatted'] ?? '').toString();
    final timeSeconds =
        (result['time_wasted_seconds'] as num?)?.toInt() ?? 0;
    final victory = result['victory'] == true;
    final flagCount = _flaggedRedFlags.length;

    final aiDeployedFlags = (result['red_flags_deployed'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList() ??
        [];

    final caughtFlags =
        _flaggedRedFlags.where((f) => aiDeployedFlags.contains(f)).toList();
    final missedFlags =
        aiDeployedFlags.where((f) => !_flaggedRedFlags.contains(f)).toList();

    final awarenessScore = aiDeployedFlags.isEmpty
        ? ((flagCount * 20) + (exchanges * 2)).clamp(0, 100)
        : (((caughtFlags.length / aiDeployedFlags.length) * 80) +
                (exchanges * 2))
            .round()
            .clamp(0, 100);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          const SizedBox(height: 10),
          // Score circle
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: awarenessScore >= 60
                    ? [Colors.green, Colors.teal]
                    : awarenessScore >= 30
                        ? [Colors.orange, Colors.amber]
                        : [Colors.red, Colors.redAccent],
              ),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$awarenessScore',
                    style: const TextStyle(
                      fontSize: 36,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const Text(
                    'Score',
                    style: TextStyle(fontSize: 14, color: Colors.white70),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            victory
                ? 'Excellent Awareness!'
                : awarenessScore >= 60
                    ? 'Good Job!'
                    : 'Keep Practising',
            style:
                const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            aiDeployedFlags.isNotEmpty
                ? 'You caught ${caughtFlags.length} of ${aiDeployedFlags.length} red flags in $exchanges exchanges.'
                : 'You engaged in $exchanges exchanges and flagged $flagCount red flag(s).',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey[600]),
          ),
          const SizedBox(height: 24),

          // Stats row
          Row(
            children: [
              _resultStat(Icons.phone, '$exchanges', 'Exchanges'),
              _resultStat(Icons.flag, '$flagCount', 'Flags'),
              _resultStat(
                Icons.timer,
                timeFormatted.isNotEmpty
                    ? timeFormatted
                    : '${timeSeconds}s',
                'Duration',
              ),
            ],
          ),

          const SizedBox(height: 20),

          // Flagged red flags review
          if (_flaggedRedFlags.isNotEmpty) ...[
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Red Flags You Identified',
                style:
                    TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
            const SizedBox(height: 8),
            ..._flaggedRedFlags.map(
              (flag) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.green.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: Colors.green.withOpacity(0.25)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.check_circle,
                        color: Colors.green, size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                        child: Text(flag,
                            style: const TextStyle(fontSize: 13))),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // Missed red flags
          if (missedFlags.isNotEmpty) ...[
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Red Flags You Missed',
                style:
                    TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
            const SizedBox(height: 8),
            ...missedFlags.map(
              (flag) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(
                    horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: Colors.red.withOpacity(0.25)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.cancel, color: Colors.red, size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                        child: Text(flag,
                            style: const TextStyle(fontSize: 13))),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // Tips
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blue.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.lightbulb_outline,
                        color: Colors.blue, size: 20),
                    SizedBox(width: 8),
                    Text('Tips',
                        style: TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 15)),
                  ],
                ),
                const SizedBox(height: 8),
                ..._getTips().map(
                  (tip) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('  \u2022 '),
                        Expanded(
                            child: Text(tip,
                                style: const TextStyle(fontSize: 13))),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _reset,
              icon: const Icon(Icons.replay),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.deepPurple,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Back to Home'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultStat(IconData icon, String value, String label) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.deepPurple.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, color: Colors.deepPurple, size: 22),
            const SizedBox(height: 6),
            Text(
              value,
              style: const TextStyle(
                  fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(label,
                style: TextStyle(fontSize: 11, color: Colors.grey[600])),
          ],
        ),
      ),
    );
  }

  List<String> _getTips() {
    final tips = <String>[
      'Real organisations never ask for money transfers over the phone.',
      'Verify caller identity by hanging up and calling the official number.',
      'Scammers create urgency -- legitimate calls allow you time to think.',
    ];
    if (!_flaggedRedFlags.contains('Money transfer request')) {
      tips.add(
          'Watch for money transfer requests -- a key scam indicator.');
    }
    if (!_flaggedRedFlags.contains('Impersonation of authority')) {
      tips.add(
          'Scammers often impersonate police, banks, or government agencies.');
    }
    return tips;
  }
}
