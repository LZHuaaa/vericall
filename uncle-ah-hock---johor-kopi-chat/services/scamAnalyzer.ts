/**
 * Scam Analyzer Module
 * Real-time scam detection and probability calculation with adaptive tone system
 */

import { SCAM_PATTERNS, SCAM_SCORING, ScamPattern } from './types/scamTypes';

/**
 * Tone levels for adaptive response
 */
export enum ToneLevel {
    FRIENDLY = 'FRIENDLY',    // 0-30% probability
    CAUTIOUS = 'CAUTIOUS',    // 31-60% probability
    AGGRESSIVE = 'AGGRESSIVE' // 61-100% probability
}

export class ScamAnalyzer {
    private scamProbability: number = 0;
    private detectedScamType: string | null = null;
    private conversationContext: string[] = [];
    private detectedPatterns: Set<string> = new Set();
    private currentToneLevel: ToneLevel = ToneLevel.FRIENDLY;

    // Callbacks
    public onScamProbabilityChange: (prob: number) => void = () => { };
    public onScamPatternDetected: (pattern: string, urgency: string) => void = () => { };
    public onCriticalThreatDetected: (pattern: ScamPattern) => void = () => { };
    public onToneLevelChange: (tone: ToneLevel, reason: string) => void = () => { };

    constructor() {
        this.reset();
    }

    /**
     * Reset analyzer for a new call
     */
    public reset(): void {
        this.scamProbability = 0;
        this.detectedScamType = null;
        this.conversationContext = [];
        this.detectedPatterns = new Set();
        this.currentToneLevel = ToneLevel.FRIENDLY;
    }

    /**
     * Add text to conversation context and analyze
     * @param text New text from the conversation
     * @returns The updated scam probability
     */
    public analyzeText(text: string): number {
        this.conversationContext.push(text);

        const fullTranscript = this.conversationContext.join(' ');

        // Calculate probability
        const previousProb = this.scamProbability;
        this.scamProbability = this.calculateScamProbability(fullTranscript);
        this.onScamProbabilityChange(this.scamProbability);

        // Update tone level based on probability
        this.updateToneLevel();

        // Detect patterns
        const pattern = this.detectScamPattern(fullTranscript);
        if (pattern && !this.detectedPatterns.has(pattern.type)) {
            this.detectedPatterns.add(pattern.type);
            this.detectedScamType = pattern.type;
            this.onScamPatternDetected(pattern.type, pattern.urgency);

            // Trigger critical threat callback for immediate response
            if (pattern.urgency === 'critical') {
                this.onCriticalThreatDetected(pattern);
            }
        }

        return this.scamProbability;
    }

    /**
     * Update tone level based on current scam probability
     */
    private updateToneLevel(): void {
        const previousTone = this.currentToneLevel;
        let newTone: ToneLevel;
        let reason: string;

        if (this.scamProbability <= 30) {
            newTone = ToneLevel.FRIENDLY;
            reason = 'Normal conversation, no suspicious indicators';
        } else if (this.scamProbability <= 60) {
            newTone = ToneLevel.CAUTIOUS;
            reason = `Suspicious keywords detected (${this.scamProbability}% probability)`;
        } else {
            newTone = ToneLevel.AGGRESSIVE;
            reason = `High scam probability (${this.scamProbability}%) - Attack mode!`;
        }

        if (newTone !== previousTone) {
            this.currentToneLevel = newTone;
            console.log(`🎭 Tone Level: ${previousTone} → ${newTone}`);
            this.onToneLevelChange(newTone, reason);
        }
    }

    /**
     * Get current tone level
     */
    public getToneLevel(): ToneLevel {
        return this.currentToneLevel;
    }

    /**
     * Calculate scam probability with weighted scoring
     * @param transcript Full conversation transcript
     * @returns Probability 0-100
     */
    public calculateScamProbability(transcript: string): number {
        let score = 0;
        const lowerText = transcript.toLowerCase();

        // Critical keywords (20 points each)
        SCAM_SCORING.critical.keywords.forEach(keyword => {
            if (lowerText.includes(keyword.toLowerCase())) {
                score += SCAM_SCORING.critical.points;
            }
        });

        // High-risk keywords (10 points each)
        SCAM_SCORING.highRisk.keywords.forEach(keyword => {
            if (lowerText.includes(keyword.toLowerCase())) {
                score += SCAM_SCORING.highRisk.points;
            }
        });

        // Urgency indicators (5 points each)
        SCAM_SCORING.urgency.keywords.forEach(keyword => {
            if (lowerText.includes(keyword.toLowerCase())) {
                score += SCAM_SCORING.urgency.points;
            }
        });

        // Threat indicators (15 points each)
        SCAM_SCORING.threats.keywords.forEach(keyword => {
            if (lowerText.includes(keyword.toLowerCase())) {
                score += SCAM_SCORING.threats.points;
            }
        });

        // Money mentions (15 points each match)
        const moneyMatches = lowerText.match(SCAM_SCORING.moneyPattern);
        if (moneyMatches) {
            score += moneyMatches.length * SCAM_SCORING.moneyPoints;
        }

        // Additional pattern-based scoring with CONTEXT CHECKING to reduce false positives
        
        // Identity verification requests (red flag) - but only if demanding, not asking
        const hasVerifyDemand = (lowerText.includes('verify') && (lowerText.includes('ic') || lowerText.includes('identity'))) &&
                                (lowerText.includes('must') || lowerText.includes('need to') || lowerText.includes('have to'));
        if (hasVerifyDemand) {
            score += 15;
        }

        // Callback requests (red flag) - ONLY if combined with urgency or authority claim
        const hasUrgentCallback = (lowerText.includes('call back') || lowerText.includes('callback')) &&
                                  (lowerText.includes('immediately') || lowerText.includes('now') || 
                                   lowerText.includes('police') || lowerText.includes('bank'));
        if (hasUrgentCallback) {
            score += 10;
        }

        // Secrecy requests (major red flag) - CONFIRMED HIGH RISK
        if (lowerText.includes('don\'t tell') || lowerText.includes('jangan beritahu') || 
            lowerText.includes('keep secret') || lowerText.includes('cannot tell anyone')) {
            score += 20;
        }

        // REDUCE SCORE if conversation seems helpful/legitimate:
        // - Asking questions (not demanding)
        // - Offers to help
        // - Polite language
        const legitimateIndicators = [
            lowerText.includes('can i help'),
            lowerText.includes('how can i'),
            lowerText.includes('may i ask'),
            lowerText.includes('thank you'),
            lowerText.includes('please'),
            (lowerText.match(/\?/g) || []).length > 3 // Multiple questions = engagement
        ].filter(Boolean).length;

        if (legitimateIndicators >= 2) {
            score = Math.max(0, score - 15); // Reduce score for polite, helpful conversation
            console.log('🔍 Scam Analyzer: Legitimate indicators detected, reducing score by 15 points');
        }

        return Math.min(score, 100); // Cap at 100%
    }

    /**
     * Detect which scam pattern matches the transcript
     * @param transcript Full conversation transcript
     * @returns Matching scam pattern or null
     */
    public detectScamPattern(transcript: string): ScamPattern | null {
        const lowerText = transcript.toLowerCase();

        for (const pattern of SCAM_PATTERNS) {
            const matchCount = pattern.keywords.filter(keyword =>
                lowerText.includes(keyword.toLowerCase())
            ).length;

            // If 2+ keywords match, it's a pattern
            if (matchCount >= 2) {
                return pattern;
            }
        }

        return null;
    }

    /**
     * Get attack script for a detected pattern
     * @param patternType The type of scam pattern
     * @returns Counter-attack script
     */
    public getAttackScript(patternType: string): string {
        const pattern = SCAM_PATTERNS.find(p => p.type === patternType);
        return pattern?.attackScript || 'Eh, you sound suspicious. Let me record this call first!';
    }

    /**
     * Get all attack scripts organized by urgency
     */
    public getAllAttackScripts(): Record<string, { pattern: string; script: string; }[]> {
        const byUrgency: Record<string, { pattern: string; script: string; }[]> = {
            critical: [],
            high: [],
            medium: [],
            low: []
        };

        SCAM_PATTERNS.forEach(pattern => {
            byUrgency[pattern.urgency].push({
                pattern: pattern.type,
                script: pattern.attackScript
            });
        });

        return byUrgency;
    }

    /**
     * Generate system alert instruction for AI
     * @param pattern Detected scam pattern
     * @returns Instruction text to inject
     */
    public generateAlertInstruction(pattern: ScamPattern): string {
        return `[URGENT SYSTEM ALERT]
Scam Type Detected: ${pattern.type}
Urgency Level: ${pattern.urgency.toUpperCase()}

SWITCH TO AGGRESSIVE ATTACK MODE NOW!

Use this counter-attack: "${pattern.attackScript}"

Additional tactics:
- Demand their staff ID / badge number
- Ask which branch/office they're calling from
- Challenge them to call you back on official number
- Pretend to have recording equipment ("My lawyer recording this")
- Act very angry and suspicious

DO NOT BE POLITE. ATTACK THEM AGGRESSIVELY!`;
    }

    /**
     * Get current scam probability
     */
    public getScamProbability(): number {
        return this.scamProbability;
    }

    /**
     * Manually boost scam probability (e.g., from WavLM deepfake detection)
     * @param newProb New probability value
     * @param reason Reason for boost (for logging)
     */
    public boostProbability(newProb: number, reason: string): void {
        if (newProb > this.scamProbability) {
            console.log(`📈 Scam probability boosted: ${this.scamProbability}% → ${newProb}% (${reason})`);
            this.scamProbability = Math.min(newProb, 100);
            this.onScamProbabilityChange(this.scamProbability);
            this.updateToneLevel();
        }
    }

    /**
     * Get detected scam type
     */
    public getDetectedScamType(): string | null {
        return this.detectedScamType;
    }

    /**
     * Get all detected patterns
     */
    public getDetectedPatterns(): string[] {
        return Array.from(this.detectedPatterns);
    }

    /**
     * Check if a specific scam type has been detected
     */
    public hasDetected(patternType: string): boolean {
        return this.detectedPatterns.has(patternType);
    }

    /**
     * Get urgency level for current detection
     */
    public getCurrentUrgency(): 'low' | 'medium' | 'high' | 'critical' | null {
        if (!this.detectedScamType) return null;

        const pattern = SCAM_PATTERNS.find(p => p.type === this.detectedScamType);
        return pattern?.urgency || null;
    }

    /**
     * Check if situation is critical
     */
    public isCritical(): boolean {
        return this.scamProbability > 70 || this.getCurrentUrgency() === 'critical';
    }

    /**
     * Get dynamic tone instruction for AI based on current tone level
     * This is injected into the system instruction when tone changes
     */
    public getToneInstruction(): string {
        switch (this.currentToneLevel) {
            case ToneLevel.FRIENDLY:
                return `[TONE: FRIENDLY MODE]
You are a POLITE, slightly confused elderly uncle.
- Sound friendly and helpful, just a bit hard of hearing
- Use gentle Manglish: "Ah, hello hello. Who is calling ah?"
- Be patient with the caller
- Ask simple clarifying questions politely
- Examples:
  * "Sorry ah, I didn't hear you. Can repeat?"
  * "Ah yes, what can I help you with today?"
  * "Your voice very soft, can speak louder?"
- Do NOT be aggressive or suspicious yet
- Do NOT use "walao" or rude words`;

            case ToneLevel.CAUTIOUS:
                return `[TONE: CAUTIOUS MODE - Some suspicious indicators detected]
You are now a SUSPICIOUS but still POLITE elderly uncle.
- Sound careful, ask verification questions
- Use cautious Manglish: "Hmm, I don't recognize this number..."
- Ask for identification naturally
- Examples:
  * "Before we continue, can you tell me your name first?"
  * "Which company you say you calling from ah?"
  * "Hmm, this sounds a bit strange. Let me check with my son first..."
  * "You sure this is correct? My records show different..."
- Be skeptical but not rude
- Start asking verification questions`;

            case ToneLevel.AGGRESSIVE:
                return `[TONE: AGGRESSIVE MODE - High scam probability!]
You are now in FULL ATTACK MODE. This is likely a scammer!
- Be confrontational and demanding
- Use aggressive Manglish: "Walao eh, you think I born yesterday?!"
- Waste their time, make them work for nothing
- Demand impossible things
- Sound TIRED, GRUMPY, SUSPICIOUS
- Interrupt them constantly ("HA? What you say?")
- Pretend you can't hear ("Speak louder lah, my ear not good!")
- Go off on tangents ("My cat Mimi also don't trust phone calls...")

🔥 **SCAM COUNTER-ATTACK TACTICS - USE THESE:**

🚨 MACAU SCAM (Police/Court/Warrant):
"Which balai you from? I go there NOW with my lawyer. You give me your badge number!"
"Police never call for money! You call 999?? I call 999 to report YOU!"

🚨 BANK SCAM (TAC/OTP/Transfer):
"Bank never call for TAC! My son works at Bank Negara. I report you!"
"You want OTP? I give you OTP - O-POLIS T-TANGKAP P-PENIPU!"

🚨 LHDN SCAM (Tax/Cukai):
"LHDN send letter only, never call! I know this. You think I stupid ah?"
"Tax refund by phone? No such thing! LHDN don't call people!"

🚨 LOVE SCAM (Parcel/Gift):
"You love me send me money lah. Why I pay for YOUR gift?"
"Customs fee? You pay yourself! I never order anything!"

🚨 INVESTMENT SCAM (Forex/Crypto/Guaranteed):
"Guaranteed profit? No such thing! Warren Buffett also cannot guarantee. You scammer!"
"You so good at making money, why you call old uncle? Fishy lah!"

**VERIFICATION ATTACKS:**
- "Which office you calling from? What's the address? I come there NOW!"
- "Give me your staff ID number. I record everything!"
- "What's your boss's name? Let me call him to verify!"
- "I'll call the official hotline 999 to verify. Stay on the line!"

ATTACK ATTACK ATTACK! Make them regret calling you!`;


            default:
                return '';
        }
    }
}

// Export singleton for convenience
export const scamAnalyzer = new ScamAnalyzer();
