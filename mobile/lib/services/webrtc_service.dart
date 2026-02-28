/// WebRTC Audio Bridge Service (Flutter / answerer side)
///
/// Reads the SDP offer from Firestore (written by web app),
/// creates an SDP answer, exchanges ICE candidates, and
/// establishes a peer-to-peer audio connection.
///
/// Usage:
///   await WebRTCService.instance.answerCall();   // after backend answer accepted
///   await WebRTCService.instance.hangUp();        // on call end

import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';

class WebRTCService {
  WebRTCService._();
  static final WebRTCService instance = WebRTCService._();

  // ─── Configuration ─────────────────────────────────────────────────────────

  static const _iceServers = <Map<String, dynamic>>[
    {'urls': 'stun:stun.l.google.com:19302'},
    {'urls': 'stun:stun1.l.google.com:19302'},
  ];

  static const _callDocPath = 'calls/current_demo';

  // ─── State ─────────────────────────────────────────────────────────────────

  RTCPeerConnection? _peerConnection;
  MediaStream? _localStream;
  MediaStream? _remoteStream;

  final List<StreamSubscription> _subscriptions = [];
  bool _isActive = false;

  /// Notifies listeners when remote audio stream is ready
  final ValueNotifier<bool> isConnected = ValueNotifier(false);

  // ─── Public API ────────────────────────────────────────────────────────────

  /// Answer a WebRTC call by reading the SDP offer from Firestore,
  /// creating an answer, and exchanging ICE candidates.
  Future<void> answerCall() async {
    if (_isActive) {
      debugPrint('📡 WebRTC: Already active, skipping answerCall');
      return;
    }
    _isActive = true;
    debugPrint('📡 WebRTC: Answering call as callee...');

    try {
      final firestore = FirebaseFirestore.instance;
      final callDoc = firestore.doc(_callDocPath);

      // 1. Read the SDP offer from Firestore
      final snapshot = await callDoc.get();
      final data = snapshot.data();
      if (data == null || data['webRtcOffer'] == null) {
        debugPrint('📡 WebRTC: No SDP offer found in Firestore');
        _isActive = false;
        return;
      }

      final offerData = data['webRtcOffer'] as Map<String, dynamic>;
      final offer = RTCSessionDescription(
        offerData['sdp'] as String,
        offerData['type'] as String,
      );

      // 2. Capture local microphone
      _localStream = await navigator.mediaDevices.getUserMedia({
        'audio': true,
        'video': false,
      });
      debugPrint('🎤 WebRTC: Microphone captured');

      // 3. Create peer connection
      _peerConnection = await createPeerConnection({
        'iceServers': _iceServers,
      });

      // 4. Add local audio tracks
      _localStream!.getAudioTracks().forEach((track) {
        _peerConnection!.addTrack(track, _localStream!);
      });

      // 5. Handle remote stream (audio from web app)
      _peerConnection!.onTrack = (RTCTrackEvent event) {
        debugPrint('🔊 WebRTC: Remote track received: ${event.track.kind}');
        if (event.streams.isNotEmpty) {
          _remoteStream = event.streams[0];
          isConnected.value = true;
          debugPrint('📡 WebRTC: Audio connected!');
        }
      };

      // 6. Connection state monitoring
      _peerConnection!.onConnectionState = (RTCPeerConnectionState state) {
        debugPrint('📡 WebRTC: Connection state → $state');
        if (state == RTCPeerConnectionState.RTCPeerConnectionStateConnected) {
          isConnected.value = true;
        } else if (state ==
                RTCPeerConnectionState.RTCPeerConnectionStateDisconnected ||
            state == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
            state == RTCPeerConnectionState.RTCPeerConnectionStateClosed) {
          isConnected.value = false;
        }
      };

      // 7. Write ICE candidates to Firestore
      final mobileIceCollection = callDoc.collection('ice_mobile');
      _peerConnection!.onIceCandidate = (RTCIceCandidate candidate) {
        mobileIceCollection.add({
          'candidate': candidate.candidate,
          'sdpMid': candidate.sdpMid,
          'sdpMLineIndex': candidate.sdpMLineIndex,
        }).catchError((e) {
          debugPrint('WebRTC: Failed to write ICE candidate: $e');
        });
      };

      // 8. Set remote description (the offer) and create answer
      await _peerConnection!.setRemoteDescription(offer);
      final answer = await _peerConnection!.createAnswer();
      await _peerConnection!.setLocalDescription(answer);
      debugPrint('📡 WebRTC: SDP answer created');

      // 9. Write answer to Firestore
      await callDoc.update({
        'webRtcAnswer': {
          'type': answer.type,
          'sdp': answer.sdp,
        },
      });
      debugPrint('📡 WebRTC: Answer written to Firestore');

      // 10. Listen for ICE candidates from web
      final webIceCollection = callDoc.collection('ice_web');
      final iceSub = webIceCollection.snapshots().listen((snapshot) {
        for (final change in snapshot.docChanges) {
          if (change.type == DocumentChangeType.added) {
            final candidateData = change.doc.data();
            if (candidateData != null) {
              final candidate = RTCIceCandidate(
                candidateData['candidate'] as String?,
                candidateData['sdpMid'] as String?,
                candidateData['sdpMLineIndex'] as int?,
              );
              _peerConnection?.addCandidate(candidate).catchError((e) {
                debugPrint('WebRTC: Failed to add remote ICE: $e');
              });
            }
          }
        }
      });
      _subscriptions.add(iceSub);

      debugPrint('📡 WebRTC: Signaling active, exchanging ICE candidates...');
    } catch (e) {
      debugPrint('📡 WebRTC: Answer failed: $e');
      _isActive = false;
      await hangUp();
    }
  }

  /// Hang up: close peer connection and clean up resources.
  Future<void> hangUp() async {
    debugPrint('📡 WebRTC: Hanging up...');

    // Cancel subscriptions
    for (final sub in _subscriptions) {
      sub.cancel();
    }
    _subscriptions.clear();

    // Close peer connection
    if (_peerConnection != null) {
      await _peerConnection!.close();
      _peerConnection = null;
    }

    // Stop local media
    if (_localStream != null) {
      _localStream!.getTracks().forEach((track) => track.stop());
      await _localStream!.dispose();
      _localStream = null;
    }

    // Remote stream cleanup
    _remoteStream = null;
    _isActive = false;
    isConnected.value = false;

    // Clean up Firestore signaling data (best-effort)
    try {
      final firestore = FirebaseFirestore.instance;
      final callDoc = firestore.doc(_callDocPath);
      await callDoc.update({
        'webRtcOffer': FieldValue.delete(),
        'webRtcAnswer': FieldValue.delete(),
      });
      // Delete ICE candidate documents
      await _deleteSubcollection(callDoc.collection('ice_web'));
      await _deleteSubcollection(callDoc.collection('ice_mobile'));
    } catch (e) {
      debugPrint('WebRTC: Firestore cleanup error (non-fatal): $e');
    }

    debugPrint('📡 WebRTC: Cleanup complete');
  }

  /// Whether WebRTC is currently active
  bool get isActive => _isActive;

  // ─── Helpers ───────────────────────────────────────────────────────────────

  Future<void> _deleteSubcollection(CollectionReference collection) async {
    try {
      final snapshot = await collection.get();
      for (final doc in snapshot.docs) {
        await doc.reference.delete();
      }
    } catch (e) {
      // Non-fatal
    }
  }
}
