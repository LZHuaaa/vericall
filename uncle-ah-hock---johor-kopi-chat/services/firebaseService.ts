/**
 * Firebase Service - Frontend Bridge
 * Connects Uncle Ah Hock frontend to VeriCall backend Firebase APIs
 * 
 * @author VeriCall Malaysia
 * @version 1.0.0
 */

// Backend API URL - change for production
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:5000/api';

// Firebase Direct Connection (for real-time demo state)
import { FirebaseApp, initializeApp } from 'firebase/app';
import { Auth, User, getAuth, signInAnonymously } from 'firebase/auth';
import { Firestore, Unsubscribe, arrayUnion, doc, getFirestore, onSnapshot, serverTimestamp, setDoc } from 'firebase/firestore';

// Firebase config - matches your firebase-credentials.json project
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'vericall-malaysia.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'vericall-malaysia',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || 'vericall-malaysia.appspot.com',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID
};

const firebaseConfigured = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.authDomain &&
  firebaseConfig.projectId &&
  firebaseConfig.storageBucket &&
  firebaseConfig.messagingSenderId &&
  firebaseConfig.appId
);

// Initialize Firebase (singleton)
let firebaseApp: FirebaseApp | null = null;
let db: Firestore | null = null;
let auth: Auth | null = null;
let warnedMissingFirebaseConfig = false;
let warnedFirebasePermission = false;
let currentDemoSessionId: string | null = null;
const WEB_CLIENT_ID_KEY = 'vericall_web_client_id';
const DEMO_CALL_POLL_INTERVAL_MS = 1000;

export function getWebClientId(): string {
  try {
    const existing = window.localStorage.getItem(WEB_CLIENT_ID_KEY);
    if (existing && existing.trim()) {
      return existing.trim();
    }
    const generated = `web_${Math.random().toString(36).slice(2, 10)}_${Date.now()}`;
    window.localStorage.setItem(WEB_CLIENT_ID_KEY, generated);
    return generated;
  } catch {
    return `web_${Date.now()}`;
  }
}

function warnMissingFirebaseConfigOnce(): void {
  if (warnedMissingFirebaseConfig) {
    return;
  }
  warnedMissingFirebaseConfig = true;
  console.warn('Firebase is not configured for web (missing VITE_FIREBASE_* env vars). Firestore sync is disabled.');
}

function warnFirestoreIssueOnce(error: unknown): void {
  const code = typeof error === 'object' && error && 'code' in error
    ? String((error as { code?: unknown }).code)
    : '';
  const message = typeof error === 'object' && error && 'message' in error
    ? String((error as { message?: unknown }).message)
    : String(error);
  const permissionIssue = code.includes('permission-denied') || message.includes('Missing or insufficient permissions');

  if (permissionIssue) {
    if (!warnedFirebasePermission) {
      warnedFirebasePermission = true;
      console.warn('Firestore denied access for demo call sync. Sign in and update Firestore security rules for calls/current_demo.');
    }
    return;
  }

  console.error('Firestore operation failed:', error);
}

function getFirebaseApp(): FirebaseApp | null {
  if (!firebaseConfigured) {
    warnMissingFirebaseConfigOnce();
    return null;
  }
  if (!firebaseApp) {
    firebaseApp = initializeApp(firebaseConfig);
    db = getFirestore(firebaseApp);
    auth = getAuth(firebaseApp);
  }
  return firebaseApp;
}

function getDb(): Firestore | null {
  const app = getFirebaseApp();
  if (!app) {
    return null;
  }
  return db;
}

function getAuthInstance(): Auth | null {
  const app = getFirebaseApp();
  if (!app) {
    return null;
  }
  return auth;
}

async function ensureAnonymousAuth(): Promise<boolean> {
  const authInstance = getAuthInstance();
  if (!authInstance) {
    return false;
  }

  if (!authInstance.currentUser) {
    try {
      await signInAnonymously(authInstance);
    } catch (error) {
      warnFirestoreIssueOnce(error);
      return false;
    }
  }

  return true;
}

// ==================== DEMO CALL STATE (Firestore Real-time) ====================

export type CallState = 'idle' | 'ringing' | 'connected' | 'ended';

export interface DemoThreatSummary {
  risk_level?: string;
  risk_score?: number;
  confidence?: number;
  mode?: string;
  retrieval_status?: string;
  reason_codes?: string[];
  call_action?: string;
  call_action_reason_codes?: string[];
}

export interface DemoCallDoc {
  state: CallState;
  sessionId?: string;
  callerName?: string;
  callerNumber?: string;
  callerId?: string;
  victimUserId?: string;
  requiresAnswer?: boolean;
  ownerDevice?: 'web' | 'mobile' | null;
  ownerClientId?: string | null;
  answeredAtIso?: string | null;
  answeredByLabel?: string | null;
  aiHostDevice?: 'web' | 'mobile' | null;
  aiHostClientId?: string | null;
  aiHostStatus?: string;
  threatSummary?: DemoThreatSummary;
  startTime?: any;
  startTimeIso?: string;
  endedAtIso?: string;
  endedBy?: string;
  scenario?: string;
  transcript?: Array<{ text: string; isUser: boolean; timestamp: number }>;
  scamProbability?: number;
  events?: Array<{
    ts: string;
    type: string;
    actor: string;
    reason_codes?: string[];
    risk_score?: number;
    call_action?: string;
  }>;
  updatedAt: any;
  updatedAtIso?: string;
}

interface DemoAnswerResult {
  accepted: boolean;
  session_id: string;
  state: CallState | string;
  owner_device?: 'web' | 'mobile' | null;
  owner_client_id?: string | null;
  reason?: string;
}

function normalizeSessionId(sessionId?: string | null): string {
  return (sessionId || '').trim();
}

function demoCallStateFingerprint(state: DemoCallDoc | null): string {
  if (!state) {
    return 'null';
  }
  return [
    normalizeSessionId(state.sessionId),
    String(state.state || 'idle'),
    String(state.updatedAtIso || '')
  ].join('|');
}

/**
 * Start a demo call. Primary path uses backend orchestration.
 * Firestore direct write remains as fallback.
 */
export async function startDemoCall(callerName: string = 'Unknown Caller', sessionId?: string): Promise<string> {
  const requestedSessionId = (sessionId ?? `demo_${Date.now()}`).trim();

  try {
    const response = await fetch(`${BACKEND_URL}/call/demo/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: requestedSessionId,
        caller_label: callerName,
        timestamp: new Date().toISOString()
      })
    });

    if (response.ok) {
      const data = await response.json();
      currentDemoSessionId = String(data.session_id || requestedSessionId);
      return currentDemoSessionId;
    }
  } catch (error) {
    console.warn('Backend demo start failed; falling back to Firestore sync.', error);
  }

  if (!(await ensureAnonymousAuth())) {
    throw new Error('Firebase is unavailable for demo call sync.');
  }

  const callDb = getDb();
  if (!callDb) {
    throw new Error('Firestore is unavailable for demo call sync.');
  }
  const callId = requestedSessionId;

  const fakeNumbers = ['+60 11-1234 5678', '+60 3-8888 9999', '+60 12-XXXX XXXX', 'Private Number'];
  const callerNumber = fakeNumbers[Math.floor(Math.random() * fakeNumbers.length)];

  const callDoc: DemoCallDoc = {
    state: 'ringing',
    sessionId: callId,
    callerName,
    callerNumber,
    callerId: callId,
    startTime: serverTimestamp(),
    transcript: [],
    scamProbability: 0,
    updatedAt: serverTimestamp()
  };

  try {
    await setDoc(doc(callDb, 'calls', 'current_demo'), callDoc);
  } catch (error) {
    warnFirestoreIssueOnce(error);
    throw error;
  }

  currentDemoSessionId = callId;
  return callId;
}
/**
 * Update demo call state
 */
export async function updateDemoCallState(state: CallState, additionalData?: Partial<DemoCallDoc>): Promise<void> {
  if (!(await ensureAnonymousAuth())) {
    return;
  }

  const callDb = getDb();
  if (!callDb) {
    return;
  }

  try {
    await setDoc(doc(callDb, 'calls', 'current_demo'), {
      state,
      ...additionalData,
      updatedAt: serverTimestamp()
    }, { merge: true });
  } catch (error) {
    warnFirestoreIssueOnce(error);
    return;
  }
  
  console.log(`📞 Demo call state: ${state}`);
}

/**
 * Update transcript in real-time for Flutter to display
 */
export async function updateDemoTranscript(message: string, isUser: boolean): Promise<void> {
  if (!(await ensureAnonymousAuth())) {
    return;
  }

  const callDb = getDb();
  if (!callDb) {
    return;
  }
  const docRef = doc(callDb, 'calls', 'current_demo');
  
  // Append to transcript array without overwriting existing entries.
  try {
    await setDoc(docRef, {
      transcript: arrayUnion({ text: message, isUser, timestamp: Date.now() }),
      updatedAt: serverTimestamp()
    }, { merge: true });
  } catch (error) {
    warnFirestoreIssueOnce(error);
  }
}

export async function answerDemoCall(
  sessionId: string,
  options: {
    device: 'web' | 'mobile';
    clientId: string;
    answeredByLabel?: string;
  }
): Promise<DemoAnswerResult> {
  const activeSessionId = (sessionId || currentDemoSessionId || '').trim();
  if (!activeSessionId) {
    throw new Error('No active session ID to answer.');
  }
  const response = await fetch(`${BACKEND_URL}/call/demo/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: activeSessionId,
      device: options.device,
      client_id: options.clientId,
      answered_by_label: options.answeredByLabel || null
    })
  });
  const data = await response.json();
  if (response.status === 409 && data?.reason === 'already_answered') {
    return data as DemoAnswerResult;
  }
  if (!response.ok) {
    const message = [data?.error, data?.reason, data?.action].filter(Boolean).join(' ');
    throw new Error(message || `Failed to answer call (${response.status})`);
  }
  currentDemoSessionId = activeSessionId;
  return data as DemoAnswerResult;
}

export async function getDemoCallSession(sessionId: string): Promise<DemoCallDoc | null> {
  const activeSessionId = (sessionId || '').trim();
  if (!activeSessionId) return null;
  const response = await fetch(`${BACKEND_URL}/call/demo/session/${encodeURIComponent(activeSessionId)}`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch call session (${response.status})`);
  }
  return await response.json() as DemoCallDoc;
}

/**
 * End demo call
 */
export async function endDemoCall(
  sessionId?: string,
  reasonCodes: string[] = [],
  options?: { endedBy?: string; device?: 'web' | 'mobile'; clientId?: string; }
): Promise<void> {
  const activeSessionId = (sessionId || currentDemoSessionId || '').trim();
  if (activeSessionId) {
    try {
      const response = await fetch(`${BACKEND_URL}/call/demo/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId,
          ended_by: options?.endedBy || 'web_client',
          device: options?.device || 'web',
          client_id: options?.clientId || getWebClientId(),
          reason_codes: reasonCodes || []
        })
      });
      if (!response.ok) {
        let data: any = null;
        try {
          data = await response.json();
        } catch {
          data = null;
        }
        const message = [data?.error, data?.reason].filter(Boolean).join(' ');
        if (response.status === 403) {
          throw new Error(message || 'Only the owner can end the active call.');
        }
        throw new Error(message || `Failed to end call (${response.status})`);
      }
      if (response.ok) {
        currentDemoSessionId = null;
        return;
      }
    } catch (error) {
      console.warn('Backend demo end failed.', error);
      throw error;
    }
  }

  if (activeSessionId) {
    throw new Error('Unable to end demo call.');
  }
}

/**
 * Listen to demo call state changes (for admin panel)
 */
export function listenToDemoCallState(callback: (state: DemoCallDoc | null) => void): Unsubscribe {
  let firestoreUnsubscribe: Unsubscribe = () => { };
  let pollHandle: ReturnType<typeof setInterval> | null = null;
  let stopped = false;
  let fallbackPollingActive = false;
  let lastFingerprint: string | null = null;

  const emit = (rawState: DemoCallDoc | null): void => {
    if (stopped) {
      return;
    }

    const state = rawState
      ? {
        ...rawState,
        sessionId: normalizeSessionId(rawState.sessionId) || undefined
      }
      : null;

    const sessionId = normalizeSessionId(state?.sessionId);
    if (sessionId) {
      currentDemoSessionId = sessionId;
    }

    const fingerprint = demoCallStateFingerprint(state);
    if (fingerprint === lastFingerprint) {
      return;
    }
    lastFingerprint = fingerprint;
    callback(state);
  };

  const stopPolling = () => {
    if (pollHandle) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  };

  const pollOnce = async () => {
    const activeSessionId = normalizeSessionId(currentDemoSessionId);
    if (!activeSessionId) {
      emit(null);
      return;
    }

    try {
      const state = await getDemoCallSession(activeSessionId);
      if (!state) {
        if (normalizeSessionId(currentDemoSessionId) === activeSessionId) {
          currentDemoSessionId = null;
        }
        emit(null);
        return;
      }
      emit(state);
    } catch (error) {
      console.warn(`Demo call polling failed for session ${activeSessionId}:`, error);
    }
  };

  const startPollingFallback = (reason: string) => {
    if (stopped || fallbackPollingActive) {
      return;
    }
    fallbackPollingActive = true;
    try {
      firestoreUnsubscribe();
    } catch {
      // no-op
    }
    firestoreUnsubscribe = () => { };
    console.warn(`Demo call state sync switched to backend polling (${reason}).`);
    void pollOnce();
    pollHandle = setInterval(() => {
      void pollOnce();
    }, DEMO_CALL_POLL_INTERVAL_MS);
  };

  void ensureAnonymousAuth().then((ready) => {
    if (stopped) {
      return;
    }
    if (!ready) {
      startPollingFallback('firebase_auth_unavailable');
      return;
    }

    const callDb = getDb();
    if (!callDb) {
      startPollingFallback('firebase_not_configured');
      return;
    }

    firestoreUnsubscribe = onSnapshot(
      doc(callDb, 'calls', 'current_demo'),
      (snapshot) => {
        if (snapshot.exists()) {
          emit(snapshot.data() as DemoCallDoc);
        } else {
          emit(null);
        }
      },
      (error) => {
        warnFirestoreIssueOnce(error);
        startPollingFallback('firestore_snapshot_error');
      }
    );
  });

  return () => {
    stopped = true;
    stopPolling();
    try {
      firestoreUnsubscribe();
    } catch {
      // no-op
    }
  };
}

// ==================== QR CODE FAMILY LINKING (Anonymous Auth) ====================

export interface FamilyLinkCode {
  victimId: string;
  code: string;
  expiresAt: number;
  victimName?: string;
}

/**
 * Generate QR code data for family linking
 * Victim shows this QR, Guardian scans it
 */
export async function generateFamilyLinkCode(victimName?: string): Promise<FamilyLinkCode> {
  const authInstance = getAuthInstance();
  if (!authInstance) {
    throw new Error('Firebase auth is unavailable.');
  }
  
  // Sign in anonymously if not already
  let user: User;
  if (!authInstance.currentUser) {
    const credential = await signInAnonymously(authInstance);
    user = credential.user;
    console.log('👤 Anonymous user created:', user.uid);
  } else {
    user = authInstance.currentUser;
  }
  
  const response = await fetch(`${BACKEND_URL}/family/link/code`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      victim_id: user.uid,
      victim_name: victimName || 'Protected User'
    })
  });

  const data = await response.json();
  if (!response.ok) {
    const message = [data.error, data.action].filter(Boolean).join(' ');
    throw new Error(message || 'Failed to generate family link code');
  }

  console.log('🔗 Family link code generated:', data.code);
  return {
    victimId: data.victim_id,
    code: data.code,
    expiresAt: data.expires_at,
    victimName: victimName || 'Protected User'
  };
}

/**
 * Guardian scans QR code to link with victim
 */
export async function linkFamilyByCode(code: string, guardianName?: string): Promise<{ success: boolean; victimId?: string; error?: string }> {
  const authInstance = getAuthInstance();
  if (!authInstance) {
    return { success: false, error: 'Firebase auth is unavailable.' };
  }
  
  // Sign in anonymously as guardian if not already
  let guardianId: string;
  if (!authInstance.currentUser) {
    const credential = await signInAnonymously(authInstance);
    guardianId = credential.user.uid;
  } else {
    guardianId = authInstance.currentUser.uid;
  }
  
  // Look up the link code
  try {
    const response = await fetch(`${BACKEND_URL}/family/link/consume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: code.toUpperCase(),
        guardian_id: guardianId,
        guardian_name: guardianName || 'Family Guardian'
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      console.log('Family linked successfully');
      return { success: true, victimId: data.victim_id };
    } else {
      const message = [data.error, data.action].filter(Boolean).join(' ');
      return { success: false, error: message || 'Failed to link' };
    }
  } catch (error) {
    console.error('❌ Error linking family:', error);
    return { success: false, error: String(error) };
  }
}

/**
 * Get QR code URL for family linking (uses QR code API)
 */
export function getFamilyLinkQRUrl(linkCode: FamilyLinkCode): string {
  const qrData = JSON.stringify({
    type: 'vericall_family_link',
    code: linkCode.code,
    victimId: linkCode.victimId
  });
  
  // Using QR code API service
  return `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(qrData)}`;
}

// ==================== TYPES ====================

export interface ScamReport {
    userId?: string;
    scamType: 'macau_scam' | 'bank_scam' | 'lhdn_scam' | 'love_scam' | 'investment_scam' | 'unknown';
    phoneNumber: string;
    transcript?: string;
    deepfakeScore?: number;
    botProbability?: number;
    location?: string;
}

export interface Evidence {
    reportId: string;
    transcript: string;
    audioUrl?: string;
    evidenceHash: string;
    qualityScore: number;
    keywordsDetected: string[];
    verificationQA?: Array<{ question: string; answer: string }>;
}

export interface ScamStats {
    total: number;
    byType: Record<string, number>;
    last24h: number;
}

export interface FamilyAlertResult {
    sent: number;
    failed: number;
    noToken: number;
}

// ==================== SCAM REPORTS ====================

/**
 * Report a scam to the community database
 * @param report Scam report data
 * @returns Report ID if successful
 */
export async function reportScam(report: ScamReport): Promise<{ success: boolean; reportId?: string; error?: string }> {
    try {
        const response = await fetch(`${BACKEND_URL}/reports`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: report.userId,
                scam_type: report.scamType,
                phone_number: report.phoneNumber,
                transcript: report.transcript,
                deepfake_score: report.deepfakeScore,
                bot_probability: report.botProbability,
                location: report.location
            })
        });

        const data = await response.json();

        if (response.ok && data.success) {
            console.log(`Scam reported: ${data.report_id}`);
            return { success: true, reportId: data.report_id };
        }

        const message = [data.error, data.action].filter(Boolean).join(' ');
        return { success: false, error: message || data.message || 'Failed to report scam' };
    } catch (error) {
        console.error('Error reporting scam:', error);
        return { success: false, error: String(error) };
    }
}

/**
 * Get recent scam reports from community database
 * @param scamType Optional filter by scam type
 * @param limit Maximum number of reports
 */
export async function getRecentScams(
    scamType?: string,
    limit: number = 20
): Promise<ScamReport[]> {
    try {
        let url = `${BACKEND_URL}/reports?limit=${limit}`;
        if (scamType) {
            url += `&type=${scamType}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        return data.reports || [];
    } catch (error) {
        console.error('❌ Error fetching scams:', error);
        return [];
    }
}

/**
 * Get aggregated scam statistics
 */
export async function getScamStats(): Promise<ScamStats> {
    try {
        const response = await fetch(`${BACKEND_URL}/reports/stats`);
        const data = await response.json();

        return {
            total: data.total || 0,
            byType: data.by_type || {},
            last24h: data.last_24h || 0
        };
    } catch (error) {
        console.error('❌ Error fetching stats:', error);
        return { total: 0, byType: {}, last24h: 0 };
    }
}

// ==================== EVIDENCE ====================

/**
 * Save evidence linked to a scam report
 * @param evidence Evidence data
 */
export async function saveEvidence(evidence: Evidence): Promise<{ success: boolean; error?: string }> {
    try {
        const response = await fetch(`${BACKEND_URL}/evidence`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                report_id: evidence.reportId,
                transcript: evidence.transcript,
                audio_url: evidence.audioUrl,
                evidence_hash: evidence.evidenceHash,
                quality_score: evidence.qualityScore,
                keywords_detected: evidence.keywordsDetected,
                verification_qa: evidence.verificationQA
            })
        });

        if (response.ok) {
            console.log('Evidence saved');
            return { success: true };
        }

        const data = await response.json();
        const message = [data.error, data.action].filter(Boolean).join(' ');
        return { success: false, error: message || data.message || 'Failed to save evidence' };
    } catch (error) {
        console.error('Error saving evidence:', error);
        return { success: false, error: String(error) };
    }
}

// ==================== FAMILY ALERTS ====================

/**
 * Send alert to family members when scam detected
 * @param userId Protected user's ID
 * @param scamType Type of scam detected
 * @param riskLevel Risk level (low/medium/high/critical)
 */
export async function sendFamilyAlert(
    userId: string,
    scamType: string,
    riskLevel: 'low' | 'medium' | 'high' | 'critical'
): Promise<FamilyAlertResult> {
    try {
        const response = await fetch(`${BACKEND_URL}/family/alert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                protected_user_id: userId,
                scam_type: scamType,
                risk_level: riskLevel
            })
        });

        const data = await response.json();

        console.log(`📢 Family alert sent: ${data.sent} notifications`);
        return {
            sent: data.sent || 0,
            failed: data.failed || 0,
            noToken: data.no_token || 0
        };
    } catch (error) {
        console.error('❌ Error sending family alert:', error);
        return { sent: 0, failed: 0, noToken: 0 };
    }
}

// ==================== ANALYTICS ====================

/**
 * Track scam pattern for analytics
 * @param patternType Type of scam pattern
 * @param keywords Keywords detected
 */
export async function trackScamPattern(
    patternType: string,
    keywords: string[]
): Promise<void> {
    try {
        await fetch(`${BACKEND_URL}/analytics/pattern`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pattern_type: patternType,
                keywords: keywords
            })
        });
        console.log(`📊 Pattern tracked: ${patternType}`);
    } catch (error) {
        console.error('❌ Error tracking pattern:', error);
    }
}

// ==================== HELPER: Integration with evidenceCollector ====================

/**
 * Auto-report and save evidence when call ends
 * Call this from geminiService.disconnect()
 */
export async function autoReportAndSaveEvidence(
    scamEvidence: {
        callerNumber: string;
        scamType: string;
        transcript: string;
        botProbability: number;
        deepfakeScore: number;
        evidenceHash: string;
        qualityScore: number;
        keywords: string[];
        verificationQA: Array<{ question: string; answer: string }>;
    }
): Promise<{ reportId?: string; success: boolean }> {
    const normalizeScamType = (value: string): ScamReport['scamType'] => {
        const v = value.toLowerCase();
        if (v.includes('macau') || v.includes('police') || v.includes('court')) return 'macau_scam';
        if (v.includes('bank') || v.includes('financial')) return 'bank_scam';
        if (v.includes('lhdn') || v.includes('tax')) return 'lhdn_scam';
        if (v.includes('love') || v.includes('parcel')) return 'love_scam';
        if (v.includes('investment') || v.includes('crypto') || v.includes('forex')) return 'investment_scam';
        return 'unknown';
    };

    // 1. Report the scam
    const reportResult = await reportScam({
        scamType: normalizeScamType(scamEvidence.scamType),
        phoneNumber: scamEvidence.callerNumber,
        transcript: scamEvidence.transcript,
        deepfakeScore: scamEvidence.deepfakeScore,
        botProbability: scamEvidence.botProbability
    });

    if (!reportResult.success || !reportResult.reportId) {
        return { success: false };
    }

    // 2. Save detailed evidence
    await saveEvidence({
        reportId: reportResult.reportId,
        transcript: scamEvidence.transcript,
        evidenceHash: scamEvidence.evidenceHash,
        qualityScore: scamEvidence.qualityScore,
        keywordsDetected: scamEvidence.keywords,
        verificationQA: scamEvidence.verificationQA
    });

    // 3. Track pattern for analytics
    await trackScamPattern(scamEvidence.scamType, scamEvidence.keywords);

    return { reportId: reportResult.reportId, success: true };
}

