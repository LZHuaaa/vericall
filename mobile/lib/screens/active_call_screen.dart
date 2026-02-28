import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../services/api_service.dart';
import '../services/webrtc_service.dart';

/// Active Call Screen - Shows during an active call with AI scam analysis
class ActiveCallScreen extends StatefulWidget {
  final String callerName;
  final String callerNumber;
  final String sessionId;
  final bool isOwner;
  final String? ownerDevice;
  final VoidCallback onHangUp;

  const ActiveCallScreen({
    super.key,
    required this.callerName,
    required this.callerNumber,
    required this.sessionId,
    required this.isOwner,
    required this.ownerDevice,
    required this.onHangUp,
  });

  @override
  State<ActiveCallScreen> createState() => _ActiveCallScreenState();
}

class _ActiveCallScreenState extends State<ActiveCallScreen> {
  final List<TranscriptMessage> _transcript = [];
  StreamSubscription? _transcriptSubscription;
  int _callDuration = 0;
  Timer? _durationTimer;
  double _scamProbability = 0;
  bool _isDefenseActive = true;
  bool _isMuted = false;
  bool _isSpeakerOn = false;
  bool _isSubmittingReport = false;
  bool _endedHandled = false;
  Map<String, dynamic>? _threatSummary;
  String? _callAction;
  final ScrollController _transcriptScrollController = ScrollController();
  WebSocketChannel? _audioChannel;
  StreamSubscription? _audioChannelSubscription;
  final AudioPlayer _relayPlayer = AudioPlayer(playerId: 'demo_relay_player');
  final List<Uint8List> _audioQueue = <Uint8List>[];
  bool _relayPlaying = false;
  String _relayStatus = 'connecting';
  int _lastRelaySeq = 0;
  int _relayReconnectAttempts = 0;
  static const int _maxReconnectAttempts = 5;
  static const Duration _reconnectDelay = Duration(seconds: 3);

  @override
  void initState() {
    super.initState();
    _startCallTimer();
    _listenToTranscript();
    _connectAudioRelay();
  }

  void _startCallTimer() {
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() => _callDuration++);
    });
  }

  String _resolveAudioRelayUrl() {
    final api = context.read<ApiService>();
    final base = Uri.parse(api.baseUrl);
    final scheme = base.scheme == 'https' ? 'wss' : 'ws';
    final host = base.host;
    final port = 8765;
    final pathSession = Uri.encodeComponent(
        widget.sessionId.isEmpty ? 'current_demo' : widget.sessionId);
    return '$scheme://$host:$port/ws/call-audio/$pathSession?role=victim';
  }

  void _connectAudioRelay() {
    final wsUrl = _resolveAudioRelayUrl();
    developer.log('Audio relay connecting to: $wsUrl', name: 'ActiveCall');
    try {
      _audioChannelSubscription?.cancel();
      _audioChannel?.sink.close();

      _audioChannel = IOWebSocketChannel.connect(
        Uri.parse(wsUrl),
        pingInterval: const Duration(seconds: 15),
      );
      if (mounted) {
        setState(() => _relayStatus = 'connecting');
      }
      _audioChannelSubscription = _audioChannel!.stream.listen(
        (data) {
          // First message confirms the connection is live.
          if (_relayStatus == 'connecting' && mounted) {
            setState(() => _relayStatus = 'connected');
            _relayReconnectAttempts = 0;
          }
          _onAudioRelayMessage(data);
        },
        onError: (error) {
          developer.log('Audio relay error: $error',
              name: 'ActiveCall', level: 900);
          if (!mounted) return;
          setState(() => _relayStatus = 'error');
          _scheduleReconnect();
        },
        onDone: () {
          final closeCode = _audioChannel?.closeCode;
          final closeReason = _audioChannel?.closeReason;
          developer.log(
            'Audio relay closed: code=$closeCode reason=$closeReason',
            name: 'ActiveCall',
          );
          if (!mounted) return;
          setState(() => _relayStatus = 'closed');
          _scheduleReconnect();
        },
      );
      // Mark as connected after a short delay if no error occurred,
      // since IOWebSocketChannel.connect is non-blocking.
      Future.delayed(const Duration(seconds: 2), () {
        if (!mounted) return;
        if (_relayStatus == 'connecting') {
          setState(() => _relayStatus = 'waiting');
        }
      });
    } catch (e) {
      developer.log('Audio relay connect exception: $e', name: 'ActiveCall');
      if (mounted) {
        setState(() => _relayStatus = 'error');
      }
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (!mounted) return;
    if (_relayReconnectAttempts >= _maxReconnectAttempts) {
      developer.log(
        'Audio relay: max reconnect attempts reached',
        name: 'ActiveCall',
      );
      return;
    }
    _relayReconnectAttempts++;
    developer.log(
      'Audio relay: reconnect attempt $_relayReconnectAttempts/$_maxReconnectAttempts',
      name: 'ActiveCall',
    );
    Future.delayed(_reconnectDelay, () {
      if (mounted) {
        _connectAudioRelay();
      }
    });
  }

  void _onAudioRelayMessage(dynamic raw) {
    if (raw is! String) return;
    try {
      final payload = jsonDecode(raw);
      if (payload is! Map<String, dynamic>) return;
      final type = (payload['type'] ?? '').toString();
      if (type == 'audio_chunk') {
        final seq = (payload['seq'] as num?)?.toInt() ?? 0;
        _lastRelaySeq = seq;
        final base64Pcm = (payload['pcm16_b64'] ?? '').toString();
        if (base64Pcm.isEmpty) return;
        final pcmBytes = base64Decode(base64Pcm);
        final wavBytes = _pcm16ToWav(pcmBytes, 16000, 1);
        _audioQueue.add(wavBytes);
        _playNextRelayChunk();
      } else if (type == 'control') {
        final state = (payload['state'] ?? '').toString();
        if (mounted) {
          setState(() => _relayStatus = state.isEmpty ? _relayStatus : state);
        }
      }
    } catch (_) {
      // Ignore malformed relay frame.
    }
  }

  Uint8List _pcm16ToWav(Uint8List pcmData, int sampleRate, int channels) {
    final byteRate = sampleRate * channels * 2;
    final blockAlign = channels * 2;
    final fileSize = 36 + pcmData.length;
    final buffer = BytesBuilder();

    void writeString(String value) => buffer.add(ascii.encode(value));
    void writeUint32(int value) {
      final data = ByteData(4)..setUint32(0, value, Endian.little);
      buffer.add(data.buffer.asUint8List());
    }

    void writeUint16(int value) {
      final data = ByteData(2)..setUint16(0, value, Endian.little);
      buffer.add(data.buffer.asUint8List());
    }

    writeString('RIFF');
    writeUint32(fileSize);
    writeString('WAVE');
    writeString('fmt ');
    writeUint32(16);
    writeUint16(1); // PCM
    writeUint16(channels);
    writeUint32(sampleRate);
    writeUint32(byteRate);
    writeUint16(blockAlign);
    writeUint16(16); // bits per sample
    writeString('data');
    writeUint32(pcmData.length);
    buffer.add(pcmData);

    return buffer.toBytes();
  }

  Future<void> _playNextRelayChunk() async {
    if (_relayPlaying || _audioQueue.isEmpty) {
      return;
    }

    _relayPlaying = true;
    final data = _audioQueue.removeAt(0);
    try {
      await _relayPlayer.play(BytesSource(data),
          volume: _isSpeakerOn ? 1.0 : 0.85);
    } catch (_) {
      // Ignore playback errors for a single chunk.
    } finally {
      _relayPlaying = false;
      if (_audioQueue.isNotEmpty) {
        unawaited(_playNextRelayChunk());
      }
    }
  }

  void _listenToTranscript() {
    developer.log(
      'Subscribing to calls/current_demo (sessionId: ${widget.sessionId})',
      name: 'ActiveCall',
    );
    _transcriptSubscription = FirebaseFirestore.instance
        .collection('calls')
        .doc('current_demo')
        .snapshots()
        .listen((snapshot) {
      if (!snapshot.exists) {
        developer.log('calls/current_demo does not exist', name: 'ActiveCall');
        return;
      }
      final data = snapshot.data()!;

      // Guard: skip stale data from a different session
      final docSessionId = (data['sessionId'] ?? '').toString();
      if (widget.sessionId.isNotEmpty &&
          docSessionId.isNotEmpty &&
          docSessionId != widget.sessionId) {
        developer.log(
          'Skipping stale session: doc=$docSessionId widget=${widget.sessionId}',
          name: 'ActiveCall',
        );
        return;
      }

      final transcript = <TranscriptMessage>[];
      final transcriptRaw = data['transcript'];
      if (transcriptRaw is List) {
        for (final item in transcriptRaw) {
          if (item is! Map) continue;
          final entry = Map<String, dynamic>.from(item);
          transcript.add(
            TranscriptMessage(
              text: (entry['text'] ?? '').toString(),
              isUser: entry['isUser'] == true,
              timestamp: DateTime.fromMillisecondsSinceEpoch(
                (entry['timestamp'] as num?)?.toInt() ?? 0,
              ),
            ),
          );
        }
      }
      transcript.sort((a, b) => a.timestamp.compareTo(b.timestamp));

      developer.log(
        'Firestore update: transcript=${transcript.length} entries, '
        'scamProb=${data['scamProbability']}, state=${data['state']}',
        name: 'ActiveCall',
      );

      if (!mounted) return;
      setState(() {
        _scamProbability =
            (data['scamProbability'] as num?)?.toDouble() ?? _scamProbability;
        _transcript
          ..clear()
          ..addAll(transcript);

        // Track threat summary and call action for UI
        final ts = data['threatSummary'];
        if (ts is Map) {
          _threatSummary = Map<String, dynamic>.from(ts);
          _callAction = (_threatSummary?['call_action'] ?? '').toString();
        }
      });

      // Auto-scroll transcript to bottom
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_transcriptScrollController.hasClients) {
          _transcriptScrollController.animateTo(
            _transcriptScrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });

      final callState = (data['state'] ?? '').toString();
      if (callState == 'ended') {
        if (!_endedHandled) {
          _endedHandled = true;
          widget.onHangUp();
        }
      } else {
        _endedHandled = false;
      }
    }, onError: (error) {
      developer.log('Firestore listener error: $error', name: 'ActiveCall');
    });
  }

  @override
  void dispose() {
    _transcriptSubscription?.cancel();
    _transcriptScrollController.dispose();
    _durationTimer?.cancel();
    _audioChannelSubscription?.cancel();
    _audioChannel?.sink.close();
    _relayPlayer.dispose();
    super.dispose();
  }

  String _formatDuration(int seconds) {
    final mins = seconds ~/ 60;
    final secs = seconds % 60;
    return '${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  Color _getScamColor() {
    if (_scamProbability < 30) return Colors.green;
    if (_scamProbability < 60) return Colors.orange;
    return Colors.red;
  }

  String _humanizeRelayStatus(String status) {
    switch (status) {
      case 'connecting':
        return 'Connecting...';
      case 'connected':
        return 'Connected';
      case 'waiting':
        return 'Waiting for audio';
      case 'error':
        return 'Connection failed';
      case 'closed':
        return 'Disconnected';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
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
              _buildCallHeader(),

              // Defense status
              _buildDefenseStatus(),

              if (!widget.isOwner) _buildReadOnlyBanner(),

              // Uncle Ah Hock responding indicator
              _buildUncleRespondingBanner(),

              // Live transcript area
              Expanded(child: _buildTranscriptView()),

              // Scam meter
              _buildScamMeter(),

              const SizedBox(height: 16),

              // Actions
              _buildActions(),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCallHeader() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          // Caller avatar
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: _getScamColor().withOpacity(0.3),
              shape: BoxShape.circle,
              border: Border.all(color: _getScamColor(), width: 2),
            ),
            child: const Icon(Icons.person, color: Colors.white),
          ),
          const SizedBox(width: 16),

          // Caller info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.callerName,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  widget.callerNumber,
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
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
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
    );
  }

  Widget _buildDefenseStatus() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.green.withOpacity(0.3),
            Colors.blue.withOpacity(0.3),
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.shield, color: Colors.green, size: 24),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'AI Scam Analysis Active',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                Text(
                  _isDefenseActive
                      ? 'AI analyzing call in real-time...'
                      : 'Analysis paused',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Audio Relay: ${_humanizeRelayStatus(_relayStatus)}${_lastRelaySeq > 0 ? ' • chunks: $_lastRelaySeq' : ''}',
                  style: TextStyle(
                    color: _relayStatus == 'connected'
                        ? Colors.greenAccent.withOpacity(0.9)
                        : _relayStatus == 'error'
                            ? Colors.redAccent.withOpacity(0.9)
                            : Colors.white.withOpacity(0.65),
                    fontSize: 11,
                  ),
                ),
                ValueListenableBuilder<bool>(
                  valueListenable: WebRTCService.instance.isConnected,
                  builder: (context, connected, _) => Text(
                    'WebRTC Audio: ${connected ? "🟢 Connected" : "⚪ Not active"}',
                    style: TextStyle(
                      color: connected
                          ? Colors.greenAccent.withOpacity(0.9)
                          : Colors.white.withOpacity(0.5),
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: _isDefenseActive,
            onChanged: widget.isOwner
                ? (v) => setState(() => _isDefenseActive = v)
                : null,
            activeColor: Colors.green,
          ),
        ],
      ),
    );
  }

  Widget _buildScamMeter() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _getScamColor().withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _getScamColor().withOpacity(0.5)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Icon(Icons.warning, color: _getScamColor(), size: 20),
              const SizedBox(width: 8),
              const Text(
                'Scam Probability',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Text(
                '${_scamProbability.toStringAsFixed(0)}%',
                style: TextStyle(
                  color: _getScamColor(),
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: _scamProbability / 100,
              backgroundColor: Colors.white.withOpacity(0.1),
              valueColor: AlwaysStoppedAnimation(_getScamColor()),
              minHeight: 8,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReadOnlyBanner() {
    final ownerLabel =
        widget.ownerDevice == 'mobile' ? 'mobile app' : 'web victim panel';
    return Container(
      margin: const EdgeInsets.fromLTRB(20, 10, 20, 0),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.blue.withOpacity(0.2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.blue.withOpacity(0.45)),
      ),
      child: Text(
        'Read-only mirror. Active control on $ownerLabel.',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildUncleRespondingBanner() {
    final isHandling = _callAction == 'none' || _callAction == 'warn' || _callAction == 'challenge';
    final isHangup = _callAction == 'hangup';

    String statusText;
    IconData statusIcon;
    Color statusColor;

    if (isHangup) {
      statusText = 'Uncle Ah Hock triggered auto-hangup';
      statusIcon = Icons.call_end;
      statusColor = Colors.red;
    } else if (isHandling) {
      statusText = 'Uncle Ah Hock is handling the scammer...';
      statusIcon = Icons.support_agent;
      statusColor = Colors.amber;
    } else if (_transcript.isNotEmpty) {
      statusText = 'Uncle Ah Hock is listening...';
      statusIcon = Icons.hearing;
      statusColor = Colors.blue;
    } else {
      statusText = 'Waiting for conversation...';
      statusIcon = Icons.hourglass_top;
      statusColor = Colors.white54;
    }

    return Container(
      margin: const EdgeInsets.fromLTRB(20, 8, 20, 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: statusColor.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: statusColor.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          Icon(statusIcon, color: statusColor, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              statusText,
              style: TextStyle(
                color: statusColor,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          if (_threatSummary != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: statusColor.withOpacity(0.2),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                (_threatSummary?['risk_level'] ?? 'analyzing').toString().toUpperCase(),
                style: TextStyle(
                  color: statusColor,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTranscriptView() {
    if (_transcript.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.chat_bubble_outline, color: Colors.white.withOpacity(0.3), size: 40),
            const SizedBox(height: 8),
            Text(
              'Live transcript will appear here...',
              style: TextStyle(color: Colors.white.withOpacity(0.4), fontSize: 13),
            ),
          ],
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: Row(
              children: [
                Icon(Icons.subtitles, color: Colors.white.withOpacity(0.5), size: 14),
                const SizedBox(width: 6),
                Text(
                  'LIVE TRANSCRIPT',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1,
                  ),
                ),
                const Spacer(),
                Text(
                  '${_transcript.length} message${_transcript.length == 1 ? '' : 's'}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.4),
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ),
          // Messages
          Expanded(
            child: ListView.builder(
              controller: _transcriptScrollController,
              padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
              itemCount: _transcript.length,
              itemBuilder: (context, index) {
                final msg = _transcript[index];
                final isScammer = msg.isUser; // isUser = caller/scammer side
                final timeStr =
                    '${msg.timestamp.hour.toString().padLeft(2, '0')}:${msg.timestamp.minute.toString().padLeft(2, '0')}:${msg.timestamp.second.toString().padLeft(2, '0')}';
                return Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Speaker indicator
                      Container(
                        width: 28,
                        height: 28,
                        margin: const EdgeInsets.only(top: 2),
                        decoration: BoxDecoration(
                          color: isScammer
                              ? Colors.red.withOpacity(0.3)
                              : Colors.green.withOpacity(0.3),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          isScammer ? Icons.person : Icons.support_agent,
                          color: isScammer ? Colors.red : Colors.green,
                          size: 14,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  isScammer ? 'Scammer' : 'Uncle Ah Hock',
                                  style: TextStyle(
                                    color: isScammer ? Colors.red[300] : Colors.green[300],
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  timeStr,
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.3),
                                    fontSize: 9,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              msg.text,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.85),
                                fontSize: 13,
                                height: 1.3,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _buildActionButton(
            icon: _isMuted ? Icons.mic_off : Icons.mic,
            label: _isMuted ? 'Unmute' : 'Mute',
            onTap: () {
              setState(() => _isMuted = !_isMuted);
            },
            disabled: !widget.isOwner,
          ),
          _buildActionButton(
            icon: _isSpeakerOn ? Icons.volume_up : Icons.hearing,
            label: _isSpeakerOn ? 'Speaker On' : 'Speaker Off',
            onTap: () {
              setState(() => _isSpeakerOn = !_isSpeakerOn);
            },
          ),
          _buildHangUpButton(enabled: widget.isOwner),
          _buildActionButton(
            icon: _isSubmittingReport ? Icons.hourglass_top : Icons.report,
            label: _isSubmittingReport ? 'Sending...' : 'Report',
            onTap: _isSubmittingReport ? () {} : _submitQuickReport,
          ),
        ],
      ),
    );
  }

  Future<void> _submitQuickReport() async {
    setState(() => _isSubmittingReport = true);
    try {
      final transcriptText = _transcript
          .map(
            (m) =>
                '[${m.timestamp.toIso8601String()}] ${m.isUser ? "Caller" : "AI"}: ${m.text}',
          )
          .join('\n');

      final api = context.read<ApiService>();
      final userId = await _resolveUserId();
      final result = await api.submitReportAndEvidence(
        userId: userId,
        scamType: _scamProbability >= 60 ? 'suspicious' : 'unknown',
        phoneNumber: widget.callerNumber,
        transcript: transcriptText,
        deepfakeScore: (_scamProbability / 100).clamp(0.0, 1.0),
        callerNumber: widget.callerNumber,
        classificationReason:
            'Submitted from active call screen with scam meter ${_scamProbability.toStringAsFixed(0)}%',
        detectedSignals: [
          if (_scamProbability >= 60) 'high_scam_probability',
          if (_transcript.isNotEmpty) 'live_transcript_available',
        ],
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Report submitted: ${result['report_id']}')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) {
        setState(() => _isSubmittingReport = false);
      }
    }
  }

  Future<String> _resolveUserId() async {
    final auth = FirebaseAuth.instance;
    if (auth.currentUser == null) {
      await auth.signInAnonymously();
    }
    return auth.currentUser?.uid ?? 'mobile_user_unknown';
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
    bool disabled = false,
  }) {
    return GestureDetector(
      onTap: disabled ? null : onTap,
      child: Column(
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: disabled
                  ? Colors.white.withOpacity(0.05)
                  : Colors.white.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child:
                Icon(icon, color: disabled ? Colors.white38 : Colors.white70),
          ),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              color: disabled ? Colors.white38 : Colors.white70,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHangUpButton({required bool enabled}) {
    return GestureDetector(
      onTap: () {
        if (enabled) {
          widget.onHangUp();
          return;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Only the owner device can end this call.')),
        );
      },
      child: Column(
        children: [
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              color: enabled ? Colors.red : Colors.grey,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: (enabled ? Colors.red : Colors.grey).withOpacity(0.4),
                  blurRadius: 12,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: const Icon(Icons.call_end, color: Colors.white, size: 28),
          ),
          const SizedBox(height: 8),
          const Text(
            'End Call',
            style: TextStyle(
              color: Colors.red,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class TranscriptMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  TranscriptMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}
