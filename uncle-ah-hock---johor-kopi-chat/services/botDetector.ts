/**
 * Bot Detector Module
 * Detects silent callers (bots) waiting for victim to speak first for voice cloning
 */

import { BotDetectionStatus, CallMetrics } from './types/scamTypes';

export class BotDetector {
    private metrics: CallMetrics = {
        silenceDuration: 0,
        firstSpeaker: 'neither',
        callerResponseDelay: 0,
        backgroundNoise: 0,
        voiceConsistency: 0
    };

    private callStartTime: number = 0;
    private firstUserSpeech: number = 0;
    private firstCallerSpeech: number = 0;
    private hasRemoteCallerSpoken: boolean = false;
    private hasModelSpoken: boolean = false;
    private backgroundNoiseUpdated: boolean = false;
    private botCheckInterval: NodeJS.Timeout | null = null;

    // Callback for UI updates
    public onBotDetected: (status: BotDetectionStatus) => void = () => { };

    /**
     * Start monitoring a new call
     */
    public start(): void {
        this.callStartTime = Date.now();
        this.hasRemoteCallerSpoken = false;
        this.hasModelSpoken = false;
        this.backgroundNoiseUpdated = false;
        this.firstUserSpeech = 0;
        this.firstCallerSpeech = 0;
        this.conversationTurns = 0;
        this.lastBotReasons = [];
        this.metrics = {
            silenceDuration: 0,
            firstSpeaker: 'neither',
            callerResponseDelay: 0,
            backgroundNoise: 0,
            voiceConsistency: 0
        };
        console.log('🤖 Bot Detection: Monitoring started');
    }

    /**
     * Increment conversation turn counter (call when speaker changes)
     */
    public incrementTurn(): void {
        this.conversationTurns++;
    }

    /**
     * Start periodic bot status checking
     * @param intervalMs Check interval in milliseconds (default: 1000ms)
     */
    public startPeriodicCheck(intervalMs: number = 1000): void {
        this.stopPeriodicCheck();
        this.botCheckInterval = setInterval(() => {
            const status = this.checkStatus();
            if (status.isSuspicious) {
                this.onBotDetected(status);
            }
        }, intervalMs);
    }

    /**
     * Stop periodic bot checking
     */
    public stopPeriodicCheck(): void {
        if (this.botCheckInterval) {
            clearInterval(this.botCheckInterval);
            this.botCheckInterval = null;
        }
    }

    /**
     * Register when someone speaks
     * @param source Who is speaking: 'user' (caller/scammer) or 'model' (Uncle AI)
     */
    public registerSpeech(source: 'user' | 'model'): void {
        const now = Date.now();

        if (source === 'user') {
            // Remote caller (scammer side) spoke
            this.hasRemoteCallerSpoken = true;
            if (this.firstUserSpeech === 0) {
                this.firstUserSpeech = now;

                // If remote caller spoke before Uncle, mark them as first speaker
                if (this.metrics.firstSpeaker === 'neither') {
                    this.metrics.firstSpeaker = 'user';
                    console.log(`📞 Remote caller spoke first after ${now - this.callStartTime}ms`);
                }
            }
        } else {
            // Model (Uncle Ah Hock) speaking — do NOT set hasRemoteCallerSpoken
            this.hasModelSpoken = true;
            if (this.firstCallerSpeech === 0) {
                this.firstCallerSpeech = now;

                // Uncle spoke first (good for defense)
                if (this.metrics.firstSpeaker === 'neither') {
                    this.metrics.firstSpeaker = 'caller';
                    this.metrics.silenceDuration = now - this.callStartTime;
                }
            }
        }
    }

    /**
     * Update background noise level (for synthetic audio detection)
     * @param level Noise level 0-1
     */
    public updateBackgroundNoise(level: number): void {
        this.metrics.backgroundNoise = level;
        this.backgroundNoiseUpdated = true;
    }

    /**
     * Check current bot detection status
     */
    public checkStatus(): BotDetectionStatus {
        const now = Date.now();
        const duration = now - this.callStartTime;

        // Pattern 1: Remote caller stays silent for >3 seconds (waiting for victim's voice)
        // Uncle speaking does NOT count — only remote caller speech clears this
        if (!this.hasRemoteCallerSpoken && this.firstUserSpeech === 0 && duration > 3000) {
            return {
                isSuspicious: true,
                reason: "Caller silent for >3s. Possible Bot waiting for your voice.",
                prob: 85,
                recommendation: "DON'T SPEAK! Wait for caller to identify themselves first."
            };
        }

        // Pattern 2: Very low background noise (synthetic audio)
        // Only trigger if we've actually measured the noise level
        if (this.backgroundNoiseUpdated && this.metrics.backgroundNoise < 0.05 && duration > 2000) {
            return {
                isSuspicious: true,
                reason: "No background noise detected. Possible AI-generated call.",
                prob: 70,
                recommendation: "Real calls have ambient sound. This may be synthetic."
            };
        }

        // Pattern 3: User spoke first (potential voice capture)
        if (this.metrics.firstSpeaker === 'user' && this.firstUserSpeech > 0) {
            const silenceBeforeUser = this.firstUserSpeech - this.callStartTime;
            if (silenceBeforeUser > 2000) {
                return {
                    isSuspicious: true,
                    reason: `You spoke first after ${silenceBeforeUser}ms of silence. Possible voice capture attempt.`,
                    prob: 75,
                    recommendation: "Your voice may have been recorded. Be extra cautious."
                };
            }
        }

        return {
            isSuspicious: false,
            reason: "Normal call pattern",
            prob: 0,
            recommendation: "Continue monitoring"
        };
    }

    /**
     * Calculate overall bot probability (0-100) with improved accuracy
     * Designed to reduce false positives for normal human callers
     */
    public calculateBotProbability(): number {
        let score = 0;
        const reasons: string[] = [];

        // Context-aware factors that REDUCE probability (real human indicators)
        const callDuration = Date.now() - this.callStartTime;
        const hasHadConversation = this.conversationTurns > 2;
        const callerRespondedQuickly = this.metrics.callerResponseDelay < 3000 && this.metrics.callerResponseDelay > 0;

        // PENALTY factors (indicators of bot)
        // Reduced from 40% to 15% - caller waiting could be connection delay
        if (this.metrics.firstSpeaker === 'user' && callDuration < 5000) {
            score += 15;
            reasons.push('Caller waited before speaking');
        }

        // Long initial silence - reduced weight
        if (this.metrics.silenceDuration > 5000) {
            score += 10;
            reasons.push('Long initial silence');
        } else if (this.metrics.silenceDuration > 3000) {
            score += 5;
        }

        // No background noise - reduced weight, could be good phone
        if (this.metrics.backgroundNoise < 0.02) {
            score += 10;
            reasons.push('Very low background noise');
        }

        // BONUS factors (indicators of real human) - REDUCE score
        // If call has lasted >30s with back-and-forth, likely real human
        if (callDuration > 30000 && hasHadConversation) {
            score = Math.max(0, score - 20);
            reasons.push('Extended natural conversation');
        }

        // If caller responded quickly to questions, likely real
        if (callerRespondedQuickly) {
            score = Math.max(0, score - 10);
        }

        // If caller spoke more than once, less likely to be voice capture bot
        if (this.conversationTurns > 1) {
            score = Math.max(0, score - 15);
        }

        // Cap at 100, but for normal conversation cap at 30
        if (!this.hasAnyRedFlags()) {
            score = Math.min(score, 30); // Normal conversation max 30%
        }

        this.lastBotReasons = reasons;
        return Math.min(score, 100);
    }

    /**
     * Check if any major red flags are present
     */
    private hasAnyRedFlags(): boolean {
        return (
            (this.metrics.firstSpeaker === 'user' && this.metrics.silenceDuration > 5000) ||
            (this.backgroundNoiseUpdated && this.metrics.backgroundNoise < 0.01)
        );
    }

    /**
     * Get explanation for bot probability (for UI)
     */
    public getBotProbabilityReasons(): string[] {
        return this.lastBotReasons;
    }

    // Track conversation turns for context
    private conversationTurns: number = 0;
    private lastBotReasons: string[] = [];

    /**
     * Enhanced silent bot detection with audio level
     */
    public detectSilentBot(audioLevel: number, timeElapsed: number): BotDetectionStatus {
        // Pattern 1: Caller stays silent for >3 seconds after connecting
        if (audioLevel < 0.01 && timeElapsed > 3000) {
            return {
                isSuspicious: true,
                reason: "Caller silent for >3 seconds. Possible bot waiting for you to speak.",
                prob: 85,
                recommendation: "DON'T SPEAK! Wait for caller to identify themselves first."
            };
        }

        // Pattern 2: Very low background noise (not a real phone environment)
        if (this.metrics.backgroundNoise < 0.05 && timeElapsed > 2000) {
            return {
                isSuspicious: true,
                reason: "No background noise detected. Possible AI-generated call.",
                prob: 70,
                recommendation: "Real calls have ambient sound. This may be synthetic."
            };
        }

        return {
            isSuspicious: false,
            reason: "Normal call pattern",
            prob: 0,
            recommendation: "Continue monitoring"
        };
    }

    /**
     * Get current metrics for debugging/display
     */
    public getMetrics(): CallMetrics {
        return { ...this.metrics };
    }

    /**
     * Clean up resources
     */
    public cleanup(): void {
        this.stopPeriodicCheck();
    }
}

// Export singleton for convenience
export const botDetector = new BotDetector();
