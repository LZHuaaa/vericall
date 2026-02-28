import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// API Service for VeriCall Backend
class ApiService {
  /// Backend base URL resolution order:
  /// 1) --dart-define=VERICALL_API_BASE_URL=<url>
  /// 2) Platform default (Android emulator/iOS simulator/web)
  String get baseUrl {
    const fromEnv = String.fromEnvironment(
      'VERICALL_API_BASE_URL',
      defaultValue: '',
    );
    if (fromEnv.isNotEmpty) {
      return fromEnv;
    }
    if (kIsWeb) {
      return '/api';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        // 10.0.2.2 is Android emulator's alias for host loopback.
        // For physical devices, override via --dart-define=VERICALL_API_BASE_URL
        return 'http://10.0.2.2:5000/api';
      case TargetPlatform.iOS:
        return 'http://localhost:5000/api';
      default:
        return 'http://localhost:5000/api';
    }
  }

  String _extractError(http.Response response, String fallback) {
    try {
      final data = jsonDecode(response.body);
      if (data is Map<String, dynamic>) {
        final error = data['error']?.toString();
        final action = data['action']?.toString();
        if (error != null && action != null) {
          return '$error $action';
        }
        if (error != null) {
          return error;
        }
      }
    } catch (_) {
      // no-op, use fallback
    }
    return '$fallback: ${response.body}';
  }

  /// Analyze text transcript for scam patterns
  Future<Map<String, dynamic>> analyzeText(String transcript) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze/text'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'transcript': transcript, 'deepfake_score': 0.5}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to analyze: ${response.body}');
    }
  }

  /// 🛡️ Complete 5-Layer Defense Analysis
  ///
  /// Analyzes call with all 5 defense layers:
  /// - Layer 1: Audio Deepfake Detection (if audio provided)
  /// - Layer 2: Scam Content Analysis
  /// - Layer 3: Caller Verification
  /// - Layer 4: Behavioral Analysis
  /// - Layer 5: Voice Cloning Protection
  Future<Map<String, dynamic>> analyzeComplete({
    required String transcript,
    String? callerNumber,
    String? claimedIdentity,
    String? claimedOrganization,
    double callDuration = 30,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze/complete'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'transcript': transcript,
        'caller_number': callerNumber ?? '+60123456789',
        'claimed_identity': claimedIdentity,
        'claimed_organization': claimedOrganization,
        'call_duration': callDuration,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to analyze: ${response.body}');
    }
  }

  /// Run full hybrid pipeline analysis (with audio)
  Future<Map<String, dynamic>> analyzePipeline(
    String audioPath,
    String? transcript,
  ) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/analyze/pipeline'),
    );

    request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

    if (transcript != null && transcript.trim().isNotEmpty) {
      request.fields['transcript'] = transcript.trim();
    }

    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception(
        _extractError(response, 'Failed to analyze audio pipeline'));
  }

  /// Answer demo call with first-answer ownership lock.
  Future<Map<String, dynamic>> answerDemoCall({
    required String sessionId,
    required String device,
    required String clientId,
    String? answeredByLabel,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/call/demo/answer'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'device': device,
        'client_id': clientId,
        'answered_by_label': answeredByLabel,
      }),
    );

    if (response.statusCode == 200 || response.statusCode == 409) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(_extractError(response, 'Failed to answer demo call'));
  }

  /// End demo call; owner/system only when connected.
  Future<Map<String, dynamic>> endDemoCall({
    required String sessionId,
    required String endedBy,
    required String device,
    required String clientId,
    List<String>? reasonCodes,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/call/demo/end'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'ended_by': endedBy,
        'device': device,
        'client_id': clientId,
        'reason_codes': reasonCodes ?? <String>[],
      }),
    );

    if (response.statusCode == 200 || response.statusCode == 403) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(_extractError(response, 'Failed to end demo call'));
  }

  /// Real-time scam verification using Gemini Grounding with Google Search.
  /// Searches Google to fact-check the caller's specific claims.
  Future<Map<String, dynamic>> groundTranscript(
    String transcript, {
    String? claimedOrg,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze/ground'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'transcript': transcript,
        if (claimedOrg != null) 'claimed_org': claimedOrg,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to verify caller claims'));
  }

  /// Deep analysis using Gemini extended thinking for ambiguous cases.
  Future<Map<String, dynamic>> analyzeWithThinking(
    String transcript, {
    double deepfakeScore = 0.0,
    List<String>? artifacts,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze/think'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'transcript': transcript,
        'deepfake_score': deepfakeScore,
        if (artifacts != null) 'artifacts': artifacts,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to run thinking analysis'));
  }

  /// Extract scam pattern from a report for self-learning database.
  Future<Map<String, dynamic>> extractPattern(
    String transcript, {
    Map<String, dynamic>? audioAnalysis,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/analyze/extract-pattern'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'transcript': transcript,
        if (audioAnalysis != null) 'audio_analysis': audioAnalysis,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to extract scam pattern'));
  }

  /// Fetch latest scam intelligence via Gemini Grounding.
  Future<Map<String, dynamic>> getDailyIntelligence({
    String region = 'Malaysia',
  }) async {
    final uri = Uri.parse('$baseUrl/intelligence/daily')
        .replace(queryParameters: {'region': region});
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to fetch daily intelligence'));
  }

  /// Get latest scam intelligence
  Future<Map<String, dynamic>> getIntelligence({String? type}) async {
    final uri = Uri.parse(
      '$baseUrl/intelligence',
    ).replace(queryParameters: type != null ? {'type': type} : null);

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to get intelligence: ${response.body}');
    }
  }

  /// Send family alert
  Future<Map<String, dynamic>> sendFamilyAlert({
    required String protectedUserId,
    required String scamType,
    required String riskLevel,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/family/alert'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'protected_user_id': protectedUserId,
        'scam_type': scamType,
        'risk_level': riskLevel,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(_extractError(response, 'Failed to send alert'));
    }
  }

  /// Generate one-time family link code
  Future<Map<String, dynamic>> generateFamilyLinkCode({
    required String victimId,
    String? victimName,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/family/link/code'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'victim_id': victimId,
        'victim_name': victimName,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(
          _extractError(response, 'Failed to generate family link code'));
    }
  }

  /// Consume one-time family link code
  Future<Map<String, dynamic>> consumeFamilyLinkCode({
    required String code,
    required String guardianId,
    String? guardianName,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/family/link/consume'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'code': code,
        'guardian_id': guardianId,
        'guardian_name': guardianName,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(
          _extractError(response, 'Failed to consume family link code'));
    }
  }

  /// Get linked family members for a user
  Future<List<Map<String, dynamic>>> getFamilyMembers(String userId) async {
    final response = await http.get(Uri.parse('$baseUrl/family/$userId'));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final members = (data['family_members'] as List<dynamic>? ?? []);
      return members.map((e) => Map<String, dynamic>.from(e)).toList();
    } else {
      throw Exception(_extractError(response, 'Failed to get family members'));
    }
  }

  /// Report a scam
  Future<Map<String, dynamic>> reportScam(Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('$baseUrl/reports'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(_extractError(response, 'Failed to report scam'));
    }
  }

  /// Get community scam reports
  Future<Map<String, dynamic>> getScamReports({
    String? type,
    int? limit,
  }) async {
    final queryParams = <String, String>{};
    if (type != null) queryParams['type'] = type;
    if (limit != null) queryParams['limit'] = limit.toString();

    final uri = Uri.parse(
      '$baseUrl/reports',
    ).replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception(_extractError(response, 'Failed to get reports'));
    }
  }

  /// Get aggregated scam statistics
  Future<Map<String, dynamic>> getScamStats() async {
    final response = await http.get(Uri.parse('$baseUrl/reports/stats'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception(_extractError(response, 'Failed to get scam stats'));
    }
  }

  /// Submit scam report and linked evidence in one flow
  Future<Map<String, dynamic>> submitReportAndEvidence({
    required String userId,
    required String scamType,
    required String phoneNumber,
    String? transcript,
    double? deepfakeScore,
    String? callerNumber,
    String? claimedOrganization,
    String? classificationReason,
    List<String>? detectedSignals,
    List<String>? moneyRequestEvidence,
    String? audioPath,
  }) async {
    final reportPayload = <String, dynamic>{
      'user_id': userId,
      'scam_type': scamType,
      'phone_number': phoneNumber,
      'transcript': transcript ?? '',
      'deepfake_score': deepfakeScore ?? 0.0,
      if (callerNumber != null && callerNumber.isNotEmpty)
        'caller_number': callerNumber,
      if (claimedOrganization != null && claimedOrganization.isNotEmpty)
        'claimed_organization': claimedOrganization,
      if (classificationReason != null && classificationReason.isNotEmpty)
        'classification_reason': classificationReason,
      if (detectedSignals != null) 'detected_signals': detectedSignals,
      if (moneyRequestEvidence != null)
        'money_request_evidence': moneyRequestEvidence,
    };

    final reportResult = await reportScam(reportPayload);
    final reportId = reportResult['report_id']?.toString();
    if (reportId == null || reportId.isEmpty) {
      throw Exception('Report submitted but report_id missing from response');
    }

    final evidencePayload = <String, dynamic>{
      'report_id': reportId,
      'transcript': transcript ?? '',
      'quality_score':
          transcript == null || transcript.trim().isEmpty ? 20 : 85,
      'keywords_detected': detectedSignals ?? <String>[],
      'classification_reason': classificationReason ?? '',
      'money_request_evidence': moneyRequestEvidence ?? <String>[],
      if (audioPath != null && audioPath.isNotEmpty) 'audio_path': audioPath,
    };

    final evidenceResponse = await http.post(
      Uri.parse('$baseUrl/evidence'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(evidencePayload),
    );

    if (evidenceResponse.statusCode != 200) {
      throw Exception(
        _extractError(evidenceResponse, 'Report saved but evidence failed'),
      );
    }

    final evidenceResult = jsonDecode(evidenceResponse.body);
    return {
      'report': reportResult,
      'evidence': evidenceResult,
      'report_id': reportId,
    };
  }

  /// Fetch alerts for a user
  Future<List<Map<String, dynamic>>> getAlerts(
    String userId, {
    int limit = 20,
  }) async {
    final uri = Uri.parse(
      '$baseUrl/alerts',
    ).replace(queryParameters: {'user_id': userId, 'limit': '$limit'});

    final response = await http.get(uri);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final alerts = (data['alerts'] as List<dynamic>? ?? <dynamic>[]);
      return alerts.map((e) => Map<String, dynamic>.from(e)).toList();
    }

    throw Exception(_extractError(response, 'Failed to get alerts'));
  }

  /// Upsert user profile
  Future<Map<String, dynamic>> upsertUserProfile({
    required String userId,
    String? name,
    String? phone,
    bool? isProtected,
    String? fcmToken,
  }) async {
    final payload = <String, dynamic>{
      'user_id': userId,
      if (name != null) 'name': name,
      if (phone != null) 'phone': phone,
      if (isProtected != null) 'is_protected': isProtected,
      if (fcmToken != null) 'fcm_token': fcmToken,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/users'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception(_extractError(response, 'Failed to save user profile'));
  }

  /// Get user profile
  Future<Map<String, dynamic>> getUserProfile(String userId) async {
    final response = await http.get(Uri.parse('$baseUrl/users/$userId'));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception(_extractError(response, 'Failed to load user profile'));
  }

  /// Update FCM token
  Future<Map<String, dynamic>> updateFcmToken({
    required String userId,
    required String fcmToken,
  }) async {
    final response = await http.put(
      Uri.parse('$baseUrl/users/$userId/fcm'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'fcm_token': fcmToken}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception(_extractError(response, 'Failed to update FCM token'));
  }

  /// Check API health
  Future<bool> healthCheck() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/status'));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  // ── Scam Vaccine (Training Mode) ──

  /// Start a vaccine training session (AI simulates a scammer).
  /// Optionally pass [scamType] to select a specific scenario
  /// (e.g. "lhdn", "police", "bank", "parcel").
  Future<Map<String, dynamic>> startVaccineSession({String? scamType}) async {
    final response = await http.post(
      Uri.parse('$baseUrl/vaccine/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        if (scamType != null) 'scam_type': scamType,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to start training session'));
  }

  /// Send user response in vaccine training session.
  Future<Map<String, dynamic>> vaccineRespond({
    required String sessionId,
    required String userResponse,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/vaccine/respond'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'session_id': sessionId,
        'user_response': userResponse,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to get training response'));
  }

  /// End vaccine training session and get results.
  Future<Map<String, dynamic>> endVaccineSession(String sessionId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/vaccine/end'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'session_id': sessionId}),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception(
        _extractError(response, 'Failed to end training session'));
  }
}
