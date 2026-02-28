import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../services/audio_service.dart';

/// Call Analysis Screen - Record and analyze calls
class CallScreen extends StatefulWidget {
  const CallScreen({super.key});

  @override
  State<CallScreen> createState() => _CallScreenState();
}

class _CallScreenState extends State<CallScreen> {
  final TextEditingController _transcriptController = TextEditingController();
  final TextEditingController _callerNumberController = TextEditingController();

  bool _isRecording = false;
  bool _isAnalyzing = false;
  bool _isSubmittingReport = false;
  bool _isPlaying = false;
  int _recordingSeconds = 0;
  String? _recordedAudioPath;
  String? _analysisError;
  Map<String, dynamic>? _analysisResult;
  Timer? _recordingTimer;
  StreamSubscription<void>? _playbackSubscription;

  // Grounding (Google Search verification)
  bool _isGrounding = false;
  Map<String, dynamic>? _groundingResult;

  // Thinking mode (deep analysis)
  bool _isThinking = false;
  Map<String, dynamic>? _thinkingResult;

  // Pattern extraction
  bool _isExtractingPattern = false;

  @override
  void initState() {
    super.initState();
    final audioService = context.read<AudioService>();
    _playbackSubscription = audioService.onPlaybackComplete.listen((_) {
      if (!mounted) return;
      setState(() => _isPlaying = false);
    });
  }

  @override
  void dispose() {
    _recordingTimer?.cancel();
    _playbackSubscription?.cancel();
    _transcriptController.dispose();
    _callerNumberController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Call Analysis')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildRecordingSection(),
            const SizedBox(height: 20),
            _buildCallerInput(),
            const SizedBox(height: 16),
            _buildTranscriptInput(),
            const SizedBox(height: 20),
            _buildActions(),
            if (_analysisError != null) ...[
              const SizedBox(height: 12),
              Text(
                _analysisError!,
                style: const TextStyle(color: Colors.red),
              ),
            ],
            const SizedBox(height: 24),
            if (_analysisResult != null) _buildResultsCard(),
            // Grounding & Thinking sections (after analysis)
            if (_analysisResult != null) ...[
              const SizedBox(height: 12),
              _buildGroundingButton(),
            ],
            if (_groundingResult != null) ...[
              const SizedBox(height: 12),
              _buildGroundingResultsCard(),
            ],
            if (_thinkingResult != null) ...[
              const SizedBox(height: 16),
              _buildThinkingResultsCard(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRecordingSection() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: _isRecording ? Colors.red[50] : Colors.blue[50],
        border: Border.all(
          color: _isRecording ? Colors.red[200]! : Colors.blue[200]!,
        ),
      ),
      child: Column(
        children: [
          GestureDetector(
            onTap: _toggleRecording,
            child: Container(
              width: 90,
              height: 90,
              decoration: BoxDecoration(
                color: _isRecording ? Colors.red : const Color(0xFF0066FF),
                shape: BoxShape.circle,
              ),
              child: Icon(
                _isRecording ? Icons.stop : Icons.mic,
                size: 44,
                color: Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            _isRecording ? 'Recording ${_formatDuration(_recordingSeconds)}' : 'Tap to record audio',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          if (_recordedAudioPath != null) ...[
            const SizedBox(height: 10),
            Text(
              'Audio ready',
              style: TextStyle(color: Colors.green[700]),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton.icon(
                  onPressed: _togglePlayback,
                  icon: Icon(_isPlaying ? Icons.stop : Icons.play_arrow),
                  label: Text(_isPlaying ? 'Stop Preview' : 'Preview'),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () {
                    setState(() {
                      _recordedAudioPath = null;
                      _analysisResult = null;
                    });
                  },
                  child: const Text('Clear Audio'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCallerInput() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Caller number (optional)',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _callerNumberController,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            hintText: '+60123456789',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            filled: true,
            fillColor: Colors.grey[50],
          ),
        ),
      ],
    );
  }

  Widget _buildTranscriptInput() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Transcript (optional if audio provided)',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: _transcriptController,
          maxLines: 4,
          decoration: InputDecoration(
            hintText: 'Paste or type transcript text here...',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            filled: true,
            fillColor: Colors.grey[50],
          ),
        ),
      ],
    );
  }

  Widget _buildActions() {
    final isRunning = _isAnalyzing || _isThinking;
    return Column(
      children: [
        ElevatedButton.icon(
          onPressed: isRunning ? null : _analyzeCall,
          icon: isRunning
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.analytics),
          label: Text(
            _isAnalyzing
                ? 'Analyzing...'
                : _isThinking
                    ? 'Deep Analysis...'
                    : 'Analyze Call',
          ),
          style: ElevatedButton.styleFrom(
            minimumSize: const Size(double.infinity, 52),
          ),
        ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          onPressed: (_analysisResult == null || _isSubmittingReport)
              ? null
              : _showReportPreviewDialog,
          icon: _isSubmittingReport
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.report),
          label: Text(
            _isSubmittingReport ? 'Submitting Report...' : 'Submit Report + Evidence',
          ),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size(double.infinity, 52),
          ),
        ),
      ],
    );
  }

  Widget _buildResultsCard() {
    final result = _analysisResult!;
    final threatLevel = _extractThreatLevel(result);
    final recommendation = _extractRecommendation(result);
    final deepfakeScore = _extractDeepfakeScore(result);
    final isScam = _extractIsScam(result);
    final scamType = _extractScamType(result);
    final signals = _extractSignals(result);
    final stages = (result['stages'] as Map<String, dynamic>?) ?? {};

    final levelColors = <String, Color>{
      'critical': Colors.red.shade700,
      'high': Colors.red.shade500,
      'medium': Colors.orange.shade700,
      'low': Colors.amber.shade700,
      'safe': Colors.green.shade700,
      'unknown': Colors.grey.shade700,
    };

    final color = levelColors[threatLevel] ?? Colors.grey.shade700;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: color.withOpacity(0.08),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Threat Level: ${threatLevel.toUpperCase()}',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 20,
              color: color,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Deepfake Score: ${(deepfakeScore * 100).toStringAsFixed(1)}%',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          Text(
            'Scam Detected: ${isScam ? "Yes" : "No"}',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 6),
          Text(
            'Scam Type: $scamType',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          if (recommendation.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              recommendation,
              style: TextStyle(color: Colors.grey[800]),
            ),
          ],
          if (signals.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text(
              'Detected Signals',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            ...signals.take(6).map(
                  (signal) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('- '),
                        Expanded(child: Text(signal)),
                      ],
                    ),
                  ),
                ),
          ],
          if (stages.isNotEmpty) ...[
            const SizedBox(height: 12),
            const Text(
              'Pipeline Stages',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            ...stages.entries.map(
              (entry) {
                final stageData = entry.value is Map<String, dynamic>
                    ? entry.value as Map<String, dynamic>
                    : <String, dynamic>{};
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('${entry.key}: ${stageData['name'] ?? 'completed'}'),
                );
              },
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _toggleRecording() async {
    final audioService = context.read<AudioService>();

    if (_isRecording) {
      _recordingTimer?.cancel();
      final path = await audioService.stopRecording();
      setState(() {
        _isRecording = false;
        _recordedAudioPath = path;
      });

      if (path == null) {
        _showSnackBar(audioService.lastError ?? 'Recording failed');
      }
      return;
    }

    await audioService.startRecording();
    if (!audioService.isRecording) {
      _showSnackBar(audioService.lastError ?? 'Could not start recording');
      return;
    }

    _recordingSeconds = 0;
    _recordingTimer?.cancel();
    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _recordingSeconds += 1);
    });

    setState(() {
      _isRecording = true;
      _analysisResult = null;
      _analysisError = null;
    });
  }

  Future<void> _togglePlayback() async {
    if (_recordedAudioPath == null) return;

    final audioService = context.read<AudioService>();
    if (_isPlaying) {
      await audioService.stopAudio();
      setState(() => _isPlaying = false);
      return;
    }

    await audioService.playAudio(_recordedAudioPath!);
    if (audioService.state == AudioServiceState.error) {
      _showSnackBar(audioService.lastError ?? 'Failed to play audio');
      return;
    }

    setState(() => _isPlaying = true);
  }

  Future<void> _analyzeCall() async {
    final transcript = _transcriptController.text.trim();
    final hasTranscript = transcript.isNotEmpty;
    final hasAudio = _recordedAudioPath != null && _recordedAudioPath!.isNotEmpty;

    if (!hasTranscript && !hasAudio) {
      _showSnackBar('Please record audio or provide transcript');
      return;
    }

    setState(() {
      _isAnalyzing = true;
      _analysisError = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final callerNumber = _callerNumberController.text.trim();

      Map<String, dynamic> result;
      if (hasAudio) {
        result = await apiService.analyzePipeline(_recordedAudioPath!, hasTranscript ? transcript : null);
      } else {
        result = await apiService.analyzeComplete(
          transcript: transcript,
          callerNumber: callerNumber.isEmpty ? null : callerNumber,
          callDuration: 30,
        );
      }

      setState(() {
        _analysisResult = result;
        _isAnalyzing = false;
      });

      // Auto-trigger deep analysis after initial analysis completes
      if (mounted && transcript.isNotEmpty) {
        _deepAnalyze();
      }
    } catch (e) {
      setState(() {
        _analysisError = e.toString().replaceFirst('Exception: ', '');
        _isAnalyzing = false;
      });
    }
  }

  Future<void> _submitReportAndEvidence() async {
    final result = _analysisResult;
    if (result == null) return;

    setState(() => _isSubmittingReport = true);
    try {
      final apiService = context.read<ApiService>();
      final userId = await _resolveUserId();
      final transcript = _transcriptController.text.trim();
      final signals = _extractSignals(result);
      final reportResult = await apiService.submitReportAndEvidence(
        userId: userId,
        scamType: _extractScamType(result),
        phoneNumber: _callerNumberController.text.trim().isEmpty
            ? 'unknown'
            : _callerNumberController.text.trim(),
        transcript: transcript,
        deepfakeScore: _extractDeepfakeScore(result),
        callerNumber: _callerNumberController.text.trim(),
        classificationReason: _extractRecommendation(result),
        detectedSignals: signals,
        moneyRequestEvidence: signals
            .where((s) => s.toLowerCase().contains('money') || s.toLowerCase().contains('transfer'))
            .toList(),
        audioPath: _recordedAudioPath,
      );

      if (!mounted) return;

      // Show confirmation dialog
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 48),
          title: const Text('Report Submitted'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Report ID: ${reportResult['report_id']}'),
              const SizedBox(height: 8),
              const Text(
                'Your report has been submitted to the VeriCall community database and can be used as evidence.',
              ),
            ],
          ),
          actions: [
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );

      // Auto-extract pattern after successful report
      _extractPatternFromReport(transcript, result);
    } catch (e) {
      _showSnackBar(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) {
        setState(() => _isSubmittingReport = false);
      }
    }
  }

  // ── Grounding (Google Search Verification) ──

  Future<void> _verifyWithGoogle() async {
    String transcript = _transcriptController.text.trim();
    if (transcript.isEmpty && _analysisResult != null) {
      final rec = _extractRecommendation(_analysisResult!);
      final scamType = _extractScamType(_analysisResult!);
      final signals = _extractSignals(_analysisResult!);
      transcript = 'Scam type: $scamType. ${rec.isNotEmpty ? rec : ""} '
          'Red flags: ${signals.join(", ")}';
    }
    if (transcript.isEmpty) {
      _showSnackBar('Please provide transcript or analyze audio first');
      return;
    }
    setState(() {
      _isGrounding = true;
      _groundingResult = null;
    });
    try {
      final apiService = context.read<ApiService>();
      final result = await apiService.groundTranscript(transcript);
      if (mounted) setState(() => _groundingResult = result);
    } catch (e) {
      if (mounted) _showSnackBar('Verification failed: ${e.toString().replaceFirst('Exception: ', '')}');
    } finally {
      if (mounted) setState(() => _isGrounding = false);
    }
  }

  Widget _buildGroundingButton() {
    return ElevatedButton.icon(
      onPressed: _isGrounding ? null : _verifyWithGoogle,
      icon: _isGrounding
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
            )
          : const Icon(Icons.travel_explore),
      label: Text(_isGrounding ? 'Verifying...' : 'Verify with Google Search'),
      style: ElevatedButton.styleFrom(
        minimumSize: const Size(double.infinity, 48),
        backgroundColor: const Color(0xFF00897B),
        foregroundColor: Colors.white,
      ),
    );
  }

  Widget _buildGroundingResultsCard() {
    final result = _groundingResult!;
    final riskLevel = (result['risk_assessment'] ?? 'unknown').toString().toLowerCase();
    final riskColor = _riskColor(riskLevel);
    final verifications = (result['verification_results'] as List<dynamic>?) ?? [];
    final summary = (result['grounding_summary'] ?? '').toString();
    final recommendation = (result['recommendation'] ?? '').toString();
    final similarScams = (result['similar_scams_found'] as num?)?.toInt() ?? 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: riskColor.withOpacity(0.08),
        border: Border.all(color: riskColor.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(Icons.travel_explore, color: riskColor),
            const SizedBox(width: 8),
            const Expanded(
              child: Text(
                'Google Search Verification',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
              ),
            ),
            _riskChip(riskLevel, riskColor),
          ]),
          if (summary.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(summary, style: TextStyle(color: Colors.grey[800])),
          ],
          if (similarScams > 0) ...[
            const SizedBox(height: 8),
            Text(
              '$similarScams similar scams found online',
              style: TextStyle(
                color: Colors.red[700],
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          if (verifications.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...verifications.take(5).map((v) {
              final item = Map<String, dynamic>.from(v as Map);
              return _buildVerificationItem(item);
            }),
          ],
          if (recommendation.isNotEmpty) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb_outline, color: Colors.blue, size: 20),
                  const SizedBox(width: 8),
                  Expanded(child: Text(recommendation)),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildVerificationItem(Map<String, dynamic> item) {
    final claim = (item['claim'] ?? '').toString();
    final verdict = (item['verdict'] ?? 'unknown').toString().toLowerCase();
    final evidence = (item['evidence'] ?? '').toString();
    final sourceUrl = (item['source_url'] ?? '').toString();

    final verdictColor = verdict == 'verified'
        ? Colors.green
        : verdict == 'scam_match'
            ? Colors.red
            : Colors.orange;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: verdictColor.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(
              child: Text(claim, style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: verdictColor.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                verdict.replaceAll('_', ' ').toUpperCase(),
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: verdictColor,
                ),
              ),
            ),
          ]),
          if (evidence.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(evidence, style: TextStyle(fontSize: 13, color: Colors.grey[700])),
          ],
          if (sourceUrl.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              sourceUrl,
              style: const TextStyle(fontSize: 11, color: Colors.blue, decoration: TextDecoration.underline),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  Color _riskColor(String level) {
    switch (level) {
      case 'critical':
        return Colors.red.shade700;
      case 'high':
        return Colors.red.shade500;
      case 'medium':
        return Colors.orange.shade700;
      case 'low':
        return Colors.amber.shade700;
      default:
        return Colors.grey.shade600;
    }
  }

  Widget _riskChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }

  // ── Thinking Mode (Deep Analysis) ──

  Future<void> _deepAnalyze() async {
    final transcript = _transcriptController.text.trim();
    final hasAudio = _recordedAudioPath != null;
    if (transcript.isEmpty && !hasAudio) {
      _showSnackBar('Please provide transcript or audio');
      return;
    }
    setState(() {
      _isThinking = true;
      _thinkingResult = null;
    });
    try {
      final apiService = context.read<ApiService>();
      final deepfakeScore = _analysisResult != null ? _extractDeepfakeScore(_analysisResult!) : 0.0;
      final artifacts = _analysisResult != null ? _extractSignals(_analysisResult!) : <String>[];
      final result = await apiService.analyzeWithThinking(
        transcript,
        deepfakeScore: deepfakeScore,
        artifacts: artifacts,
      );
      if (mounted) setState(() => _thinkingResult = result);
    } catch (e) {
      if (mounted) _showSnackBar('Deep analysis failed: ${e.toString().replaceFirst('Exception: ', '')}');
    } finally {
      if (mounted) setState(() => _isThinking = false);
    }
  }

  Widget _buildThinkingResultsCard() {
    final result = _thinkingResult!;
    final riskLevel = (result['risk_assessment'] ?? 'unknown').toString().toLowerCase();
    final confidence = (result['confidence'] as num?)?.toDouble() ?? 0.0;
    final reasoningChain = (result['reasoning_chain'] as List<dynamic>?) ?? [];
    final tactics = (result['manipulation_tactics'] as List<dynamic>?) ?? [];
    final inconsistencies = (result['inconsistencies_found'] as List<dynamic>?) ?? [];
    final novelElements = (result['novel_elements'] as List<dynamic>?) ?? [];
    final depth = (result['thinking_depth'] ?? 'unknown').toString();
    final recommendation = (result['recommendation'] ?? '').toString();

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: Colors.deepPurple.withOpacity(0.06),
        border: Border.all(color: Colors.deepPurple.withOpacity(0.3)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: true,
          leading: const Icon(Icons.psychology, color: Colors.deepPurple),
          title: Text(
            'Deep Analysis ($depth)',
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          subtitle: Text(
            'Confidence: ${(confidence * 100).toStringAsFixed(0)}% | Risk: ${riskLevel.toUpperCase()}',
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (reasoningChain.isNotEmpty) ...[
                    _sectionHeader('Reasoning Chain'),
                    ...reasoningChain.asMap().entries.map(
                      (e) => _numberedItem(e.key + 1, e.value.toString()),
                    ),
                  ],
                  if (tactics.isNotEmpty) ...[
                    _sectionHeader('Manipulation Tactics'),
                    ..._bulletItems(tactics),
                  ],
                  if (inconsistencies.isNotEmpty) ...[
                    _sectionHeader('Inconsistencies Found'),
                    ..._bulletItems(inconsistencies),
                  ],
                  if (novelElements.isNotEmpty) ...[
                    _sectionHeader('Novel Elements'),
                    ..._bulletItems(novelElements),
                  ],
                  if (recommendation.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.deepPurple.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(recommendation),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(top: 12, bottom: 6),
      child: Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
    );
  }

  Widget _numberedItem(int num, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 24,
            child: Text('$num.', style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }

  List<Widget> _bulletItems(List<dynamic> items) {
    return items
        .map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('  \u2022 '),
                  Expanded(child: Text(item.toString())),
                ],
              ),
            ))
        .toList();
  }

  // ── Pattern Extraction (after report) ──

  Future<void> _extractPatternFromReport(String transcript, Map<String, dynamic> analysisResult) async {
    if (transcript.isEmpty) return;
    setState(() => _isExtractingPattern = true);
    try {
      final apiService = context.read<ApiService>();
      final pattern = await apiService.extractPattern(
        transcript,
        audioAnalysis: {
          'deepfake_score': _extractDeepfakeScore(analysisResult),
          'artifacts_detected': _extractSignals(analysisResult),
          'is_deepfake': _extractDeepfakeScore(analysisResult) > 0.7,
        },
      );
      if (mounted) {
        setState(() => _isExtractingPattern = false);
        _showPatternBottomSheet(pattern);
      }
    } catch (e) {
      if (mounted) setState(() => _isExtractingPattern = false);
    }
  }

  void _showPatternBottomSheet(Map<String, dynamic> pattern) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.6,
          maxChildSize: 0.85,
          minChildSize: 0.3,
          expand: false,
          builder: (_, scrollController) {
            return SingleChildScrollView(
              controller: scrollController,
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      decoration: BoxDecoration(
                        color: Colors.grey[400],
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.green.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.green.withOpacity(0.3)),
                    ),
                    child: Row(children: [
                      const Icon(Icons.check_circle, color: Colors.green, size: 32),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('Thank you!', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                            Text('Your report makes VeriCall smarter.', style: TextStyle(color: Colors.grey[700])),
                          ],
                        ),
                      ),
                    ]),
                  ),
                  const SizedBox(height: 20),
                  const Text('Extracted Scam Pattern', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                  const SizedBox(height: 12),
                  _patternField('Scam Type', pattern['scam_type']),
                  _patternField('Language', pattern['language']),
                  _patternField('Severity', '${pattern['severity'] ?? '?'}/10'),
                  _patternField('Opening Script', pattern['opening_script']),
                  _patternListField('Pressure Tactics', pattern['pressure_tactics']),
                  _patternListField('Requested Actions', pattern['requested_actions']),
                  _patternListField('Organizations Mentioned', pattern['mentioned_organizations']),
                  if (pattern['red_flags_summary'] != null)
                    _patternField('Red Flags Summary', pattern['red_flags_summary']),
                  if (pattern['key_phrases'] is List && (pattern['key_phrases'] as List).isNotEmpty)
                    _patternListField('Key Phrases', pattern['key_phrases']),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _patternField(String label, dynamic value) {
    if (value == null || value.toString().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey[600])),
          const SizedBox(height: 2),
          Text(value.toString(), style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }

  Widget _patternListField(String label, dynamic items) {
    if (items is! List || items.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey[600])),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: items
                .map<Widget>((item) => Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue.withOpacity(0.2)),
                      ),
                      child: Text(item.toString(), style: const TextStyle(fontSize: 12)),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  // ── PDRM Report Preview Dialog ──

  Future<void> _showReportPreviewDialog() async {
    final result = _analysisResult;
    if (result == null) return;

    final confirmed = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.75,
          maxChildSize: 0.9,
          minChildSize: 0.4,
          expand: false,
          builder: (_, scrollController) {
            return SingleChildScrollView(
              controller: scrollController,
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      decoration: BoxDecoration(
                        color: Colors.grey[400],
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'PDRM Evidence Report Preview',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const Divider(),
                  _reportSection('Incident Details', [
                    _reportFieldRow('Date/Time', DateTime.now().toIso8601String().split('T').join(' ').substring(0, 19)),
                    _reportFieldRow(
                      'Caller Number',
                      _callerNumberController.text.trim().isEmpty ? 'Unknown' : _callerNumberController.text.trim(),
                    ),
                    _reportFieldRow('Scam Type', _extractScamType(result).toUpperCase()),
                    _reportFieldRow('Threat Level', _extractThreatLevel(result).toUpperCase()),
                  ]),
                  _reportSection('Audio Analysis', [
                    _reportFieldRow('Deepfake Score', '${(_extractDeepfakeScore(result) * 100).toStringAsFixed(1)}%'),
                    _reportFieldRow('Audio Recorded', _recordedAudioPath != null ? 'Yes' : 'No'),
                  ]),
                  _reportSection('Transcript', []),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.grey[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.grey[300]!),
                    ),
                    child: Text(
                      _transcriptController.text.trim().isEmpty
                          ? 'No transcript available'
                          : _transcriptController.text.trim(),
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  const SizedBox(height: 12),
                  _reportSection('Red Flags Detected', []),
                  ..._extractSignals(result).map(
                    (s) => Padding(
                      padding: const EdgeInsets.only(left: 4, bottom: 4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.warning_amber, color: Colors.red[400], size: 16),
                          const SizedBox(width: 8),
                          Expanded(child: Text(s, style: const TextStyle(fontSize: 13))),
                        ],
                      ),
                    ),
                  ),
                  if (_groundingResult != null) ...[
                    const SizedBox(height: 8),
                    _reportSection('Google Verification', [
                      _reportFieldRow(
                        'Risk Assessment',
                        (_groundingResult!['risk_assessment'] ?? 'N/A').toString().toUpperCase(),
                      ),
                      _reportFieldRow(
                        'Similar Scams Found',
                        '${_groundingResult!['similar_scams_found'] ?? 0}',
                      ),
                    ]),
                  ],
                  const SizedBox(height: 24),
                  Row(children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.pop(context, false),
                        child: const Text('Cancel'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => Navigator.pop(context, true),
                        icon: const Icon(Icons.send),
                        label: const Text('Submit to PDRM'),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                      ),
                    ),
                  ]),
                ],
              ),
            );
          },
        );
      },
    );

    if (confirmed == true) {
      await _submitReportAndEvidence();
    }
  }

  Widget _reportSection(String title, List<Widget> children) {
    return Padding(
      padding: const EdgeInsets.only(top: 14, bottom: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          ...children,
        ],
      ),
    );
  }

  Widget _reportFieldRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          SizedBox(width: 130, child: Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 13))),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13))),
        ],
      ),
    );
  }

  Future<String> _resolveUserId() async {
    final auth = FirebaseAuth.instance;
    if (auth.currentUser == null) {
      await auth.signInAnonymously();
    }
    return auth.currentUser?.uid ?? 'mobile_user_unknown';
  }

  String _extractThreatLevel(Map<String, dynamic> result) {
    final level = result['threat_level']?.toString();
    if (level != null && level.isNotEmpty) {
      return level.toLowerCase();
    }

    final verdict = result['verdict']?.toString().toLowerCase();
    if (verdict == 'high') return 'high';
    if (verdict == 'medium') return 'medium';
    if (verdict == 'safe') return 'safe';
    return 'unknown';
  }

  String _extractRecommendation(Map<String, dynamic> result) {
    if (result['recommendation'] != null) {
      return result['recommendation'].toString();
    }

    if (result['explanation'] != null) {
      return result['explanation'].toString();
    }

    return '';
  }

  double _extractDeepfakeScore(Map<String, dynamic> result) {
    final deepfake = result['deepfake'];
    if (deepfake is Map<String, dynamic>) {
      final score = deepfake['score'];
      if (score is num) return score.toDouble();
    }

    final deepfakeAnalysis = result['deepfake_analysis'];
    if (deepfakeAnalysis is Map<String, dynamic>) {
      final score = deepfakeAnalysis['deepfake_score'];
      if (score is num) return score.toDouble();
    }

    final layerAudio = ((result['layers'] as Map<String, dynamic>?)?['layer1_audio']);
    if (layerAudio is Map<String, dynamic>) {
      final score = layerAudio['deepfake_score'] ?? layerAudio['score'];
      if (score is num) return score.toDouble();
    }

    return 0.0;
  }

  bool _extractIsScam(Map<String, dynamic> result) {
    final scam = result['scam'];
    if (scam is Map<String, dynamic>) {
      return scam['is_scam'] == true;
    }

    final layer2 = (result['layers'] as Map<String, dynamic>?)?['layer2_content'];
    if (layer2 is Map<String, dynamic>) {
      return layer2['is_scam'] == true;
    }

    final threat = _extractThreatLevel(result);
    return threat == 'critical' || threat == 'high' || threat == 'medium';
  }

  String _extractScamType(Map<String, dynamic> result) {
    final scam = result['scam'];
    if (scam is Map<String, dynamic> && scam['scam_type'] != null) {
      return scam['scam_type'].toString();
    }

    final layer2 = (result['layers'] as Map<String, dynamic>?)?['layer2_content'];
    if (layer2 is Map<String, dynamic> && layer2['scam_type'] != null) {
      return layer2['scam_type'].toString();
    }

    return 'unknown';
  }

  List<String> _extractSignals(Map<String, dynamic> result) {
    final signals = <String>[];

    final scam = result['scam'];
    if (scam is Map<String, dynamic> && scam['red_flags'] is List) {
      signals.addAll((scam['red_flags'] as List).map((e) => e.toString()));
    }

    final layer2 = (result['layers'] as Map<String, dynamic>?)?['layer2_content'];
    if (layer2 is Map<String, dynamic> && layer2['red_flags'] is List) {
      signals.addAll((layer2['red_flags'] as List).map((e) => e.toString()));
    }

    final layer4 = (result['layers'] as Map<String, dynamic>?)?['layer4_behavior'];
    if (layer4 is Map<String, dynamic> && layer4['red_flags'] is List) {
      signals.addAll((layer4['red_flags'] as List).map((e) => e.toString()));
    }

    return signals.toSet().toList();
  }

  String _formatDuration(int seconds) {
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}
