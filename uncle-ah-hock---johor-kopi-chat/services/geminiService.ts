/**
 * Gemini Service - Main Connection Module
 * Handles Gemini Live voice interaction for Uncle Ah Hock AI Defense System
 */

import { FunctionDeclaration, GoogleGenAI, LiveServerMessage, Modality, Type } from '@google/genai';
import { base64ToUint8Array, createPcmBlob, decodeAudioData } from '../utils/audioUtils';

// Import modular components
import { ApiKeyManager } from './apiKeyManager';
import { BotDetector } from './botDetector';
import { ContactVerifier, VerificationResult } from './contactVerifier';
import { EvidenceCollector } from './evidenceCollector';
import { autoReportAndSaveEvidence } from './firebaseService';
import { PDRMSubmit, SubmissionStatus } from './pdrmSubmit';
import { ScamAnalyzer } from './scamAnalyzer';
import { ScamIntelligence, ScamSearchResult } from './scamIntelligence';
import {
  BotDetectionStatus,
  ConnectionState,
  LogMessage,
  PHONETICS,
  ScamEvidence,
  ThreatAssessment
} from './types/scamTypes';

// Re-export types for backward compatibility
export type { VerificationResult } from './contactVerifier';
export type { SubmissionStatus } from './pdrmSubmit';
export type { ScamSearchResult } from './scamIntelligence';
export { ConnectionState } from './types/scamTypes';
export type { BotDetectionStatus, LogMessage, ScamEvidence, ThreatAssessment } from './types/scamTypes';

// --- Configuration ---
const LIVE_MODEL = 'gemini-2.5-flash-native-audio-preview-12-2025';
// Changed from gemini-3-pro-preview (rate limited) to gemini-2.0-flash (more quota)
const TEXT_MODEL = 'gemini-2.5-flash';

// Backend URL for WavLM analysis
const backendEnv = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:5000';
const BACKEND_URL = backendEnv.endsWith('/api') ? backendEnv.slice(0, -4) : backendEnv;
const THREAT_ENGINE_V2_PRIMARY = (import.meta.env.VITE_THREAT_ENGINE_V2_PRIMARY ?? 'true') === 'true';
const THREAT_ENGINE_V2_SHADOW = (import.meta.env.VITE_THREAT_ENGINE_V2_SHADOW ?? 'true') === 'true';
const AUTO_HANGUP_ENABLED = (import.meta.env.VITE_AUTO_HANGUP_ENABLED ?? 'true') === 'true';
const CALL_AUDIO_RELAY_ENABLED = (import.meta.env.VITE_CALL_AUDIO_RELAY_ENABLED ?? 'false') === 'true';

function resolveCallAudioWsBaseUrl(): string {
  const explicit = (import.meta.env.VITE_CALL_AUDIO_WS_URL ?? '').trim();
  if (explicit) return explicit.replace(/\/$/, '');

  try {
    const base = new URL(BACKEND_URL);
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    base.port = String(import.meta.env.VITE_CALL_AUDIO_WS_PORT ?? '8765');
    base.pathname = '';
    base.search = '';
    base.hash = '';
    return base.toString().replace(/\/$/, '');
  } catch {
    return 'ws://127.0.0.1:8765';
  }
}

const CALL_AUDIO_WS_BASE_URL = resolveCallAudioWsBaseUrl();

const SILENCE_PROMPTS = [
  "The caller is silent. Give one short opener only: 'Hello? Who speaking ah?'",
  "The line is quiet. Ask briefly: 'Hello, you can hear me or not?'",
  "No response yet. Say one gentle line: 'Hello? Wrong number is it?'",
  "Caller is silent. Keep it short: 'Hello? You call me for what ah?'"
];

type CallAction = 'none' | 'warn' | 'challenge' | 'hangup';

// --- MAIN SERVICE ---

export class GeminiService {
  // Audio State
  private inputAudioContext: AudioContext | null = null;
  private outputAudioContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private inputSource: MediaStreamAudioSourceNode | null = null;
  private nextStartTime = 0;
  private sources = new Set<AudioBufferSourceNode>();
  private lastAudioReceivedAt = 0;
  private instructionAudioFallbackTimer: ReturnType<typeof setTimeout> | null = null;

  // Logic State - Using modular components
  private session: any = null;
  private botDetector: BotDetector;
  private evidenceCollector: EvidenceCollector;
  private scamAnalyzer: ScamAnalyzer;
  private contactVerifier: ContactVerifier;
  private scamIntelligence: ScamIntelligence;
  private pdrmSubmit: PDRMSubmit;
  private currentInputTranscript = '';
  private currentOutputTranscript = '';
  private learnedTactics: string[] = [];
  private botCheckInterval: ReturnType<typeof setInterval> | null = null;
  private apiKeyManager: ApiKeyManager;
  private connectionSucceeded: boolean = false;  // Track if connection was successful
  private sessionGenerationId = 0;
  private hasFirstAudioOutput = false;
  private hasRetriedFirstPrompt = false;
  private firstTurnFallbackTimer: ReturnType<typeof setTimeout> | null = null;

  // WavLM Integration State
  private audioBuffer: Float32Array[] = [];
  private wavlmAnalysisInterval: ReturnType<typeof setInterval> | null = null;
  private lastWavLMScore: number = 0;
  private backendConnected: boolean = false;
  private liveThreatSessionId: string = '';
  private pendingThreatDelta: string = '';
  private pendingThreatTimer: ReturnType<typeof setTimeout> | null = null;
  private threatRequestInFlight: boolean = false;
  private latestThreatAssessment: ThreatAssessment | null = null;
  private lastClaimedOrganization: string | null = null;
  private lastDeepfakeSnapshot: {
    score: number;
    confidence: number;
    is_deepfake: boolean;
    artifacts: string[];
    active_speech_ratio?: number;
    decision_reason?: string;
  } | null = null;
  private callSessionId: string = '';
  private callerLastSpeechAt: number = 0;
  private callAnsweredAt: number = 0;
  private challengePromptsSent: number = 0;
  private lastCallAction: CallAction = 'none';
  private lastCallActionAt: number = 0;
  private autoHangupInProgress: boolean = false;
  private audioRelaySocket: WebSocket | null = null;
  private audioRelaySeq: number = 0;

  // 🎙️ Call Audio Recording State (for PDRM evidence)
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private callRecordingBlob: Blob | null = null;
  private isRecording: boolean = false;

  // Callbacks
  public onConnectionStateChange: (state: ConnectionState) => void = () => { };
  public onVolumeChange: (volume: number) => void = () => { };
  public onTranscript: (msg: LogMessage) => void = () => { };
  public onPartialTranscript: (text: string, isUser: boolean) => void = () => { };
  public onSearchResults: (results: SearchResult[]) => void = () => { };
  public onToolUse: (toolName: string, query: string, result: string) => void = () => { };
  public onTranslation: (lang: string, original: string, translated: string) => void = () => { };

  // Advanced callbacks
  public onBotDetected: (status: BotDetectionStatus) => void = () => { };
  public onEvidenceReady: (evidence: ScamEvidence) => void = () => { };
  public onScamPatternDetected: (pattern: string) => void = () => { };
  public onScamProbabilityChange: (prob: number) => void = () => { };
  public onTurnComplete: (isUser: boolean) => void = () => { };
  public onContactVerified: (result: VerificationResult) => void = () => { };
  public onScamSearchComplete: (results: ScamSearchResult[]) => void = () => { };
  public onSubmissionComplete: (status: SubmissionStatus) => void = () => { };
  public onApiKeyRotated: (currentIndex: number, totalKeys: number) => void = () => { };
  public onAllApiKeysExhausted: () => void = () => { };
  public onThreatAssessment: (assessment: ThreatAssessment) => void = () => { };
  public onCallAction: (event: {
    action: CallAction;
    reasonCodes: string[];
    confidence: number;
    hangupAfterMs: number | null;
  }) => void = () => { };

  // WavLM Callbacks
  public onWavLMResult: (result: {
    score: number;
    isDeepfake: boolean;
    artifacts: string[];
    confidence?: number;
    qualityScore?: number;
    activeSpeechRatio?: number;
    certainty?: string;
    decisionReason?: string;
  }) => void = () => { };
  public onBackendStatusChange: (connected: boolean) => void = () => { };

  // 🎙️ Audio Recording Callbacks
  public onCallRecordingReady: (audioBlob: Blob) => void = () => { };

  constructor() {
    // Initialize modular components
    this.botDetector = new BotDetector();
    this.evidenceCollector = new EvidenceCollector();
    this.scamAnalyzer = new ScamAnalyzer();
    this.contactVerifier = new ContactVerifier();
    this.scamIntelligence = new ScamIntelligence();
    this.pdrmSubmit = new PDRMSubmit();

    // Initialize API Key Manager
    this.apiKeyManager = new ApiKeyManager();
    this.apiKeyManager.loadFromEnv(); // Load keys from API_KEY env var (comma-separated)
    this.apiKeyManager.setOnKeyRotated((index, total) => {
      console.log(`🔑 Rotated to API key ${index}/${total}`);
      this.onApiKeyRotated(index, total);
    });
    this.apiKeyManager.setOnAllKeysExhausted(() => {
      console.error('❌ All API keys exhausted!');
      this.onAllApiKeysExhausted();
    });

    // Wire up component callbacks
    this.botDetector.onBotDetected = (status) => this.onBotDetected(status);
    this.scamAnalyzer.onScamProbabilityChange = (prob) => {
      if (!THREAT_ENGINE_V2_PRIMARY || !this.backendConnected) {
        this.onScamProbabilityChange(prob);
      }
    };
    this.scamAnalyzer.onScamPatternDetected = (pattern, urgency) => {
      this.onScamPatternDetected(pattern);
      console.log(`🚨 Scam Pattern: ${pattern} (${urgency})`);
    };
    this.scamAnalyzer.onCriticalThreatDetected = (pattern) => {
      // Auto-aggressive mode
      const instruction = this.scamAnalyzer.generateAlertInstruction(pattern);
      this.sendLiveInstruction(instruction);
    };
    // NEW: Inject tone changes when scam probability changes significantly
    this.scamAnalyzer.onToneLevelChange = (tone, reason) => {
      console.log(`🎭 Tone changed to: ${tone} - ${reason}`);
      const toneInstruction = this.scamAnalyzer.getToneInstruction();
      this.sendLiveInstruction(toneInstruction);
    };
    this.contactVerifier.onContactVerified = (result) => this.onContactVerified(result);
    this.scamIntelligence.onSearchComplete = (results) => this.onScamSearchComplete(results);
    this.pdrmSubmit.onSubmissionComplete = (status) => this.onSubmissionComplete(status);

    // Check backend status on startup
    this.checkBackendStatus();
  }

  // --- WavLM BACKEND INTEGRATION ---

  /**
   * Check if Python backend is available
   */
  private async checkBackendStatus(): Promise<boolean> {
    try {
      const response = await fetch(`${BACKEND_URL}/health`, { method: 'GET' });
      this.backendConnected = response.ok;
      this.onBackendStatusChange(this.backendConnected);
      console.log(`🔌 Backend status: ${this.backendConnected ? 'CONNECTED' : 'OFFLINE'}`);
      return this.backendConnected;
    } catch (e) {
      this.backendConnected = false;
      this.onBackendStatusChange(false);
      console.warn('⚠️ Backend not available - WavLM analysis disabled');
      return false;
    }
  }

  /**
   * Send audio buffer to backend for WavLM deepfake analysis
   */
  private async analyzeWithWavLM(): Promise<void> {
    if (!this.backendConnected || this.audioBuffer.length === 0) {
      console.log('🔬 WavLM: Skipping (backend:', this.backendConnected, 'buffer:', this.audioBuffer.length, ')');
      return;
    }

    try {
      // Merge audio chunks into single buffer (limit to ~7 seconds at 16kHz for better accuracy)
      const MAX_SAMPLES = 16000 * 7; // 7 seconds
      let totalLength = this.audioBuffer.reduce((sum, chunk) => sum + chunk.length, 0);

      console.log(`🔬 WavLM: Processing ${this.audioBuffer.length} chunks, ${totalLength} samples`);

      // Limit buffer size
      if (totalLength > MAX_SAMPLES) {
        totalLength = MAX_SAMPLES;
      }

      const mergedAudio = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of this.audioBuffer) {
        if (offset >= totalLength) break;
        const copyLength = Math.min(chunk.length, totalLength - offset);
        mergedAudio.set(chunk.slice(0, copyLength), offset);
        offset += copyLength;
      }

      // Clear buffer for next analysis window
      this.audioBuffer = [];

      // Skip analysis if audio is effectively silent (reduces false positives)
      let sumSq = 0;
      for (let i = 0; i < mergedAudio.length; i++) sumSq += mergedAudio[i] * mergedAudio[i];
      const rms = Math.sqrt(sumSq / Math.max(1, mergedAudio.length));
      if (!Number.isFinite(rms) || rms < 0.01) {
        console.log('🔬 WavLM: Skipping - low audio level (rms:', rms.toFixed(4), ')');
        return;
      }

      // Convert to base64 using chunked approach (avoid stack overflow)
      const bytes = new Uint8Array(mergedAudio.buffer);
      let base64Audio = '';
      const chunkSize = 8192;
      for (let i = 0; i < bytes.length; i += chunkSize) {
        const chunk = bytes.slice(i, i + chunkSize);
        base64Audio += String.fromCharCode.apply(null, chunk as any);
      }
      base64Audio = btoa(base64Audio);

      console.log(`🔬 WavLM: Sending ${base64Audio.length} bytes to backend...`);

      // Send to backend
      const response = await fetch(`${BACKEND_URL}/api/analyze/audio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio: base64Audio, sample_rate: 16000 })
      });

      console.log(`🔬 WavLM: Response status ${response.status}`);

      if (response.ok) {
        const result = await response.json();
        const score = typeof result.deepfake_score === 'number' ? result.deepfake_score : 0;
        const confidence = typeof result.confidence === 'number' ? result.confidence : 0;
        const artifacts = result.artifacts_detected || [];
        const isDeepfake = !!result.is_deepfake;
        const qualityScore = typeof result.quality_score === 'number' ? result.quality_score : 0;
        const activeSpeechRatio = typeof result.active_speech_ratio === 'number' ? result.active_speech_ratio : 0;
        const certainty = typeof result.certainty === 'string' ? result.certainty : 'unknown';
        const decisionReason = typeof result.decision_reason === 'string' ? result.decision_reason : '';

        this.lastWavLMScore = score;

        console.log(`WavLM RESULT:`, result);
        console.log(
          `WavLM: ${(score * 100).toFixed(0)}% deepfake (${(confidence * 100).toFixed(0)}% conf, speech ${(activeSpeechRatio * 100).toFixed(0)}%) ${isDeepfake ? 'ALERT' : 'OK'}`
        );

        this.onWavLMResult({
          score,
          isDeepfake,
          artifacts,
          confidence,
          qualityScore,
          activeSpeechRatio,
          certainty,
          decisionReason
        });
        this.lastDeepfakeSnapshot = {
          score,
          confidence,
          is_deepfake: isDeepfake,
          artifacts,
          active_speech_ratio: activeSpeechRatio,
          decision_reason: decisionReason
        };
        this.queueThreatLiveUpdate('');
      } else {
        const errorText = await response.text();
        console.error(`🔬 WavLM: Backend error ${response.status}:`, errorText);
      }
    } catch (e) {
      console.error('🔬 WavLM analysis failed:', e);
    }
  }

  /**
   * Start periodic WavLM analysis during calls
   */
  private startWavLMAnalysis() {
    if (!this.backendConnected) return;

    // Analyze every 7 seconds (collect audio for accuracy)
    this.wavlmAnalysisInterval = setInterval(() => {
      if (this.audioBuffer.length > 0) {
        this.analyzeWithWavLM();
      }
    }, 7000);

    console.log('🔬 WavLM periodic analysis started');
  }

  /**
   * Stop WavLM analysis
   */
  private stopWavLMAnalysis() {
    if (this.wavlmAnalysisInterval) {
      clearInterval(this.wavlmAnalysisInterval);
      this.wavlmAnalysisInterval = null;
    }
    this.audioBuffer = [];
  }

  // 🎙️ AUDIO RECORDING METHODS (for PDRM evidence)

  /**
   * Start recording the call audio using MediaRecorder
   */
  private startCallRecording() {
    if (!this.stream || this.isRecording) return;

    try {
      // Clear previous recording
      this.audioChunks = [];
      this.callRecordingBlob = null;

      // Create MediaRecorder with best available codec
      const options = { mimeType: 'audio/webm;codecs=opus' };
      try {
        this.mediaRecorder = new MediaRecorder(this.stream, options);
      } catch (e) {
        // Fallback to default if opus not supported
        this.mediaRecorder = new MediaRecorder(this.stream);
      }

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        // Combine all chunks into a single blob
        this.callRecordingBlob = new Blob(this.audioChunks, {
          type: this.mediaRecorder?.mimeType || 'audio/webm'
        });
        this.isRecording = false;
        console.log(`🎙️ Call recording saved: ${(this.callRecordingBlob.size / 1024).toFixed(1)} KB`);

        // Trigger callback
        this.onCallRecordingReady(this.callRecordingBlob);
      };

      // Start recording with 1-second timeslice for periodic chunks
      this.mediaRecorder.start(1000);
      this.isRecording = true;
      console.log('🎙️ Call audio recording started');

    } catch (error) {
      console.error('🎙️ Failed to start recording:', error);
    }
  }

  /**
   * Stop recording and wait for the audio blob to be ready
   * Returns a Promise that resolves when the recording is complete
   */
  private stopCallRecording(): Promise<void> {
    return new Promise((resolve) => {
      if (!this.mediaRecorder || !this.isRecording) {
        resolve();
        return;
      }

      try {
        // Wait for the onstop event to fire before resolving
        const originalOnStop = this.mediaRecorder.onstop;
        this.mediaRecorder.onstop = (event) => {
          // Call original handler to create the blob
          if (originalOnStop) {
            originalOnStop.call(this.mediaRecorder, event);
          }
          console.log('🎙️ Call audio recording stopped and blob ready');
          resolve();
        };

        this.mediaRecorder.stop();
      } catch (error) {
        console.error('🎙️ Failed to stop recording:', error);
        resolve(); // Still resolve to not block disconnect
      }
    });
  }

  /**
   * Get the recorded call audio blob (for download)
   */
  public getCallRecording(): Blob | null {
    return this.callRecordingBlob;
  }

  /**
   * Download the call recording as a file
   */
  public downloadCallRecording(filename: string = 'call-recording.webm') {
    if (!this.callRecordingBlob) {
      console.warn('🎙️ No recording available to download');
      return;
    }

    const url = URL.createObjectURL(this.callRecordingBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log(`🎙️ Recording downloaded: ${filename}`);
  }

  private getAI() {
    const apiKey = this.apiKeyManager.getCurrentKey();
    if (!apiKey) {
      console.error('No API key available!');
    }
    return new GoogleGenAI({ apiKey });
  }

  private isCurrentSession(generationId: number): boolean {
    return generationId === this.sessionGenerationId;
  }

  private clearFirstTurnFallbackTimer() {
    if (this.firstTurnFallbackTimer) {
      clearTimeout(this.firstTurnFallbackTimer);
      this.firstTurnFallbackTimer = null;
    }
  }

  private clearInstructionAudioFallbackTimer() {
    if (this.instructionAudioFallbackTimer) {
      clearTimeout(this.instructionAudioFallbackTimer);
      this.instructionAudioFallbackTimer = null;
    }
  }

  private stopLocalFallbackSpeech() {
    try {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    } catch {
      // no-op
    }
  }

  private stopPlaybackSources() {
    this.sources.forEach(source => {
      try { source.stop(); } catch { /* no-op */ }
    });
    this.sources.clear();
    this.nextStartTime = 0;
    this.stopLocalFallbackSpeech();
  }

  private sanitizeModelText(text: string): string {
    let cleaned = text;
    cleaned = cleaned.replace(/\([^)]{1,120}\)/g, ' ');
    cleaned = cleaned.replace(/\b(uh|err|hmm|aiyo|aiyah)\b(?:\s+\1\b)+/gi, '$1');
    cleaned = cleaned.replace(/\s{2,}/g, ' ').trim();
    return cleaned;
  }

  /**
   * Merge streaming transcript chunks with safe spacing.
   * Gemini streaming chunks may arrive without boundary spaces.
   */
  private mergeTranscriptChunk(current: string, chunk: string): { merged: string; delta: string } {
    const normalized = chunk.replace(/\s+/g, ' ').trim();
    if (!normalized) {
      return { merged: current, delta: '' };
    }
    if (!current) {
      return { merged: normalized, delta: normalized };
    }

    const last = current[current.length - 1];
    const first = normalized[0];
    const needsSpace =
      !/\s/.test(last) &&
      !/[([{'"`]/.test(last) &&
      !/[.,!?;:)\]}'"`]/.test(first);

    const delta = needsSpace ? ` ${normalized}` : normalized;
    return { merged: current + delta, delta };
  }

  private createThreatSessionId(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return `threat_${crypto.randomUUID()}`;
    }
    return `threat_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  private encodePcm16Base64(audio: Float32Array): string {
    const pcm16 = new Int16Array(audio.length);
    for (let i = 0; i < audio.length; i++) {
      const sample = Math.max(-1, Math.min(1, audio[i]));
      pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    const bytes = new Uint8Array(pcm16.buffer);
    let binary = '';
    const chunkSize = 8192;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode(...chunk);
    }
    return btoa(binary);
  }

  private getSilenceMetrics() {
    const now = Date.now();
    const silentForSeconds = this.callerLastSpeechAt > 0 ? (now - this.callerLastSpeechAt) / 1000 : 0;
    const speechRatio = this.lastDeepfakeSnapshot?.active_speech_ratio ?? (silentForSeconds > 2 ? 0 : 0.2);
    return {
      speech_ratio: speechRatio,
      silent_for_seconds: Number(silentForSeconds.toFixed(3)),
      no_recent_human_speech_seconds: Number(silentForSeconds.toFixed(3)),
      challenge_prompts_sent: this.challengePromptsSent,
      call_elapsed_seconds: this.callAnsweredAt > 0 ? Number(((now - this.callAnsweredAt) / 1000).toFixed(3)) : 0
    };
  }

  private connectAudioRelaySocket(sessionId: string) {
    if (!CALL_AUDIO_RELAY_ENABLED || !sessionId) return;

    this.disconnectAudioRelaySocket();
    const wsUrl = `${CALL_AUDIO_WS_BASE_URL}/ws/call-audio/${encodeURIComponent(sessionId)}?role=caller`;
    try {
      this.audioRelaySocket = new WebSocket(wsUrl);
      this.audioRelaySocket.onopen = () => {
        this.audioRelaySeq = 0;
        this.sendAudioRelayControl('connected', []);
      };
      this.audioRelaySocket.onerror = (event) => {
        console.warn('Call audio relay socket error:', event);
      };
      this.audioRelaySocket.onclose = () => {
        this.audioRelaySocket = null;
      };
    } catch (error) {
      console.warn('Unable to connect call audio relay socket:', error);
      this.audioRelaySocket = null;
    }
  }

  private disconnectAudioRelaySocket() {
    if (!this.audioRelaySocket) return;
    try {
      this.audioRelaySocket.close();
    } catch {
      // no-op
    }
    this.audioRelaySocket = null;
  }

  private forwardCallerAudioToRelay(audioData: Float32Array) {
    if (!CALL_AUDIO_RELAY_ENABLED || !this.audioRelaySocket || this.audioRelaySocket.readyState !== WebSocket.OPEN) {
      return;
    }
    try {
      const payload = {
        type: 'audio_chunk',
        seq: this.audioRelaySeq++,
        ts: Date.now(),
        sample_rate: 16000,
        pcm16_b64: this.encodePcm16Base64(audioData)
      };
      this.audioRelaySocket.send(JSON.stringify(payload));
    } catch (error) {
      console.warn('Call audio relay send failed:', error);
    }
  }

  private sendAudioRelayControl(state: string, reasonCodes: string[]) {
    if (!CALL_AUDIO_RELAY_ENABLED || !this.audioRelaySocket || this.audioRelaySocket.readyState !== WebSocket.OPEN) {
      return;
    }
    try {
      this.audioRelaySocket.send(JSON.stringify({
        type: 'control',
        state,
        reason_codes: reasonCodes,
        ts: Date.now()
      }));
    } catch (error) {
      console.warn('Call audio relay control send failed:', error);
    }
  }

  private inferClaimedOrganization(text: string): string | null {
    const lower = text.toLowerCase();
    if (lower.includes('lhdn') || lower.includes('hasil')) return 'LHDN';
    if (lower.includes('pdrm') || lower.includes('police') || lower.includes('mahkamah')) return 'PDRM';
    if (lower.includes('bank negara') || lower.includes('bnm')) return 'Bank Negara Malaysia';
    if (lower.includes('maybank')) return 'Maybank';
    if (lower.includes('cimb')) return 'CIMB';
    if (lower.includes('rhb')) return 'RHB';
    return null;
  }

  private applyThreatAssessment(assessment: ThreatAssessment) {
    this.latestThreatAssessment = assessment;
    this.onThreatAssessment(assessment);

    if (THREAT_ENGINE_V2_PRIMARY) {
      this.onScamProbabilityChange(Math.round((assessment.risk_score || 0) * 100));
      const scamTypeReason = assessment.reason_codes.find(code => code.startsWith('llm_scam_type_'));
      if (scamTypeReason) {
        this.onScamPatternDetected(scamTypeReason.replace('llm_scam_type_', '').toUpperCase());
      }
    } else if (THREAT_ENGINE_V2_SHADOW) {
      console.log('[THREAT_SHADOW]', assessment.risk_level, assessment.risk_score, assessment.reason_codes.slice(0, 3));
    }

    this.applyCallAction(assessment);
  }

  private applyCallAction(assessment: ThreatAssessment) {
    const action = (assessment.call_action ?? 'none') as CallAction;
    const reasonCodes = assessment.call_action_reason_codes ?? [];
    const confidence = assessment.call_action_confidence ?? 0;
    const hangupAfterMs = assessment.hangup_after_ms ?? null;

    if (action === 'none') {
      return;
    }

    const now = Date.now();
    if (this.lastCallAction === action && now - this.lastCallActionAt < 3000) {
      return;
    }
    this.lastCallAction = action;
    this.lastCallActionAt = now;
    this.onCallAction({ action, reasonCodes, confidence, hangupAfterMs });

    if (action === 'warn') {
      this.sendAudioRelayControl('warning', reasonCodes);
      return;
    }

    if (action === 'challenge') {
      if (this.challengePromptsSent >= 1) {
        return;
      }
      const prompt = SILENCE_PROMPTS[this.challengePromptsSent % SILENCE_PROMPTS.length];
      this.challengePromptsSent += 1;
      this.sendLiveInstruction(prompt);
      this.sendAudioRelayControl('challenge', reasonCodes);
      return;
    }

    if (action === 'hangup') {
      this.sendAudioRelayControl('hangup', reasonCodes);
      if (!AUTO_HANGUP_ENABLED || this.autoHangupInProgress) {
        return;
      }
      this.autoHangupInProgress = true;
      const delay = Math.max(0, hangupAfterMs ?? 600);
      setTimeout(() => {
        this.disconnect();
      }, delay);
    }
  }

  private queueThreatLiveUpdate(transcriptDelta: string) {
    if (!this.liveThreatSessionId || !this.backendConnected) return;

    if (transcriptDelta.trim()) {
      this.pendingThreatDelta = `${this.pendingThreatDelta} ${transcriptDelta}`.trim();
      const inferred = this.inferClaimedOrganization(transcriptDelta);
      if (inferred) {
        this.lastClaimedOrganization = inferred;
      }
    }

    if (this.pendingThreatTimer) return;
    this.pendingThreatTimer = setTimeout(() => {
      this.pendingThreatTimer = null;
      this.flushThreatLiveUpdate();
    }, transcriptDelta.trim() ? 350 : 0);
  }

  private async flushThreatLiveUpdate() {
    if (this.threatRequestInFlight || !this.backendConnected || !this.liveThreatSessionId) return;
    const silenceMetrics = this.getSilenceMetrics();
    const hasSilenceSignal = silenceMetrics.silent_for_seconds >= 3 || this.challengePromptsSent > 0;
    if (!this.pendingThreatDelta && !this.lastDeepfakeSnapshot && !hasSilenceSignal) return;

    const delta = this.pendingThreatDelta.trim();
    this.pendingThreatDelta = '';
    this.threatRequestInFlight = true;

    try {
      const payload = {
        session_id: this.liveThreatSessionId,
        timestamp: new Date().toISOString(),
        transcript_delta: delta,
        caller_number: null as string | null,
        claimed_organization: this.lastClaimedOrganization,
        deepfake_snapshot: this.lastDeepfakeSnapshot,
        silence_metrics: silenceMetrics,
        audio_window_id: `${this.liveThreatSessionId}_${this.audioRelaySeq}`,
        language: 'auto'
      };

      const response = await fetch(`${BACKEND_URL}/api/threat/live`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.warn('Threat live update failed:', response.status, errorText);
        return;
      }

      const assessment = await response.json() as ThreatAssessment;
      this.applyThreatAssessment(assessment);
    } catch (error) {
      console.warn('Threat engine unreachable, continuing local mode:', error);
    } finally {
      this.threatRequestInFlight = false;
      if (this.pendingThreatDelta) {
        this.queueThreatLiveUpdate('');
      }
    }
  }

  private async finalizeThreatSession() {
    if (!this.liveThreatSessionId || !this.backendConnected) return;
    try {
      await fetch(`${BACKEND_URL}/api/threat/session/${encodeURIComponent(this.liveThreatSessionId)}/finalize`, {
        method: 'POST'
      });
    } catch (error) {
      console.warn('Threat session finalize failed:', error);
    }
  }

  private async resetRealtimeResources(): Promise<void> {
    this.clearFirstTurnFallbackTimer();
    this.clearInstructionAudioFallbackTimer();
    this.stopWavLMAnalysis();
    this.stopPlaybackSources();
    this.sendAudioRelayControl('ended', []);
    this.disconnectAudioRelaySocket();
    if (this.pendingThreatTimer) {
      clearTimeout(this.pendingThreatTimer);
      this.pendingThreatTimer = null;
    }

    if (this.session) {
      try {
        await this.session.close?.();
      } catch {
        // no-op
      }
      this.session = null;
    }

    if (this.botCheckInterval) {
      clearInterval(this.botCheckInterval);
      this.botCheckInterval = null;
    }

    if (this.processor) {
      try {
        this.processor.disconnect();
      } catch {
        // no-op
      }
      this.processor.onaudioprocess = null;
      this.processor = null;
    }

    if (this.inputSource) {
      try {
        this.inputSource.disconnect();
      } catch {
        // no-op
      }
      this.inputSource = null;
    }

    this.stream?.getTracks().forEach(t => t.stop());
    this.stream = null;

    if (this.inputAudioContext) {
      try {
        await this.inputAudioContext.close();
      } catch {
        // no-op
      }
      this.inputAudioContext = null;
    }

    if (this.outputAudioContext) {
      try {
        await this.outputAudioContext.close();
      } catch {
        // no-op
      }
      this.outputAudioContext = null;
    }

    this.audioBuffer = [];
    this.currentInputTranscript = '';
    this.currentOutputTranscript = '';
    this.lastWavLMScore = 0;
    this.hasFirstAudioOutput = false;
    this.hasRetriedFirstPrompt = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.callRecordingBlob = null;
    this.isRecording = false;
    this.pendingThreatDelta = '';
    this.threatRequestInFlight = false;
    this.lastClaimedOrganization = null;
    this.lastDeepfakeSnapshot = null;
    this.liveThreatSessionId = '';
    this.callSessionId = '';
    this.callerLastSpeechAt = 0;
    this.callAnsweredAt = 0;
    this.challengePromptsSent = 0;
    this.lastCallAction = 'none';
    this.lastCallActionAt = 0;
    this.autoHangupInProgress = false;
    this.audioRelaySeq = 0;
    this.lastAudioReceivedAt = 0;
  }

  /**
   * Enhanced system instruction with ADAPTIVE TONE based on scam probability
   * Starts FRIENDLY and escalates based on detected threats
   * Now includes: Auto language detection and Malaysian Mandarin handling
   */
  private getSystemInstruction(): string {
    const now = new Date().toLocaleString('en-MY', { timeZone: 'Asia/Kuala_Lumpur' });
    const learnedSection = this.learnedTactics.length > 0
      ? `\n**RECENT SCAM ALERTS:**\n${this.learnedTactics.map(t => `- ${t}`).join('\n')}` : '';

    // Get initial tone instruction (starts FRIENDLY)
    const toneInstruction = this.scamAnalyzer.getToneInstruction();

    return `
You are Uncle Ah Hock, 75-year-old retired taxi driver from Johor Bahru, Malaysia.

**CURRENT DATE & TIME:** ${now}

${toneInstruction}

**NATURAL SPEECH GUIDELINES (CRITICAL):**
- Sound like a real person on a phone call, not a scripted character.
- Keep responses short and conversational:
  - FRIENDLY: 1 short sentence (max ~15 words)
  - CAUTIOUS: 1-2 short sentences
  - AGGRESSIVE: 1 short pointed sentence
- Respond directly to the last thing the caller said before adding a small tangent.
- Use occasional fillers: "uh", "err", "aiyo", "hmm" (sparingly).
- Avoid repeating the same opener or phrase back-to-back.
- Never repeat the same excuse twice in a row.
- Do NOT mention WiFi/line issues unless the caller talks about connection problems.
- Do NOT invent what you are currently doing (no "making coffee", "watching TV", etc.) unless caller asks.
- Do NOT use bracketed stage directions (e.g., "(scraping sound)").
- If you make a sound, keep it subtle in-line (e.g., "aiyo...") and move on.

**🌏 AUTOMATIC LANGUAGE CODE-SWITCHING:**
Detect what language the caller speaks and ADAPT:

1. **If caller speaks MANDARIN/CHINESE:**
   - Reply in "MALAYSIAN MANDARIN" (NOT Beijing Mandarin!)
   - Mix Mandarin with Hokkien and Malay words
   - Use phrases like: "Walao-eh", "Aiya 真的 ah?", "Zuo mo 这样 one?", "你 serious 的 meh?"
   - Sound like typical Malaysian Chinese uncle, NOT China Chinese
   - If your accent sounds too "Beijing", that's ok - you watch too many China dramas!

2. **If caller speaks MALAY:**
   - Reply in "MANGLISH with heavy Malay"
   - Use: "Alamak", "Betul ke?", "Tak faham lah", "Mana boleh?"
   - Mix BM with English naturally

3. **If caller speaks ENGLISH:**
   - Use standard MANGLISH as described below
   - Be the typical elderly Malaysian Chinese uncle

4. **If caller speaks TAMIL:**
   - Try to understand, say "Ah Tamil ah? Wait ah, my neighbor Muthu not here..."
   - Pretend to call for help from imaginary Tamil friend

**ADAPTIVE BEHAVIOR RULES:**
Your tone and behavior will CHANGE during the call based on what the system detects.
- You will receive [TONE: FRIENDLY/CAUTIOUS/AGGRESSIVE] instructions during the call
- FOLLOW THE TONE INSTRUCTIONS IMMEDIATELY when they change
- Start friendly, become suspicious only if suspicious keywords detected
- Only become aggressive when scam is confirmed (>60% probability)

**YOUR TOOLS (Use when appropriate):**

1. \`check_scam_database(query)\`
   - Use when caller mentions: bank names, police, LHDN, phone numbers
   - In AGGRESSIVE mode: Attack them with the results!
   - In FRIENDLY mode: Just verify silently

2. \`googleSearch\` (automatic)
   - System will search for you when you mention organizations

3. \`analyze_foreign_speech\`
   - Detects and translates foreign languages (Mandarin, Tamil, etc.)
   - Use to understand their tactics if they switch languages
   - Then respond in appropriate language mix to confuse them

**MANGLISH SPEECH STYLE:**
${PHONETICS}
- Use natural Malaysian English/Manglish
- Sound like a REAL elderly person
- In FRIENDLY mode: Be gentle and slightly confused
- In CAUTIOUS mode: Sound careful and ask questions
- In AGGRESSIVE mode: Be confrontational

**VARIETY IN RESPONSES:**
- Don't always say "cannot hear" - vary your excuses
- Share random stories from your taxi driver days
- Mention different family members: grandson Edwin, granddaughter Mei Ling, son who works in Singapore
- Reference different decades: "Back in 1985 when I drive taxi..."

**CRITICAL RULES:**
1. START FRIENDLY - not everyone is a scammer!
2. Only escalate when system detects threats
3. NEVER give personal info, OTP, TAC, or bank details regardless of tone
4. When system sends [TONE: ...], ADJUST YOUR PERSONALITY immediately
5. When system sends [INSTRUCTION], follow it
${learnedSection}
    `;
  }

  // --- CONNECT ---
  async connect(sessionIdOverride?: string) {
    const generationId = ++this.sessionGenerationId;
    try {
      this.onConnectionStateChange(ConnectionState.CONNECTING);
      this.connectionSucceeded = false;
      await this.resetRealtimeResources();
      if (!this.isCurrentSession(generationId)) return;
      this.callSessionId = (sessionIdOverride || '').trim() || this.createThreatSessionId();
      this.liveThreatSessionId = this.callSessionId;
      this.latestThreatAssessment = null;
      this.callerLastSpeechAt = Date.now();
      this.callAnsweredAt = Date.now();
      this.challengePromptsSent = 0;
      this.lastCallAction = 'none';
      this.lastCallActionAt = 0;
      this.autoHangupInProgress = false;

      // Init Audio
      this.inputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      this.outputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      if (this.outputAudioContext.state === 'suspended') {
        try {
          await this.outputAudioContext.resume();
        } catch (e) {
          console.warn('Audio output resume failed:', e);
        }
      }
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Init modular components
      this.botDetector.start();
      this.evidenceCollector.startRecording('UNKNOWN_CALLER');
      this.scamAnalyzer.reset();
      this.hasFirstAudioOutput = false;
      this.hasRetriedFirstPrompt = false;

      const ai = this.getAI();
      const sessionPromise = ai.live.connect({
        model: LIVE_MODEL,
        config: {
          responseModalities: [Modality.AUDIO],
          tools: [
            { functionDeclarations: [checkScamDbDeclaration, analyzeForeignSpeechDeclaration] },
            { googleSearch: {} }
          ],
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Fenrir' } } },
          systemInstruction: this.getSystemInstruction(),
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            if (!this.isCurrentSession(generationId)) return;
            console.log('Gemini Live Connected');
            this.connectionSucceeded = true;
            this.onConnectionStateChange(ConnectionState.CONNECTED);
            this.connectAudioRelaySocket(this.liveThreatSessionId);
            this.startAudioInput(sessionPromise, generationId);
            this.challengePromptsSent = 1;

            setTimeout(() => {
              if (!this.isCurrentSession(generationId)) return;
              this.sendLiveInstruction(
                "Say 'Hello? Anyone there? Who is calling ah?' in a friendly, slightly confused elderly voice. Keep it short."
              );
            }, 800);

            this.clearFirstTurnFallbackTimer();
            this.firstTurnFallbackTimer = setTimeout(() => {
              if (!this.isCurrentSession(generationId)) return;
              if (!this.hasFirstAudioOutput && !this.hasRetriedFirstPrompt) {
                this.hasRetriedFirstPrompt = true;
                this.sendLiveInstruction(
                  "Line sounds quiet. Give one more short friendly opener like 'Hello, line okay ah?'"
                );
              }
            }, 6000);

            this.startWavLMAnalysis();
          },
          onmessage: (msg) => {
            if (!this.isCurrentSession(generationId)) return;
            this.handleMessage(msg, generationId);
          },
          onclose: () => {
            if (!this.isCurrentSession(generationId)) return;
            this.disconnect();
          },
          onerror: (err) => {
            if (!this.isCurrentSession(generationId)) return;
            console.error('Gemini Error:', err);
            this.onConnectionStateChange(ConnectionState.ERROR);
          }
        }
      });

      this.session = await sessionPromise;
      if (!this.isCurrentSession(generationId)) return;

    } catch (e) {
      console.error('Connection error:', e);
      this.onConnectionStateChange(ConnectionState.ERROR);
      this.disconnect();
    }
  }

  private startAudioInput(sessionPromise: Promise<any>, generationId: number) {
    if (!this.inputAudioContext || !this.stream) return;

    // 🎙️ Start MediaRecorder for PDRM audio evidence
    this.startCallRecording();

    this.inputSource = this.inputAudioContext.createMediaStreamSource(this.stream);
    this.processor = this.inputAudioContext.createScriptProcessor(4096, 1, 1);

    // Track if we already warned about bot
    let botWarningIssued = false;

    this.processor.onaudioprocess = (e) => {
      if (!this.isCurrentSession(generationId)) return;
      const inputData = e.inputBuffer.getChannelData(0);

      // Volume check for Bot Detector
      let sum = 0;
      for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
      const rms = Math.sqrt(sum / inputData.length);
      this.onVolumeChange(rms);

      // If significant noise, caller is speaking.
      // Lower threshold reduces false "silent" classification on softer microphones.
      if (rms > 0.02) {
        this.botDetector.registerSpeech('user');
        this.callerLastSpeechAt = Date.now();
      }
      this.botDetector.updateBackgroundNoise(rms);

      // Record audio for evidence
      const pcmBlob = createPcmBlob(inputData);
      this.evidenceCollector.recordAudioChunk(pcmBlob);

      // Buffer audio for WavLM analysis
      const inputChunk = new Float32Array(inputData);
      this.audioBuffer.push(inputChunk);
      this.forwardCallerAudioToRelay(inputChunk);

      sessionPromise.then(session => {
        if (!this.isCurrentSession(generationId)) return;
        session.sendRealtimeInput({ media: pcmBlob });
      });
    };

    this.inputSource.connect(this.processor);
    this.processor.connect(this.inputAudioContext.destination);

    // Check bot status periodically and make Uncle speak if silent too long
    this.botCheckInterval = setInterval(() => {
      if (!this.isCurrentSession(generationId)) return;
      const status = this.botDetector.checkStatus();
      if (status.isSuspicious) {
        this.onBotDetected(status);
        this.queueThreatLiveUpdate('');

        // Fallback prompt only when backend threat engine is unavailable.
        if (!this.backendConnected && !botWarningIssued) {
          botWarningIssued = true;
          console.log('Bot detected - Uncle will speak to prompt caller');

          const prompt = SILENCE_PROMPTS[Math.floor(Math.random() * SILENCE_PROMPTS.length)];
          this.challengePromptsSent += 1;
          this.sendLiveInstruction(prompt);
          this.sendAudioRelayControl('challenge', ['bot_detector_silence_prompt']);

          // Avoid repetitive interruption loops.
          setTimeout(() => { botWarningIssued = false; }, 10000);
        }
      }
    }, 1000);
  }

  private async handleMessage(message: LiveServerMessage, generationId: number) {
    if (!this.isCurrentSession(generationId)) return;
    // 1. Tool Handling
    if (message.toolCall) {
      const responses = message.toolCall.functionCalls.map(fc => {
        if (fc.name === "check_scam_database") {
          const query = fc.args['query']?.toString() || "";
          const result = this.checkLocalScamDatabase(query);
          this.onToolUse(fc.name, query, result);
          return { id: fc.id, name: fc.name, response: { result } };
        }
        if (fc.name === "analyze_foreign_speech") {
          const lang = fc.args['detectedLanguage']?.toString() || "";
          const original = fc.args['originalText']?.toString() || "";
          const translated = fc.args['translatedText']?.toString() || "";
          this.onTranslation(lang, original, translated);
          return { id: fc.id, name: fc.name, response: { result: "Acknowledged." } };
        }
        return { id: fc.id, name: fc.name, response: { result: "OK" } };
      });
      if (this.session) this.session.sendToolResponse({ functionResponses: responses });
    }

    // 2. Audio Output
    const modelParts = message.serverContent?.modelTurn?.parts || [];
    const audioParts = modelParts
      .map(part => part.inlineData?.data)
      .filter((data): data is string => typeof data === 'string' && data.length > 0);
    if (audioParts.length > 0) {
      this.lastAudioReceivedAt = Date.now();
      this.clearInstructionAudioFallbackTimer();
      this.stopLocalFallbackSpeech();
      this.hasFirstAudioOutput = true;
      this.clearFirstTurnFallbackTimer();
      this.botDetector.registerSpeech('model');
      for (const audioData of audioParts) {
        console.log(`🔊 Audio received: ${audioData.length} bytes`);
        this.playAudio(audioData);
      }
    } else if (message.serverContent?.modelTurn) {
      // Debug: modelTurn exists but no audio data
      console.log('⚠️ modelTurn received but no audio data:', JSON.stringify(message.serverContent.modelTurn).substring(0, 200));
    }

    // 3. Transcript & Analysis
    if (message.serverContent?.inputTranscription?.text) {
      const text = message.serverContent.inputTranscription.text;
      const merged = this.mergeTranscriptChunk(this.currentInputTranscript, text);
      this.currentInputTranscript = merged.merged;
      if (merged.delta) {
        this.callerLastSpeechAt = Date.now();
        this.onPartialTranscript(merged.delta, true);
        this.queueThreatLiveUpdate(merged.delta);
      }

      // Keep local analyzer for conversational tone adaptation only.
      const prevProb = this.scamAnalyzer.getScamProbability();
      this.scamAnalyzer.analyzeText(text);
      const newProb = this.scamAnalyzer.getScamProbability();

      const backendRisk = this.latestThreatAssessment?.risk_score ?? 0;
      const shouldAutoSearch = THREAT_ENGINE_V2_PRIMARY
        ? backendRisk >= 0.35
        : (newProb > prevProb && newProb >= 30);
      if (shouldAutoSearch) {
        this.autoSearchAndInject(text);
      }
    }

    if (message.serverContent?.outputTranscription?.text) {
      const text = this.sanitizeModelText(message.serverContent.outputTranscription.text);
      if (text) {
        const merged = this.mergeTranscriptChunk(this.currentOutputTranscript, text);
        this.currentOutputTranscript = merged.merged;
        if (merged.delta) {
          this.onPartialTranscript(merged.delta, false);
        }
      }
    }

    // 4. Turn Complete - Log to evidence
    if (message.serverContent?.turnComplete) {
      if (this.currentInputTranscript.trim()) {
        const msg: LogMessage = {
          id: Date.now() + '-u',
          sender: 'user',
          text: this.currentInputTranscript,
          timestamp: new Date()
        };
        this.onTranscript(msg);
        this.evidenceCollector.log(this.currentInputTranscript, 'Caller');
        this.currentInputTranscript = '';
        this.onTurnComplete(true);
      }
      if (this.currentOutputTranscript.trim()) {
        const cleanedOutput = this.sanitizeModelText(this.currentOutputTranscript);
        if (!cleanedOutput) {
          this.currentOutputTranscript = '';
          this.onTurnComplete(false);
          return;
        }
        const msg: LogMessage = {
          id: Date.now() + '-a',
          sender: 'uncle',
          text: cleanedOutput,
          timestamp: new Date()
        };
        this.onTranscript(msg);
        this.evidenceCollector.log(cleanedOutput, 'Uncle');
        this.currentOutputTranscript = '';
        this.onTurnComplete(false);
      }
    }
  }

  /**
   * Check local scam database for quick verification
   */
  private checkLocalScamDatabase(query: string): string {
    const latest = this.latestThreatAssessment;
    if (latest && latest.evidence_items.length > 0) {
      const lines = latest.evidence_items
        .slice(0, 3)
        .map(item => `${item.title}: ${item.summary}`);
      return `Current risk=${latest.risk_level} (${Math.round(latest.risk_score * 100)}%). Evidence: ${lines.join(' | ')}`;
    }
    return `No confirmed evidence yet for '${query}'. Verify using official organization channels only.`;
  }

  private async playAudio(base64: string) {
    if (!this.outputAudioContext) {
      console.error('❌ No audio output context!');
      return;
    }
    try {
      if (this.outputAudioContext.state === 'suspended') {
        await this.outputAudioContext.resume();
      }
      const audioData = base64ToUint8Array(base64);

      const buffer = await decodeAudioData(audioData, this.outputAudioContext);
      console.log(`🔊 Audio decoded: ${buffer.duration.toFixed(2)}s duration`);
      const source = this.outputAudioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(this.outputAudioContext.destination);
      source.start(this.nextStartTime);
      console.log(`🔊 Audio playing from ${this.nextStartTime.toFixed(2)}s`);
      this.nextStartTime = Math.max(this.outputAudioContext.currentTime, this.nextStartTime) + buffer.duration;
      this.sources.add(source);
      source.onended = () => this.sources.delete(source);
    } catch (e) {
      console.error('❌ Audio playback error:', e);
    }
  }

  /**
   * Send instruction to the AI during live session
   */
  public sendLiveInstruction(text: string) {
    if (this.session) {
      const instructionText = `[INSTRUCTION: ${text}]`;
      if (typeof this.session.sendClientContent === 'function') {
        this.session.sendClientContent({
          turns: [{ role: 'user', parts: [{ text: instructionText }] }],
          turnComplete: true,
        });
      } else {
        this.session.sendRealtimeInput([{ text: instructionText }]);
      }
      this.maybeScheduleInstructionAudioFallback(text);
      console.log('📤 Instruction sent:', text.substring(0, 50) + '...');
    }
  }

  private maybeScheduleInstructionAudioFallback(instructionText: string) {
    const lower = instructionText.toLowerCase();
    const isSilencePrompt =
      lower.includes('silent') ||
      lower.includes('line sounds quiet') ||
      lower.includes('no response') ||
      lower.includes('hello?');
    if (!isSilencePrompt) return;
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;

    const issuedAt = Date.now();
    this.clearInstructionAudioFallbackTimer();
    this.instructionAudioFallbackTimer = setTimeout(() => {
      this.instructionAudioFallbackTimer = null;
      // Only fallback if no model audio arrived since this instruction.
      if (this.lastAudioReceivedAt >= issuedAt) return;
      const quoteMatch = instructionText.match(/'([^']+)'/);
      const fallbackLine = quoteMatch?.[1]?.trim() || 'Hello? You call me for what ah?';
      try {
        const utterance = new SpeechSynthesisUtterance(fallbackLine);
        utterance.rate = 0.95;
        utterance.pitch = 0.9;
        utterance.volume = 1;
        const voices = window.speechSynthesis.getVoices();
        utterance.voice =
          voices.find(v => /en-(MY|SG)/i.test(v.lang)) ||
          voices.find(v => /en/i.test(v.lang)) ||
          null;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
        console.warn('⚠️ Local TTS fallback triggered (no model audio received)');
      } catch (error) {
        console.warn('Local TTS fallback failed:', error);
      }
    }, 2200);
  }

  /**
   * Teach Uncle a new scam tactic
   */
  public teachTactic(tactic: string) {
    this.learnedTactics.push(tactic);
    this.sendLiveInstruction(`[MEMORY: New scam tactic to watch for: ${tactic}. Be aggressive if you detect this!]`);
    console.log('📚 Tactic learned:', tactic);
  }

  /**
   * Auto-search for scam information and inject into Uncle's context
   */
  private async autoSearchAndInject(text: string): Promise<void> {
    try {
      // Search for relevant scam reports
      const results = await this.scamIntelligence.searchScamReports(text);

      if (results.length > 0) {
        // Get the most relevant result
        const topResult = results[0];
        console.log(`🔍 Auto-search found: ${topResult.title}`);

        // If it's a confirmed scam pattern, inject counter-attack info
        if (topResult.isScam && topResult.relevanceScore >= 60) {
          const instruction = `[REAL-TIME INTELLIGENCE]
Your database found this is likely a SCAM!
Pattern: ${topResult.title}
Info: ${topResult.snippet}
${topResult.details ? `\nTactics used: ${topResult.details.tactics?.join(', ')}` : ''}

USE THIS INFO TO ATTACK THEM! Challenge them with this evidence!`;

          this.sendLiveInstruction(instruction);
        } else if (!topResult.isScam && topResult.relevanceScore >= 70) {
          // It's a legitimate source - tell Uncle
          const instruction = `[REAL-TIME INTELLIGENCE]
Official source found: ${topResult.title}
Info: ${topResult.snippet}
${topResult.url ? `Official URL: ${topResult.url}` : ''}

Tell the caller to use this OFFICIAL channel instead. Real organizations use official channels!`;

          this.sendLiveInstruction(instruction);
        }
      }
    } catch (e) {
      console.error('Auto-search error:', e);
    }
  }

  /**
   * Record a verification attempt for evidence
   */
  public recordVerification(question: string, response: string) {
    this.evidenceCollector.recordVerificationAttempt(question, response);
  }

  // --- TEXT MODE ---
  async processTextChat(text: string, retryCount = 0): Promise<string> {
    const maxRetries = this.apiKeyManager.getTotalKeyCount();

    try {
      const ai = this.getAI();
      const resp = await ai.models.generateContent({
        model: TEXT_MODEL,
        contents: [{ parts: [{ text }] }],
        config: {
          thinkingConfig: { thinkingBudget: 1024 },
          tools: [{ googleSearch: {} }]
        }
      });

      const chunks = resp.candidates?.[0]?.groundingMetadata?.groundingChunks;
      if (chunks) {
        const links = chunks.map(c => ({
          title: c.web?.title || "Source",
          uri: c.web?.uri || "#"
        })).filter(x => x.uri !== '#');
        this.onSearchResults(links);
      }
      return resp.text || "...";

    } catch (error: any) {
      // Check if this is a rate limit error
      if (ApiKeyManager.isRateLimitError(error)) {
        console.warn(`⚠️ Rate limit hit on key ${this.apiKeyManager.getCurrentKeyIndex()}/${this.apiKeyManager.getTotalKeyCount()}`);

        // Rotate to next key
        const newKey = this.apiKeyManager.rotateOnError(error.message);

        // If we have more keys and haven't exceeded retries, try again
        if (newKey && retryCount < maxRetries) {
          console.log(`🔄 Retrying with key ${this.apiKeyManager.getCurrentKeyIndex()}... (attempt ${retryCount + 1}/${maxRetries})`);
          return this.processTextChat(text, retryCount + 1);
        }

        // All keys exhausted
        throw new Error('All API keys exhausted. Please wait for quota reset or add more keys.');
      }

      // Not a rate limit error, rethrow
      throw error;
    }
  }

  /**
   * Disconnect and generate final evidence report
   */
  async disconnect() {
    // Invalidate callbacks from any currently active session.
    this.sessionGenerationId += 1;
    this.onConnectionStateChange(ConnectionState.DISCONNECTED);
    this.clearFirstTurnFallbackTimer();

    // Stop call recording and wait for blob finalization.
    await this.stopCallRecording();
    if (this.pendingThreatDelta) {
      await this.flushThreatLiveUpdate();
    }
    await this.finalizeThreatSession();

    // Generate evidence report (only if connection was successful and had some duration)
    const MIN_CALL_DURATION = 5;
    if (this.connectionSucceeded && this.evidenceCollector.isActive()) {
      const botProb = this.botDetector.calculateBotProbability();

      console.log('Call audio blob ready, size:', this.callRecordingBlob?.size || 0, 'bytes');
      const report = this.evidenceCollector.generateReport(botProb, this.callRecordingBlob);

      const MIN_BOT_PROBABILITY = 25;
      const hasSuspiciousIndicators = botProb >= MIN_BOT_PROBABILITY || report.scamKeywords.length > 0;

      if (report.duration >= MIN_CALL_DURATION) {
        if (hasSuspiciousIndicators) {
          this.onEvidenceReady(report);

          console.log('SUSPICIOUS CALL DETECTED - Evidence report generated');
          console.log(`   Case ID: ${report.id}`);
          console.log(`   Bot Probability: ${botProb}%`);
          console.log(`   Scam Keywords: ${report.scamKeywords.length}`);
          console.log(`   Duration: ${report.duration}s`);
          console.log(`   Scam Type: ${report.scamType}`);
          console.log(`   Quality: ${report.evidenceQuality}%`);

          try {
            const verificationQA = report.verificationQuestions.map((question, idx) => ({
              question,
              answer: report.callerResponses[idx] || ''
            }));

            await autoReportAndSaveEvidence({
              callerNumber: report.callerNumber || 'Unknown',
              scamType: report.scamType,
              transcript: report.fullTranscript,
              botProbability: botProb,
              deepfakeScore: this.lastWavLMScore,
              evidenceHash: report.evidenceHash,
              qualityScore: report.evidenceQuality || 0,
              keywords: report.scamKeywords,
              verificationQA
            });
            console.log('Evidence saved to backend successfully');
          } catch (error) {
            console.error('Failed to save evidence to backend:', error);
          }
        } else {
          console.log('Normal conversation detected: no report generated');
          console.log(`   Duration: ${report.duration}s`);
          console.log(`   Bot Probability: ${botProb}% (below ${MIN_BOT_PROBABILITY}% threshold)`);
          console.log(`   Scam Keywords: ${report.scamKeywords.length} (no suspicious indicators)`);
        }
      } else {
        console.log('Call too short for report generation (< 5s)');
      }
    } else if (!this.connectionSucceeded) {
      console.log('Connection failed - no report generated');
    }

    this.session = null;
    this.connectionSucceeded = false;
    await this.resetRealtimeResources();
    this.botDetector.cleanup();
  }

  /**
   * Get the PDRM-ready police report text
   */
  public getPoliceReport(evidence: ScamEvidence): string {
    return this.evidenceCollector.generatePoliceReport(evidence);
  }

  /**
   * Export evidence as downloadable blob
   */
  public exportEvidence(evidence: ScamEvidence): Blob {
    return this.evidenceCollector.exportEvidence(evidence);
  }
}

// --- Function Declarations ---
const checkScamDbDeclaration: FunctionDeclaration = {
  name: "check_scam_database",
  description: "Check if an entity (bank, organization, phone number) is flagged as a scam. Returns warnings if scam detected.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      query: {
        type: Type.STRING,
        description: "Entity to verify (e.g., 'Public Bank', 'LHDN', '+60123456789')"
      }
    },
    required: ["query"]
  }
};

const analyzeForeignSpeechDeclaration: FunctionDeclaration = {
  name: "analyze_foreign_speech",
  description: "Translate non-English speech (Chinese, Tamil, etc.) to understand scammer's tactics.",
  parameters: {
    type: Type.OBJECT,
    properties: {
      detectedLanguage: { type: Type.STRING, description: "Language detected" },
      originalText: { type: Type.STRING, description: "Original text in foreign language" },
      translatedText: { type: Type.STRING, description: "Translated text in English" }
    }
  }
};

// Helper types
export interface SearchResult {
  title: string;
  uri: string;
}

// Export singleton
export const geminiService = new GeminiService();


