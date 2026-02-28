import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

enum AudioServiceState {
  idle,
  recording,
  recorded,
  playing,
  error,
}

/// Audio Service for recording and processing
class AudioService {
  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _player = AudioPlayer();

  AudioServiceState _state = AudioServiceState.idle;
  String? _currentRecordingPath;
  String? _lastError;

  AudioServiceState get state => _state;
  bool get isRecording => _state == AudioServiceState.recording;
  bool get isPlaying => _state == AudioServiceState.playing;
  String? get currentRecordingPath => _currentRecordingPath;
  String? get lastError => _lastError;
  Stream<void> get onPlaybackComplete => _player.onPlayerComplete;

  AudioService() {
    _player.onPlayerComplete.listen((_) {
      _state = _currentRecordingPath == null
          ? AudioServiceState.idle
          : AudioServiceState.recorded;
    });
  }

  void _setError(String message) {
    _lastError = message;
    _state = AudioServiceState.error;
  }

  /// Start recording audio
  Future<void> startRecording() async {
    try {
      _lastError = null;

      final granted = await requestPermission();
      if (!granted) {
        _setError('Microphone permission denied');
        return;
      }

      if (await _recorder.isRecording()) {
        await _recorder.stop();
      }

      final filename =
          'vericall_${DateTime.now().millisecondsSinceEpoch}.wav';
      final path =
          '${Directory.systemTemp.path}${Platform.pathSeparator}$filename';

      await _recorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
          bitRate: 128000,
        ),
        path: path,
      );

      _currentRecordingPath = path;
      _state = AudioServiceState.recording;
    } catch (e) {
      _setError('Failed to start recording: $e');
    }
  }

  /// Stop recording and return path to audio file
  Future<String?> stopRecording() async {
    try {
      if (!await _recorder.isRecording()) {
        return _currentRecordingPath;
      }

      final path = await _recorder.stop();
      if (path == null || path.isEmpty) {
        _setError('Recording did not produce an audio file');
        return null;
      }

      _currentRecordingPath = path;
      _state = AudioServiceState.recorded;
      return _currentRecordingPath;
    } catch (e) {
      _setError('Failed to stop recording: $e');
      return null;
    }
  }

  /// Play audio from path
  Future<void> playAudio(String path) async {
    try {
      _lastError = null;

      if (!File(path).existsSync()) {
        _setError('Audio file not found');
        return;
      }

      await _player.stop();
      _state = AudioServiceState.playing;
      await _player.play(DeviceFileSource(path));
      _currentRecordingPath = path;
    } catch (e) {
      _setError('Failed to play audio: $e');
    }
  }

  /// Stop audio playback
  Future<void> stopAudio() async {
    try {
      await _player.stop();
      _state = _currentRecordingPath == null
          ? AudioServiceState.idle
          : AudioServiceState.recorded;
    } catch (e) {
      _setError('Failed to stop playback: $e');
    }
  }

  /// Request microphone permission
  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    return status.isGranted;
  }

  /// Check if microphone permission is granted
  Future<bool> hasPermission() async {
    return Permission.microphone.isGranted;
  }

  /// Dispose resources
  Future<void> dispose() async {
    await _player.dispose();
    await _recorder.dispose();
  }
}
