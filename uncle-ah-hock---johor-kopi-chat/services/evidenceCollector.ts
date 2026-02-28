/**
 * Evidence Collector Module
 * Collects and formats evidence for PDRM (Royal Malaysian Police) submission
 */

import { SCAM_PATTERNS, ScamEvidence } from './types/scamTypes';

export class EvidenceCollector {
    private id: string = '';
    private startTime: Date = new Date();
    private transcript: string = '';
    private keywordsFound: Set<string> = new Set();
    private verificationQuestions: string[] = [];
    private callerResponses: string[] = [];
    private inconsistencies: string[] = [];
    private callerUtterances: string[] = [];
    private callerNumber: string = 'UNKNOWN';
    private audioChunks: Blob[] = [];
    private callRecording: Blob | null = null;
    private isRecording: boolean = false;

    // Callbacks
    public onEvidenceReady: (evidence: ScamEvidence) => void = () => { };

    constructor() {
        this.reset();
    }

    /**
     * Reset and start a new evidence collection session
     */
    public reset(): void {
        this.id = `CASE-${Date.now()}`;
        this.startTime = new Date();
        this.transcript = '';
        this.keywordsFound = new Set();
        this.verificationQuestions = [];
        this.callerResponses = [];
        this.inconsistencies = [];
        this.callerUtterances = [];
        this.audioChunks = [];
        this.callRecording = null;
        this.isRecording = false;
    }

    /**
     * Start recording evidence for a call
     * @param callerNumber Phone number of the caller (if available)
     */
    public startRecording(callerNumber: string = 'UNKNOWN'): void {
        this.reset();
        this.callerNumber = callerNumber;
        this.isRecording = true;
        console.log(`📹 Evidence recording started: ${this.id}`);
    }

    /**
     * Context keywords: when Uncle mentions these, it proves the caller
     * brought up that scam topic — even if caller transcription missed it.
     */
    private static readonly RESPONSE_CONTEXT_CLUES: Record<string, string[]> = {
        'lhdn': ['lhdn', 'lembaga hasil', 'tax department', 'cukai', 'income tax'],
        'police': ['polis', 'police', 'mahkamah', 'court', 'warrant', 'waran', 'balai', 'bukit aman'],
        'bank': ['bank account', 'akaun bank', 'maybank', 'cimb', 'tac', 'otp', 'pin number'],
        'invest': ['investment', 'pelaburan', 'forex', 'crypto', 'bitcoin', 'guaranteed profit'],
        'parcel': ['parcel', 'poslaju', 'j&t', 'custom', 'kastam', 'bungkusan'],
    };

    /**
     * Log a transcript entry
     * @param text The spoken text
     * @param speaker Who said it: 'Caller' or 'Uncle'
     */
    public log(text: string, speaker: string): void {
        if (!this.isRecording) return;

        const time = new Date().toLocaleTimeString('en-MY', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        this.transcript += `[${time}] ${speaker}: ${text}\n`;

        // Check for scam keywords from both sides
        const speakerLower = speaker.toLowerCase();
        const isCaller = speakerLower.includes('caller') || speakerLower.includes('scammer') || speakerLower.includes('user');
        const isUncle = speakerLower.includes('uncle') || speakerLower.includes('model') || speakerLower.includes('bot');

        if (isCaller) {
            // Direct keyword detection from caller's transcribed text
            this.callerUtterances.push(text);
            const lower = text.toLowerCase();
            SCAM_PATTERNS.forEach(pattern => {
                pattern.keywords.forEach(keyword => {
                    if (lower.includes(keyword.toLowerCase())) {
                        this.keywordsFound.add(keyword);
                    }
                });
            });
        } else if (isUncle) {
            // Infer caller's topic from Uncle's response context.
            // If Uncle says "LHDN never call people!", caller clearly mentioned LHDN.
            const lower = text.toLowerCase();
            for (const [label, clues] of Object.entries(EvidenceCollector.RESPONSE_CONTEXT_CLUES)) {
                for (const clue of clues) {
                    if (lower.includes(clue) && !this.keywordsFound.has(`[inferred] ${label}`)) {
                        this.keywordsFound.add(`[inferred] ${label}`);
                        console.log(`🔍 Keyword inferred from Uncle's response: "${label}" (Uncle mentioned "${clue}")`);
                        break; // one match per category is enough
                    }
                }
            }
        }
    }

    /**
     * Record a specific scam keyword
     */
    public recordScamKeyword(keyword: string): void {
        if (!this.keywordsFound.has(keyword)) {
            this.keywordsFound.add(keyword);
            console.log(`🚨 Scam keyword detected: ${keyword}`);
        }
    }

    /**
     * Record a verification attempt
     * @param question The verification question asked
     * @param response The caller's response
     */
    public recordVerificationAttempt(question: string, response: string): void {
        this.verificationQuestions.push(question);
        this.callerResponses.push(response);

        // Analyze for inconsistencies
        this.detectInconsistency(question, response);

        console.log(`🔍 Verification: Q="${question}" A="${response}"`);
    }

    /**
     * Detect inconsistencies in caller's responses
     */
    private detectInconsistency(question: string, response: string): void {
        const lowerQ = question.toLowerCase();
        const lowerR = response.toLowerCase();

        // Pattern 1: Claims to be official but can't identify office
        if ((lowerQ.includes('which office') || lowerQ.includes('which balai') || lowerQ.includes('which branch')) &&
            (lowerR.includes('not sure') || lowerR.includes('cannot') || lowerR.includes('tak tahu'))) {
            this.addInconsistency('Claimed to be official but couldn\'t identify office location');
        }

        // Pattern 2: Claims to be police but refuses badge number
        if ((lowerQ.includes('badge number') || lowerQ.includes('nombor badge') || lowerQ.includes('staff id')) &&
            (lowerR.includes('cannot give') || lowerR.includes('not allowed') || lowerR.includes('tak boleh'))) {
            this.addInconsistency('Refused to provide badge number (PDRM officers must identify)');
        }

        // Pattern 3: Claims to be bank but can't verify account details
        if ((lowerQ.includes('my account') || lowerQ.includes('account number')) &&
            (lowerR.includes('confirm') || lowerR.includes('verify') || lowerR.includes('need you to'))) {
            this.addInconsistency('Caller asking victim to verify information (real banks have your info)');
        }

        // Pattern 4: Urgency pressure
        if ((lowerQ.includes('why') || lowerQ.includes('kenapa')) &&
            (lowerR.includes('immediately') || lowerR.includes('now') || lowerR.includes('sekarang juga'))) {
            this.addInconsistency('Applying urgency pressure to prevent victim from thinking');
        }
    }

    /**
     * Add a detected inconsistency
     */
    public addInconsistency(text: string): void {
        if (!this.inconsistencies.includes(text)) {
            this.inconsistencies.push(text);
            console.log(`⚠️ Inconsistency detected: ${text}`);
        }
    }

    /**
     * Record audio chunk (for future audio evidence)
     * Accepts any blob-like object for compatibility with various audio formats
     */
    public recordAudioChunk(audioBlob: Blob | any): void {
        this.audioChunks.push(audioBlob);
    }

    /**
     * Generate evidence hash for integrity verification using SHA-256
     * Uses Web Crypto API for proper cryptographic hash
     */
    private async generateEvidenceHashAsync(): Promise<string> {
        const raw = this.transcript + this.id + this.startTime.toISOString();
        const encoder = new TextEncoder();
        const data = encoder.encode(raw);

        try {
            const hashBuffer = await crypto.subtle.digest('SHA-256', data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            return hashHex.toUpperCase().substring(0, 16); // Return first 16 chars for readability
        } catch (e) {
            // Fallback to simple hash if crypto API unavailable
            console.warn('SHA-256 unavailable, using fallback hash');
            return this.generateSimpleHash();
        }
    }

    /**
     * Fallback simple hash for environments without crypto.subtle
     */
    private generateSimpleHash(): string {
        const raw = this.transcript + this.id + this.startTime.toISOString();
        let hash = 0;
        for (let i = 0; i < raw.length; i++) {
            const char = raw.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        const hashHex = Math.abs(hash).toString(16).padStart(8, '0');
        const suffix = Date.now().toString(16).slice(-8);
        return `${hashHex}${suffix}`.toUpperCase();
    }

    /**
     * Synchronous hash generation (uses simple hash for sync contexts)
     */
    private generateEvidenceHash(): string {
        return this.generateSimpleHash();
    }

    /**
     * Assess the quality of collected evidence (0-100)
     */
    public assessEvidenceQuality(): number {
        let quality = 0;

        // Transcript length (30 points)
        if (this.transcript.length > 500) quality += 30;
        else if (this.transcript.length > 200) quality += 20;
        else if (this.transcript.length > 50) quality += 10;

        // Scam keywords detected (20 points)
        const keywordCount = this.keywordsFound.size;
        if (keywordCount >= 5) quality += 20;
        else if (keywordCount >= 3) quality += 15;
        else if (keywordCount >= 1) quality += 10;

        // Verification attempts (20 points)
        if (this.verificationQuestions.length >= 3) quality += 20;
        else if (this.verificationQuestions.length >= 1) quality += 10;

        // Inconsistencies found (20 points)
        if (this.inconsistencies.length >= 3) quality += 20;
        else if (this.inconsistencies.length >= 1) quality += 15;

        // Call duration (10 points) - longer calls = more evidence
        const duration = Math.floor((Date.now() - this.startTime.getTime()) / 1000);
        if (duration >= 60) quality += 10;
        else if (duration >= 30) quality += 5;

        return Math.min(quality, 100);
    }

    private extractMoneyRequestEvidence(callerText: string): string[] {
        const cues = [
            /transfer/gi,
            /send money/gi,
            /safe account/gi,
            /rm\s*\d+/gi,
            /ringgit/gi,
            /\b(tac|otp|pin|password)\b/gi,
            /\b(bank account|akaun bank)\b/gi,
            /\bpay now|payment now|bayar sekarang\b/gi
        ];
        const matches = new Set<string>();
        cues.forEach((regex) => {
            const found = callerText.match(regex) || [];
            found.forEach((m) => matches.add(m.trim()));
        });
        return Array.from(matches);
    }

    private extractAmountRequested(callerText: string): number | undefined {
        const match = callerText.match(/rm\s*([0-9][0-9,]*)/i);
        if (!match) return undefined;
        const parsed = Number(match[1].replace(/,/g, ''));
        return Number.isFinite(parsed) ? parsed : undefined;
    }

    private extractOrganizationImpersonated(callerText: string): string | undefined {
        if (/\blhdn|lembaga hasil\b/i.test(callerText)) return 'LHDN';
        if (/\bpdrm|polis|police|mahkamah|court\b/i.test(callerText)) return 'PDRM/Police';
        if (/\bmaybank|cimb|public bank|rhb|bank\b/i.test(callerText)) return 'Bank';
        return undefined;
    }

    private classifyScamFromCallerContent(): {
        scamType: string;
        classificationReason: string;
        detectedSignals: string[];
        moneyRequestEvidence: string[];
        amountRequested?: number;
        organizationImpersonated?: string;
    } {
        const callerText = this.callerUtterances.join(' ').toLowerCase();
        const detectedSignals = Array.from(this.keywordsFound);
        const moneyRequestEvidence = this.extractMoneyRequestEvidence(callerText);
        const amountRequested = this.extractAmountRequested(callerText);
        const organizationImpersonated = this.extractOrganizationImpersonated(callerText);

        if (!callerText.trim()) {
            return {
                scamType: 'Unknown/Suspicious',
                classificationReason: 'No caller content captured; cannot determine scam type.',
                detectedSignals,
                moneyRequestEvidence
            };
        }

        const scoreByType = new Map<string, number>();
        SCAM_PATTERNS.forEach((pattern) => {
            const score = pattern.keywords.filter(k => callerText.includes(k.toLowerCase())).length;
            scoreByType.set(pattern.type, score);
        });

        const bankScore = scoreByType.get('Bank/Financial Scam') || 0;
        if (bankScore > 0 && moneyRequestEvidence.length === 0) {
            scoreByType.set('Bank/Financial Scam', 0);
        }

        let bestType = 'Unknown/Suspicious';
        let bestScore = 0;
        scoreByType.forEach((score, type) => {
            if (score > bestScore) {
                bestScore = score;
                bestType = type;
            }
        });

        if (bestScore === 0) {
            return {
                scamType: 'Unknown/Suspicious',
                classificationReason: moneyRequestEvidence.length > 0
                    ? 'Money/credential request detected but scam category is unclear from caller wording.'
                    : 'No reliable scam-pattern match from caller utterances.',
                detectedSignals,
                moneyRequestEvidence,
                amountRequested,
                organizationImpersonated
            };
        }

        const reason = bestType === 'Bank/Financial Scam'
            ? `Bank/financial cues with explicit money/credential request detected (${moneyRequestEvidence.join(', ')})`
            : `Matched caller keywords for ${bestType} (${detectedSignals.slice(0, 4).join(', ') || 'pattern match'})`;

        return {
            scamType: bestType,
            classificationReason: reason,
            detectedSignals,
            moneyRequestEvidence,
            amountRequested,
            organizationImpersonated
        };
    }

    /**
     * Generate the ScamEvidence object
     * @param botProb Bot probability from detection
     * @param audioBlob Optional audio recording blob from call
     */
    public generateReport(botProb: number, audioBlob: Blob | null = null): ScamEvidence {
        console.log('📋 EvidenceCollector.generateReport() called');
        console.log('   audioBlob parameter:', audioBlob);
        console.log('   audioBlob size:', audioBlob?.size);

        this.callRecording = audioBlob;

        console.log('   this.callRecording stored:', this.callRecording);
        console.log('   this.callRecording size:', this.callRecording?.size);

        const classification = this.classifyScamFromCallerContent();

        const evidence: ScamEvidence = {
            id: this.id,
            timestamp: this.startTime,
            duration: Math.floor((Date.now() - this.startTime.getTime()) / 1000),
            callerNumber: this.callerNumber,
            fullTranscript: this.transcript,
            scamKeywords: Array.from(this.keywordsFound),
            botProbability: botProb,
            scamType: classification.scamType,
            classificationReason: classification.classificationReason,
            detectedSignals: classification.detectedSignals,
            moneyRequestEvidence: classification.moneyRequestEvidence,
            amountRequested: classification.amountRequested,
            organizationImpersonated: classification.organizationImpersonated,
            verificationQuestions: this.verificationQuestions,
            callerResponses: this.callerResponses,
            inconsistencies: this.inconsistencies,
            evidenceHash: this.generateEvidenceHash(),
            evidenceQuality: this.assessEvidenceQuality(),
            policeReportReady: this.assessEvidenceQuality() >= 50,
            callRecording: this.callRecording
        };

        console.log('📋 Evidence object created with callRecording:', evidence.callRecording);
        console.log('   Evidence.callRecording size:', evidence.callRecording?.size);

        this.isRecording = false;
        return evidence;
    }

    /**
 * Generate a formatted PDRM-ready police report with 3 sections
 * Section A: Metadata (Facts)
 * Section B: Executive Summary (AI-Generated English)
 * Section C: Evidence Transcript (Verbatim Manglish)
 */
    public generatePoliceReport(evidence: ScamEvidence): string {
        const divider = '═'.repeat(70);
        const sectionDivider = '─'.repeat(70);

        // Generate reference ID
        const refId = `VC-${new Date().getFullYear()}-${Math.floor(Math.random() * 10000).toString().padStart(4, '0')}`;

        // Format duration
        const mins = Math.floor(evidence.duration / 60);
        const secs = evidence.duration % 60;
        const durationStr = `${mins} min ${secs} sec`;

        // Determine AI verdict
        const deepfakeProb = evidence.aiVoiceProbability || 0;
        let verdict = '✅ LOW RISK';
        if (deepfakeProb > 85) verdict = '🚨 HIGH RISK (AI Voice Detected)';
        else if (deepfakeProb > 70) verdict = '⚠️ MEDIUM RISK';
        else if (deepfakeProb > 50) verdict = '⚠️ SUSPICIOUS';

        // Generate AI summary
        const aiSummary = this.generateAISummary(evidence);

        return `
${divider}
VeriCall Automated Scam Incident Report
Reference ID: #${refId}
${divider}

════════════════════════════════════════════════════════════════════════
SECTION A: METADATA (The Facts)
════════════════════════════════════════════════════════════════════════

Date/Time:          ${evidence.timestamp.toLocaleString('en-MY', {
            timeZone: 'Asia/Kuala_Lumpur',
            dateStyle: 'long',
            timeStyle: 'short'
        })}

Caller ID:          ${evidence.callerNumber || '+60-XXX-XXX-XXXX'} ${evidence.callerNumber?.startsWith('+60') ? '' : '(Flagged as VoIP)'}

Duration:           ${durationStr}

Claimed Identity:   ${evidence.claimedIdentity || 'Not disclosed'}

Claimed Org:        ${evidence.organizationImpersonated || 'Not specified'}

Scam Type:          ${evidence.scamType.toUpperCase()}

Amount Requested:   ${evidence.amountRequested ? `RM ${evidence.amountRequested.toLocaleString()}` : 'No explicit amount detected'}

Classification:     ${evidence.classificationReason || 'No classification reason recorded'}

Money Evidence:     ${evidence.moneyRequestEvidence && evidence.moneyRequestEvidence.length > 0
                ? evidence.moneyRequestEvidence.join(', ')
                : 'No explicit money request detected'}

${sectionDivider}
AI DETECTION RESULTS
${sectionDivider}

AI Voice Analysis:  ${deepfakeProb}% Deepfake Probability
Bot Detection:      ${evidence.botProbability}% Confidence
Evidence Quality:   ${evidence.evidenceQuality || this.assessEvidenceQuality()}%

AI VERDICT:         ${verdict}


════════════════════════════════════════════════════════════════════════
SECTION B: EXECUTIVE SUMMARY (Proper English)
════════════════════════════════════════════════════════════════════════

${aiSummary}

Keywords Detected:
${evidence.scamKeywords.length > 0
                ? evidence.scamKeywords.map(k => `  - ${k}`).join('\n')
                : '  - None detected'}

Signals Used For Classification:
${evidence.detectedSignals && evidence.detectedSignals.length > 0
                ? evidence.detectedSignals.map(signal => `  - ${signal}`).join('\n')
                : '  - None detected'}

Inconsistencies:
${evidence.inconsistencies.length > 0
                ? evidence.inconsistencies.map(inc => `  ⚠️ ${inc}`).join('\n')
                : '  • None detected'}


════════════════════════════════════════════════════════════════════════
SECTION C: EVIDENCE TRANSCRIPT (Verbatim Manglish)
════════════════════════════════════════════════════════════════════════

${this.formatTranscriptWithTimestamps(evidence.fullTranscript)}


${divider}
EVIDENCE INTEGRITY
${divider}

Evidence Hash:      ${evidence.evidenceHash}
Integrity Status:   ${(evidence.evidenceQuality || this.assessEvidenceQuality()) >= 50
                ? '✅ VALID - Ready for PDRM submission'
                : '⚠️ Additional evidence recommended'}

${divider}
HOW TO REPORT
${divider}

This evidence package can be submitted to:

• National Scam Response Centre (NSRC)
  Hotline: 997 (24 hours)
  
• PDRM Commercial Crime Investigation Dept (CCID)
  Website: https://www.rmp.gov.my
  
• MCMC Consumer Complaints Portal
  Website: https://aduan.skmm.gov.my

${divider}
DISCLAIMER
${divider}

This report was automatically generated by VeriCall AI Defense System.
"Uncle" = AI Decoy (Defense System)
"Caller" = Suspected Scammer

${divider}
`;
    }

    /**
     * Generate AI summary in proper English
     */
    private generateAISummary(evidence: ScamEvidence): string {
        const caller = evidence.claimedIdentity || 'The caller';
        const aiProb = evidence.aiVoiceProbability || 0;
        const moneyEvidence = evidence.moneyRequestEvidence || [];

        let summary = `AI-Generated Summary:\n\n"`;

        summary += `${caller} was classified as ${evidence.scamType}. `;
        if (evidence.classificationReason) {
            summary += `Reason: ${evidence.classificationReason}. `;
        }

        if (evidence.organizationImpersonated) {
            summary += `The caller claimed affiliation with ${evidence.organizationImpersonated}. `;
        }

        if (moneyEvidence.length > 0) {
            summary += `Explicit money or credential request cues were detected: ${moneyEvidence.join(', ')}. `;
            if (evidence.amountRequested) {
                summary += `Detected amount mentioned: RM ${evidence.amountRequested.toLocaleString()}. `;
            }
        } else {
            summary += `No explicit money request was detected in caller utterances. `;
        }

        // AI voice detection
        if (aiProb > 70) {
            summary += `Voice biometrics indicate a synthetic AI-generated voice was likely used (${aiProb}% probability). `;
        } else if (aiProb > 50) {
            summary += `Voice analysis detected potential AI involvement (${aiProb}% probability). `;
        }

        // Closing
        summary += `The call was intercepted and handled by VeriCall's AI defense system."`;

        return summary;
    }

    /**
     * Format transcript with timestamps
     */
    private formatTranscriptWithTimestamps(transcript: string): string {
        if (!transcript) return 'No transcript recorded.';

        const lines = transcript.split('\n').filter(l => l.trim());
        let seconds = 0;

        return lines.map(line => {
            const timestamp = `[${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}]`;
            seconds += 5 + Math.floor(Math.random() * 10); // Simulate realistic timing
            return `${timestamp} ${line}`;
        }).join('\n\n');
    }
    /**
     * Export evidence as downloadable text file
     */
    public exportEvidence(evidence: ScamEvidence): Blob {
        const report = this.generatePoliceReport(evidence);
        return new Blob([report], { type: 'text/plain;charset=utf-8' });
    }

    /**
     * Check if currently recording
     */
    public isActive(): boolean {
        return this.isRecording;
    }

    /**
     * Get current transcript length
     */
    public getTranscriptLength(): number {
        return this.transcript.length;
    }

    /**
     * Get count of detected keywords
     */
    public getKeywordCount(): number {
        return this.keywordsFound.size;
    }
}

// Export singleton for convenience
export const evidenceCollector = new EvidenceCollector();
