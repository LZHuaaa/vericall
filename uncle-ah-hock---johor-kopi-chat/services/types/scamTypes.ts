/**
 * Scam Types Module
 * Shared interfaces and constants for the Uncle Ah Hock AI Defense System
 */

// ==================== INTERFACES ====================

/**
 * Scam pattern definition for detection and counter-attack
 */
export interface ScamPattern {
    type: string;
    keywords: string[];
    urgency: 'low' | 'medium' | 'high' | 'critical';
    attackScript: string;
}

/**
 * Call metrics for bot detection
 */
export interface CallMetrics {
    silenceDuration: number;         // How long caller stays silent (ms)
    firstSpeaker: 'caller' | 'user' | 'neither';
    callerResponseDelay: number;     // Delay between user speaking and caller response
    backgroundNoise: number;         // Presence of natural background noise (0-1)
    voiceConsistency: number;        // How consistent voice characteristics are (0-1)
}

/**
 * Bot detection status result
 */
export interface BotDetectionStatus {
    isSuspicious: boolean;
    reason: string;
    prob: number;
    recommendation?: string;
}

/**
 * Full scam evidence for PDRM submission
 */
export interface ScamEvidence {
    // Case identification
    id: string;
    timestamp: Date;
    duration: number;

    // Call details
    callerNumber?: string;

    // Content evidence
    fullTranscript: string;
    scamKeywords: string[];
    claimedIdentity?: string;

    // Technical evidence
    botProbability: number;
    aiVoiceProbability?: number;
    backgroundNoiseProfile?: number;

    // Scam classification
    scamType: string;
    organizationImpersonated?: string;
    amountRequested?: number;
    classificationReason?: string;
    detectedSignals?: string[];
    moneyRequestEvidence?: string[];

    // Verification attempts
    verificationQuestions: string[];
    callerResponses: string[];
    inconsistencies: string[];

    // Evidence integrity
    evidenceHash: string;
    evidenceQuality?: number;
    policeReportReady?: boolean;
    callRecording?: Blob | null;
}

/**
 * Log message for UI display
 */
export interface LogMessage {
    id: string;
    sender: 'user' | 'uncle';
    text: string;
    timestamp: Date;
}

export type ThreatRiskLevel = 'safe' | 'low' | 'medium' | 'high' | 'critical';

export interface ThreatSignal {
    name: string;
    score: number;
    confidence: number;
    active: boolean;
    details?: string;
}

export interface ThreatEvidenceItem {
    source: string;
    source_tier: number;
    title: string;
    summary: string;
    url?: string;
    supports_risk: boolean;
    timestamp?: string;
}

export interface ThreatAssessment {
    risk_level: ThreatRiskLevel;
    risk_score: number;
    confidence: number;
    reason_codes: string[];
    recommended_actions: string[];
    evidence_items: ThreatEvidenceItem[];
    retrieval_status: string;
    signals: ThreatSignal[];
    mode: 'normal' | 'degraded_local';
    version: string;
    call_action?: 'none' | 'warn' | 'challenge' | 'hangup';
    call_action_confidence?: number;
    call_action_reason_codes?: string[];
    hangup_after_ms?: number | null;
    timestamp?: string;
}

/**
 * Connection state enum
 */
export enum ConnectionState {
    DISCONNECTED = 'DISCONNECTED',
    CONNECTING = 'CONNECTING',
    CONNECTED = 'CONNECTED',
    ERROR = 'ERROR',
}

/**
 * Audio visualizer props
 */
export interface AudioVisualizerProps {
    isSpeaking: boolean;
    volume: number;
    color?: string;
}

// ==================== SCAM PATTERNS DATABASE ====================

export const SCAM_PATTERNS: ScamPattern[] = [
    {
        type: 'Macau Scam (Impersonation)',
        keywords: ['warrant', 'arrest', 'police', 'court', 'tangkap', 'mahkamah', 'pdrm', 'bukit aman', 'waran'],
        urgency: 'critical',
        attackScript: 'Which balai you calling from? I know OCPD there. You give me your badge number NOW!'
    },
    {
        type: 'Bank/Financial Scam',
        keywords: ['tac', 'otp', 'pin', 'transfer', 'bank account', 'blocked', 'suspended', 'transaction', 'password'],
        urgency: 'critical',
        attackScript: 'My account empty one! Only got RM10. You want to steal RM10 ah? Kesian you.'
    },
    {
        type: 'LHDN/Tax Scam',
        keywords: ['lhdn', 'cukai', 'tax', 'refund', 'rebate', 'outstanding', 'arrears'],
        urgency: 'high',
        attackScript: 'LHDN never call people one! They send letter only. You scammer right?'
    },
    {
        type: 'Love/Parcel Scam',
        keywords: ['parcel', 'custom', 'stuck', 'overseas', 'gift', 'package', 'courier'],
        urgency: 'medium',
        attackScript: 'You love me send me money lah. Why I pay custom tax for you?'
    },
    {
        type: 'Investment Scam',
        keywords: ['investment', 'guaranteed', 'profit', 'forex', 'crypto', 'bitcoin', 'return'],
        urgency: 'high',
        attackScript: 'Guaranteed profit? No such thing! Warren Buffett also cannot guarantee. You scammer!'
    }
];

// ==================== KEYWORD SCORING WEIGHTS ====================

export const SCAM_SCORING = {
    critical: {
        keywords: ['warrant', 'arrest', 'tangkap', 'waran', 'tac', 'otp', 'pin', 'password', 'transfer now', 'urgent', 'immediately'],
        points: 20
    },
    highRisk: {
        keywords: ['lhdn', 'police', 'bank', 'account', 'blocked', 'suspended', 'investigation', 'fraud'],
        points: 10
    },
    urgency: {
        keywords: ['now', 'today', 'sekarang', 'segera', 'must', 'immediately', 'urgent'],
        points: 5
    },
    threats: {
        keywords: ['arrest', 'jail', 'court', 'legal action', 'lawsuit', 'prison', 'penjara'],
        points: 15
    },
    moneyPattern: /rm\s*\d+|ringgit|thousand|ribu|juta|million/gi,
    moneyPoints: 15
};

// ==================== PHONETICS FOR MANGLISH ====================

export const PHONETICS = `
- "Already" -> "O-red-di"
- "Correct" -> "Ko-rek"
- "Brother" -> "Brudder"
- "Like that" -> "Lid-dat"
- "Don't" -> "Dun"
- "What" -> "Wot"
- "Think" -> "Ting"
- "The" -> "De"
- "Police" -> "Po-lees"
- "Bank" -> "Beng"
- "Problem" -> "Pro-blem"
- "Transfer" -> "Trens-fer"
- "Aiyo" -> "Ai-yoh"
- "Walao" -> "Wa-lau"
`;
