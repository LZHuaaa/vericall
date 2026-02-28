/**
 * Contact Verifier Module
 * Differentiates between known contacts (friends/family) and potential scammers
 * Uses voice signature, topic analysis, and call pattern verification
 */

import { SCAM_PATTERNS } from './types/scamTypes';

/**
 * Known contact profile for verification
 */
export interface ContactProfile {
    id: string;
    name: string;
    phoneNumber: string;
    relationship: 'family' | 'friend' | 'work' | 'other';
    typicalTopics: string[];                    // What they usually talk about
    voiceSignature?: Float32Array;              // Voice fingerprint (placeholder)
    lastContact?: Date;
    trustLevel: number;                         // 0-100
}

/**
 * Verification result
 */
export interface VerificationResult {
    isKnownContact: boolean;
    confidence: number;                         // 0-100
    matchedContact?: ContactProfile;
    suspiciousIndicators: string[];
    recommendation: 'TRUST' | 'CAUTIOUS' | 'SUSPICIOUS' | 'BLOCK';
    reasoning: string;
}

/**
 * Contact Verifier Class
 * Helps Uncle Ah Hock differentiate between real friends and scammers
 */
export class ContactVerifier {
    private knownContacts: Map<string, ContactProfile> = new Map();
    private conversationTopics: string[] = [];
    private urgentMoneyRequests: number = 0;
    private claimedIdentity: string | null = null;

    // Callbacks
    public onContactVerified: (result: VerificationResult) => void = () => { };
    public onSuspiciousActivity: (reason: string) => void = () => { };

    constructor() {
        // Initialize with some sample contacts (in real app, would load from storage)
        this.initializeSampleContacts();
    }

    /**
     * Initialize sample contacts for demo purposes
     */
    private initializeSampleContacts(): void {
        const sampleContacts: ContactProfile[] = [
            {
                id: 'contact-1',
                name: 'Ah Mei',
                phoneNumber: '+60123456789',
                relationship: 'family',
                typicalTopics: ['health', 'grandchildren', 'dinner', 'medicine'],
                trustLevel: 95
            },
            {
                id: 'contact-2',
                name: 'Ah Kow',
                phoneNumber: '+60198765432',
                relationship: 'friend',
                typicalTopics: ['kopi', 'coffee', 'fishing', 'lottery', 'weather'],
                trustLevel: 85
            },
            {
                id: 'contact-3',
                name: 'Dr. Wong',
                phoneNumber: '+60387654321',
                relationship: 'work',
                typicalTopics: ['appointment', 'medicine', 'checkup', 'health'],
                trustLevel: 90
            }
        ];

        sampleContacts.forEach(contact => {
            this.knownContacts.set(contact.phoneNumber, contact);
        });

        console.log(`📱 ContactVerifier: Loaded ${this.knownContacts.size} known contacts`);
    }

    /**
     * Add a new known contact
     */
    public addContact(contact: ContactProfile): void {
        this.knownContacts.set(contact.phoneNumber, contact);
        console.log(`📱 Added contact: ${contact.name}`);
    }

    /**
     * Remove a contact
     */
    public removeContact(phoneNumber: string): void {
        this.knownContacts.delete(phoneNumber);
    }

    /**
     * Reset for a new call
     */
    public reset(): void {
        this.conversationTopics = [];
        this.urgentMoneyRequests = 0;
        this.claimedIdentity = null;
    }

    /**
     * Main verification method
     * @param phoneNumber Caller's phone number (if available)
     * @param transcript Current conversation transcript
     * @param audioFeatures Audio features for voice comparison (optional)
     */
    public async verifyContact(
        phoneNumber: string,
        transcript: string,
        audioFeatures?: Float32Array
    ): Promise<VerificationResult> {
        const suspiciousIndicators: string[] = [];
        let confidence = 50; // Start neutral

        // Step 1: Check if phone number is known
        const knownContact = this.knownContacts.get(phoneNumber);
        if (knownContact) {
            confidence += 30;
            console.log(`📱 Known contact detected: ${knownContact.name}`);
        } else if (phoneNumber && phoneNumber !== 'UNKNOWN') {
            // Unknown number - slightly suspicious
            suspiciousIndicators.push('Calling from unknown number');
            confidence -= 10;
        }

        // Step 2: Analyze conversation topics
        const topicAnalysis = this.analyzeTopics(transcript, knownContact);
        confidence += topicAnalysis.adjustment;
        if (topicAnalysis.suspicious.length > 0) {
            suspiciousIndicators.push(...topicAnalysis.suspicious);
        }

        // Step 3: Check for scam patterns
        const scamPatterns = this.detectScamPatterns(transcript);
        if (scamPatterns.length > 0) {
            confidence -= 30;
            suspiciousIndicators.push(`Scam keywords detected: ${scamPatterns.join(', ')}`);
        }

        // Step 4: Check for urgent money requests
        const moneyAnalysis = this.analyzeMoneyRequests(transcript);
        if (moneyAnalysis.hasUrgentRequest) {
            confidence -= 25;
            suspiciousIndicators.push('Urgent money request detected');
        }
        if (moneyAnalysis.amount && moneyAnalysis.amount > 1000) {
            confidence -= 20;
            suspiciousIndicators.push(`Large amount requested: RM ${moneyAnalysis.amount}`);
        }

        // Step 5: Check for identity claims that don't match
        const identityCheck = this.checkIdentityClaim(transcript, knownContact);
        if (identityCheck.mismatch) {
            confidence -= 30;
            suspiciousIndicators.push(identityCheck.reason);
        }

        // Step 6: Voice signature comparison (placeholder for future)
        if (audioFeatures && knownContact?.voiceSignature) {
            const voiceMatch = this.compareVoiceSignature(audioFeatures, knownContact.voiceSignature);
            if (voiceMatch < 0.5) {
                confidence -= 20;
                suspiciousIndicators.push('Voice does not match stored signature');
            }
        }

        // Clamp confidence
        confidence = Math.max(0, Math.min(100, confidence));

        // Determine recommendation
        let recommendation: VerificationResult['recommendation'];
        let reasoning: string;

        if (confidence >= 75 && knownContact) {
            recommendation = 'TRUST';
            reasoning = `High confidence match with known contact ${knownContact.name}`;
        } else if (confidence >= 50) {
            recommendation = 'CAUTIOUS';
            reasoning = 'Moderate confidence - proceed with caution';
        } else if (confidence >= 25) {
            recommendation = 'SUSPICIOUS';
            reasoning = 'Low confidence - likely scam attempt';
        } else {
            recommendation = 'BLOCK';
            reasoning = 'Very low confidence - recommend blocking this caller';
        }

        const result: VerificationResult = {
            isKnownContact: !!knownContact,
            confidence,
            matchedContact: knownContact,
            suspiciousIndicators,
            recommendation,
            reasoning
        };

        // Trigger callbacks
        this.onContactVerified(result);
        if (suspiciousIndicators.length > 0) {
            this.onSuspiciousActivity(suspiciousIndicators.join('; '));
        }

        return result;
    }

    /**
     * Analyze conversation topics
     */
    private analyzeTopics(
        transcript: string,
        knownContact?: ContactProfile
    ): { adjustment: number; suspicious: string[] } {
        const lowerTranscript = transcript.toLowerCase();
        const suspicious: string[] = [];
        let adjustment = 0;

        // Check if topics match known contact's typical topics
        if (knownContact) {
            const matchedTopics = knownContact.typicalTopics.filter(topic =>
                lowerTranscript.includes(topic.toLowerCase())
            );
            if (matchedTopics.length > 0) {
                adjustment += 10 * matchedTopics.length;
            } else {
                // Caller claims to be known contact but talking about unusual topics
                suspicious.push('Unusual topics for this contact');
                adjustment -= 10;
            }
        }

        // Check for suspicious topics
        const suspiciousTopics = [
            'transfer', 'urgent', 'immediately', 'secret', 'don\'t tell anyone',
            'arrested', 'accident', 'hospital', 'kidnapped', 'emergency'
        ];

        suspiciousTopics.forEach(topic => {
            if (lowerTranscript.includes(topic)) {
                suspicious.push(`Suspicious topic: ${topic}`);
                adjustment -= 5;
            }
        });

        return { adjustment, suspicious };
    }

    /**
     * Detect scam patterns in transcript
     */
    private detectScamPatterns(transcript: string): string[] {
        const lowerTranscript = transcript.toLowerCase();
        const detected: string[] = [];

        SCAM_PATTERNS.forEach(pattern => {
            const matches = pattern.keywords.filter(keyword =>
                lowerTranscript.includes(keyword.toLowerCase())
            );
            if (matches.length >= 2) {
                detected.push(pattern.type);
            }
        });

        return detected;
    }

    /**
     * Analyze money requests in transcript
     */
    private analyzeMoneyRequests(transcript: string): {
        hasUrgentRequest: boolean;
        amount?: number;
    } {
        const lowerTranscript = transcript.toLowerCase();

        // Check for urgent money keywords
        const urgentKeywords = ['urgent', 'immediately', 'now', 'today', 'sekarang'];
        const moneyKeywords = ['transfer', 'send money', 'pay', 'bayar', 'duit'];

        const hasUrgent = urgentKeywords.some(k => lowerTranscript.includes(k));
        const hasMoney = moneyKeywords.some(k => lowerTranscript.includes(k));

        // Extract amount if mentioned
        const amountMatch = transcript.match(/rm\s*([\d,]+)/i);
        const amount = amountMatch ? parseInt(amountMatch[1].replace(/,/g, ''), 10) : undefined;

        return {
            hasUrgentRequest: hasUrgent && hasMoney,
            amount
        };
    }

    /**
     * Check identity claim against known contact
     */
    private checkIdentityClaim(
        transcript: string,
        knownContact?: ContactProfile
    ): { mismatch: boolean; reason: string } {
        const lowerTranscript = transcript.toLowerCase();

        // Pattern: "This is [name]" or "I am [name]" or "Ini [name]"
        const claimPatterns = [
            /this is (\w+)/i,
            /i am (\w+)/i,
            /ini (\w+)/i,
            /saya (\w+)/i
        ];

        for (const pattern of claimPatterns) {
            const match = lowerTranscript.match(pattern);
            if (match) {
                const claimedName = match[1];
                this.claimedIdentity = claimedName;

                if (knownContact) {
                    // Check if claimed name matches
                    if (!knownContact.name.toLowerCase().includes(claimedName.toLowerCase())) {
                        return {
                            mismatch: true,
                            reason: `Claimed to be "${claimedName}" but caller ID shows ${knownContact.name}`
                        };
                    }
                } else {
                    // Unknown number claiming to be someone
                    // Check if this name is in our contacts
                    let foundContact = false;
                    this.knownContacts.forEach(contact => {
                        if (contact.name.toLowerCase().includes(claimedName.toLowerCase())) {
                            foundContact = true;
                        }
                    });

                    if (foundContact) {
                        return {
                            mismatch: true,
                            reason: `Claims to be "${claimedName}" but calling from unknown number`
                        };
                    }
                }
            }
        }

        return { mismatch: false, reason: '' };
    }

    /**
     * Compare voice signatures (placeholder - returns simulated result)
     * In real implementation, this would use ML-based voice comparison
     */
    private compareVoiceSignature(
        currentVoice: Float32Array,
        storedVoice: Float32Array
    ): number {
        // Placeholder: In real implementation, use cosine similarity or ML model
        // For now, return a random value for demo purposes
        console.log('🔊 Voice comparison placeholder - would compare signatures here');
        return 0.8; // Assume good match for demo
    }

    /**
     * Generate verification questions for the AI to ask
     */
    public getVerificationQuestions(claimedIdentity?: string): string[] {
        const questions: string[] = [];

        if (claimedIdentity) {
            // Find if we have this contact
            let foundContact: ContactProfile | undefined;
            this.knownContacts.forEach(contact => {
                if (contact.name.toLowerCase().includes(claimedIdentity.toLowerCase())) {
                    foundContact = contact;
                }
            });

            if (foundContact) {
                questions.push(`If you are ${foundContact.name}, what did we talk about last time?`);
                questions.push(`What's my (Uncle's) favorite thing to do in the morning?`);
                questions.push(`Where do I usually go for kopi?`);
            }
        }

        // Generic verification questions
        questions.push('Which branch/office are you calling from?');
        questions.push('What is your staff ID or badge number?');
        questions.push('Give me a number I can call back to verify');

        return questions;
    }

    /**
     * Get all known contacts
     */
    public getKnownContacts(): ContactProfile[] {
        return Array.from(this.knownContacts.values());
    }

    /**
     * Get contact by phone number
     */
    public getContactByPhone(phoneNumber: string): ContactProfile | undefined {
        return this.knownContacts.get(phoneNumber);
    }
}

// Export singleton for convenience
export const contactVerifier = new ContactVerifier();
