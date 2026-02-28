import 'dart:async';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'firebase_options.dart';
import 'screens/active_call_screen.dart';
import 'screens/alerts_screen.dart';
import 'screens/call_report_screen.dart';
import 'screens/call_screen.dart';
import 'screens/family_link_screen.dart';
import 'screens/home_screen.dart';
import 'screens/incoming_call_screen.dart';
import 'screens/intelligence_screen.dart';
import 'screens/scam_vaccine_screen.dart';
import 'screens/settings_screen.dart';
import 'services/api_service.dart';
import 'services/audio_service.dart';
import 'services/webrtc_service.dart';

Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  runApp(const VeriCallApp());
}

class VeriCallApp extends StatelessWidget {
  const VeriCallApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => ApiService()),
        Provider<AudioService>(create: (_) => AudioService()),
      ],
      child: MaterialApp(
        title: 'VeriCall Malaysia',
        debugShowCheckedModeBanner: false,
        theme: _buildTheme(),
        home: const MainNavigation(),
        routes: {
          '/home': (context) => const HomeScreen(),
          '/call': (context) => const CallScreen(),
          '/alerts': (context) => const AlertsScreen(),
          '/settings': (context) => const SettingsScreen(),
          '/family_link': (context) => const FamilyLinkScreen(),
          '/intelligence': (context) => const IntelligenceScreen(),
          '/scam_vaccine': (context) => const ScamVaccineScreen(),
        },
      ),
    );
  }

  ThemeData _buildTheme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF0066FF),
        brightness: Brightness.light,
        primary: const Color(0xFF0066FF),
        secondary: const Color(0xFF00D4AA),
        error: const Color(0xFFFF4444),
        surface: Colors.white,
      ),
      textTheme: GoogleFonts.poppinsTextTheme(),
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.black87,
        titleTextStyle: GoogleFonts.poppins(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: Colors.black87,
        ),
      ),
      cardTheme: const CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(16))),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}

/// Main navigation with bottom nav bar AND Firestore call listener
class MainNavigation extends StatefulWidget {
  const MainNavigation({super.key});

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _currentIndex = 0;
  bool _showingIncomingCall = false;
  bool _showingActiveCall = false;
  bool _showingCallReport = false;
  String _callerName = 'Unknown Caller';
  String _callerNumber = '+60 XX-XXXX XXXX';
  String _currentSessionId = '';
  String? _ownerDevice;
  String? _ownerClientId;
  // Report screen data (captured on call end)
  int _reportScamProbability = 0;
  Map<String, dynamic>? _reportThreatSummary;
  List<Map<String, dynamic>> _reportTranscript = [];
  List<Map<String, dynamic>> _reportEvents = [];
  String? _reportEndedBy;
  String? _reportEndedAtIso;
  String? _reportStartTimeIso;
  StreamSubscription<RemoteMessage>? _fcmForegroundSub;
  StreamSubscription<RemoteMessage>? _fcmOpenedSub;
  StreamSubscription<String>? _fcmTokenRefreshSub;

  final List<Widget> _screens = const [
    HomeScreen(),
    CallScreen(),
    AlertsScreen(),
    SettingsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _listenForDemoCall();
    _setupIncomingCallPush();
  }

  Future<void> _setupIncomingCallPush() async {
    final messaging = FirebaseMessaging.instance;
    try {
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      final auth = FirebaseAuth.instance;
      if (auth.currentUser == null) {
        await auth.signInAnonymously();
      }

      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _registerDemoVictimToken(token);
      }

      _fcmTokenRefreshSub = messaging.onTokenRefresh.listen((token) {
        _registerDemoVictimToken(token);
      });

      _fcmForegroundSub =
          FirebaseMessaging.onMessage.listen(_handleIncomingCallPush);
      _fcmOpenedSub =
          FirebaseMessaging.onMessageOpenedApp.listen(_handleIncomingCallPush);

      final initial = await messaging.getInitialMessage();
      if (initial != null) {
        _handleIncomingCallPush(initial);
      }
    } catch (e) {
      debugPrint('FCM setup failed: $e');
    }
  }

  Future<String> _resolveMobileClientId() async {
    final auth = FirebaseAuth.instance;
    if (auth.currentUser == null) {
      await auth.signInAnonymously();
    }
    return auth.currentUser?.uid ?? 'mobile_demo';
  }

  Future<void> _registerDemoVictimToken(String token) async {
    try {
      await ApiService().upsertUserProfile(
        userId: 'demo_victim',
        name: 'Demo Victim',
        isProtected: true,
        fcmToken: token,
      );
    } catch (e) {
      debugPrint('Failed to register demo victim token: $e');
    }
  }

  void _handleIncomingCallPush(RemoteMessage message) {
    final data = message.data;
    if ((data['type'] ?? '').toString() != 'incoming_demo_call') {
      return;
    }

    final callerName = (data['caller_name'] ?? 'Unknown Caller').toString();
    final callerNumber =
        (data['caller_number'] ?? '+60 XX-XXXX XXXX').toString();
    final sessionId = (data['session_id'] ?? '').toString();

    if (!mounted) return;
    setState(() {
      _callerName = callerName;
      _callerNumber = callerNumber;
      if (sessionId.isNotEmpty) {
        _currentSessionId = sessionId;
      }
      _showingIncomingCall = true;
      _showingActiveCall = false;
    });
  }

  /// 🔥 Firestore listener for real-time demo calls from web admin
  /// Latency: < 100ms - bulletproof!
  void _listenForDemoCall() {
    FirebaseFirestore.instance
        .collection('calls')
        .doc('current_demo')
        .snapshots()
        .listen((snapshot) {
      if (!snapshot.exists) return;

      final data = snapshot.data()!;
      final state = data['state'] as String?;

      print('📞 Call state changed: $state');

      setState(() {
        _callerName = data['callerName'] ?? 'Unknown Caller';
        _callerNumber = data['callerNumber'] ?? '+60 XX-XXXX XXXX';
        _currentSessionId = (data['sessionId'] ?? _currentSessionId).toString();
        _ownerDevice = (data['ownerDevice'] ?? '').toString().isEmpty
            ? null
            : (data['ownerDevice'] ?? '').toString();
        _ownerClientId = (data['ownerClientId'] ?? '').toString().isEmpty
            ? null
            : (data['ownerClientId'] ?? '').toString();
      });

      switch (state) {
        case 'ringing':
          // Show incoming call screen
          if (!_showingIncomingCall && !_showingActiveCall) {
            setState(() => _showingIncomingCall = true);
          }
          break;
        case 'connected':
          // Show active call screen
          setState(() {
            _showingIncomingCall = false;
            _showingActiveCall = true;
          });
          break;
        case 'ended':
          // Clean up WebRTC audio bridge
          WebRTCService.instance.hangUp().catchError((e) {
            debugPrint('WebRTC cleanup on call end: $e');
          });
          // Capture report data from Firestore BEFORE hiding call screen
          _reportScamProbability =
              (data['scamProbability'] as num?)?.toInt() ?? 0;
          final ts = data['threatSummary'];
          _reportThreatSummary =
              ts is Map ? Map<String, dynamic>.from(ts) : null;
          final tr = data['transcript'];
          _reportTranscript = tr is List
              ? tr
                  .whereType<Map>()
                  .map((e) => Map<String, dynamic>.from(e))
                  .toList()
              : [];
          final ev = data['events'];
          _reportEvents = ev is List
              ? ev
                  .whereType<Map>()
                  .map((e) => Map<String, dynamic>.from(e))
                  .toList()
              : [];
          _reportEndedBy = (data['endedBy'] ?? '').toString();
          _reportEndedAtIso = (data['endedAtIso'] ?? '').toString();
          _reportStartTimeIso = (data['startTimeIso'] ?? '').toString();
          // Show report screen instead of silently returning to home
          setState(() {
            _showingIncomingCall = false;
            _showingActiveCall = false;
            _showingCallReport = true;
          });
          break;
        case 'idle':
          // Clean up WebRTC audio bridge
          WebRTCService.instance.hangUp().catchError((e) {
            debugPrint('WebRTC cleanup on idle: $e');
          });
          // Hide all call screens (idle = no report needed)
          setState(() {
            _showingIncomingCall = false;
            _showingActiveCall = false;
          });
          break;
      }
    });
  }

  void _answerCall() async {
    if (_currentSessionId.isEmpty) return;
    try {
      final clientId = await _resolveMobileClientId();
      final result = await ApiService().answerDemoCall(
        sessionId: _currentSessionId,
        device: 'mobile',
        clientId: clientId,
        answeredByLabel: 'Mobile Victim App',
      );
      if ((result['accepted'] ?? false) == true) {
        // Clear stale transcript/analysis data from previous sessions
        FirebaseFirestore.instance
            .collection('calls')
            .doc('current_demo')
            .update({
          'transcript': [],
          'scamProbability': 0,
          'threatSummary': null,
          'events': [],
        }).catchError((e) {
          debugPrint('Failed to clear stale call data: $e');
        });
        // Start WebRTC audio bridge after successful answer
        WebRTCService.instance.answerCall().catchError((e) {
          debugPrint('WebRTC audio bridge failed (call works without it): $e');
        });
      } else if ((result['reason'] ?? '').toString() == 'already_answered') {
        if (mounted) {
          setState(() {
            _showingIncomingCall = false;
          });
        }
      }
    } catch (e) {
      debugPrint('Answer call failed: $e');
    }
  }

  void _declineCall() async {
    if (_currentSessionId.isEmpty) return;
    // Clean up WebRTC if active
    WebRTCService.instance.hangUp().catchError((e) {
      debugPrint('WebRTC cleanup on decline: $e');
    });
    try {
      final clientId = await _resolveMobileClientId();
      await ApiService().endDemoCall(
        sessionId: _currentSessionId,
        endedBy: 'mobile_client',
        device: 'mobile',
        clientId: clientId,
        reasonCodes: const ['declined_by_mobile'],
      );
    } catch (e) {
      debugPrint('Decline call failed: $e');
    }
  }

  void _hangUpCall() async {
    if (_currentSessionId.isEmpty) return;
    // Clean up WebRTC audio bridge
    WebRTCService.instance.hangUp().catchError((e) {
      debugPrint('WebRTC cleanup on hangup: $e');
    });
    try {
      final clientId = await _resolveMobileClientId();
      await ApiService().endDemoCall(
        sessionId: _currentSessionId,
        endedBy: 'mobile_client',
        device: 'mobile',
        clientId: clientId,
        reasonCodes: const ['hangup_by_mobile'],
      );
    } catch (e) {
      debugPrint('Hang up call failed: $e');
    }
  }

  @override
  void dispose() {
    _fcmForegroundSub?.cancel();
    _fcmOpenedSub?.cancel();
    _fcmTokenRefreshSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Show incoming call screen over everything
    if (_showingIncomingCall) {
      return IncomingCallScreen(
        callerName: _callerName,
        callerNumber: _callerNumber,
        onAnswer: _answerCall,
        onDecline: _declineCall,
      );
    }

    // Show call report screen after call ends
    if (_showingCallReport) {
      return CallReportScreen(
        sessionId: _currentSessionId,
        callerName: _callerName,
        callerNumber: _callerNumber,
        scamProbability: _reportScamProbability,
        threatSummary: _reportThreatSummary,
        transcript: _reportTranscript,
        events: _reportEvents,
        endedBy: _reportEndedBy,
        endedAtIso: _reportEndedAtIso,
        startTimeIso: _reportStartTimeIso,
        onDismiss: () {
          setState(() => _showingCallReport = false);
        },
      );
    }

    // Show active call screen over everything
    if (_showingActiveCall) {
      final currentUid = FirebaseAuth.instance.currentUser?.uid;
      final isOwner = _ownerDevice == 'mobile' &&
          _ownerClientId != null &&
          currentUid != null &&
          _ownerClientId == currentUid;
      return ActiveCallScreen(
        callerName: _callerName,
        callerNumber: _callerNumber,
        sessionId: _currentSessionId,
        isOwner: isOwner,
        ownerDevice: _ownerDevice,
        onHangUp: _hangUpCall,
      );
    }

    // Normal app navigation
    return Scaffold(
      body: IndexedStack(index: _currentIndex, children: _screens),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 20,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() => _currentIndex = index);
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.shield_outlined),
              selectedIcon: Icon(Icons.shield),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.phone_outlined),
              selectedIcon: Icon(Icons.phone),
              label: 'Call',
            ),
            NavigationDestination(
              icon: Icon(Icons.notifications_outlined),
              selectedIcon: Icon(Icons.notifications),
              label: 'Alerts',
            ),
            NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
