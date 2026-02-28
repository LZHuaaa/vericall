/**
 * Scam Intelligence Module
 * Real-time scam report searching and community learning
 */

import { SCAM_PATTERNS, ScamPattern } from './types/scamTypes';

/**
 * Community scam report structure
 */
export interface ScamReport {
    id: string;
    reportedAt: Date;
    phoneNumber?: string;
    scamType: string;
    description: string;
    keywords: string[];
    amountLost?: number;
    organization?: string;
    tactics: string[];
    verified: boolean;
    reportCount: number;         // How many people reported this
}

/**
 * Search result from scam database/Google
 */
export interface ScamSearchResult {
    source: 'local' | 'google' | 'community';
    title: string;
    snippet: string;
    url?: string;
    relevanceScore: number;
    isScam: boolean;
    details?: ScamReport;
}

/**
 * Scam Intelligence Class
 * Provides real-time scam verification and community learning
 */
export class ScamIntelligence {
    private communityReports: Map<string, ScamReport> = new Map();
    private learnedPatterns: ScamPattern[] = [];
    private searchCache: Map<string, ScamSearchResult[]> = new Map();

    // Callbacks
    public onNewThreatLearned: (pattern: ScamPattern) => void = () => { };
    public onSearchComplete: (results: ScamSearchResult[]) => void = () => { };

    constructor() {
        // Initialize with known scam reports
        this.initializeKnownScams();
    }

    /**
     * Initialize with known scam reports for demo
     */
    private initializeKnownScams(): void {
        const knownScams: ScamReport[] = [
            {
                id: 'scam-001',
                reportedAt: new Date('2024-01-15'),
                phoneNumber: '+60123456789',
                scamType: 'Macau Scam',
                description: 'Caller claims to be PDRM officer, threatens arrest over fake warrant',
                keywords: ['pdrm', 'warrant', 'arrest', 'bukit aman'],
                tactics: ['Urgency', 'Fear', 'Authority impersonation'],
                verified: true,
                reportCount: 127
            },
            {
                id: 'scam-002',
                reportedAt: new Date('2024-01-20'),
                scamType: 'Bank OTP Scam',
                description: 'Claims account is frozen, requests OTP to "unblock"',
                keywords: ['otp', 'tac', 'blocked', 'maybank', 'cimb'],
                organization: 'Maybank',
                tactics: ['Technical jargon', 'Urgency', 'Fear of loss'],
                verified: true,
                reportCount: 89
            },
            {
                id: 'scam-003',
                reportedAt: new Date('2024-01-25'),
                scamType: 'LHDN Tax Scam',
                description: 'Fake LHDN officer claims outstanding tax, threatens legal action',
                keywords: ['lhdn', 'cukai', 'tax', 'arrears', 'court'],
                organization: 'LHDN',
                tactics: ['Government authority', 'Legal threats', 'Urgency'],
                verified: true,
                reportCount: 156
            },
            {
                id: 'scam-004',
                reportedAt: new Date('2024-02-01'),
                phoneNumber: '+60198765432',
                scamType: 'Love Scam',
                description: 'Online acquaintance claims parcel stuck at customs, needs money',
                keywords: ['parcel', 'customs', 'love', 'overseas', 'gift'],
                amountLost: 25000,
                tactics: ['Emotional manipulation', 'Fake relationship', 'Gift trap'],
                verified: true,
                reportCount: 43
            }
        ];

        knownScams.forEach(report => {
            this.communityReports.set(report.id, report);
        });

        console.log(`📊 ScamIntelligence: Loaded ${this.communityReports.size} known scam reports`);
    }

    /**
     * Search for scam reports matching a query
     * Combines local database, community reports, and simulated Google search
     */
    public async searchScamReports(query: string): Promise<ScamSearchResult[]> {
        const results: ScamSearchResult[] = [];
        const lowerQuery = query.toLowerCase();

        // Check cache first
        if (this.searchCache.has(lowerQuery)) {
            console.log('🔍 Search cache hit');
            return this.searchCache.get(lowerQuery)!;
        }

        // 1. Search local community reports
        this.communityReports.forEach(report => {
            const keywordMatches = report.keywords.filter(k =>
                lowerQuery.includes(k.toLowerCase()) || k.toLowerCase().includes(lowerQuery)
            );

            if (keywordMatches.length > 0 ||
                report.description.toLowerCase().includes(lowerQuery) ||
                report.scamType.toLowerCase().includes(lowerQuery)) {
                results.push({
                    source: 'community',
                    title: `${report.scamType} - ${report.reportCount} reports`,
                    snippet: report.description,
                    relevanceScore: Math.min(100, 50 + keywordMatches.length * 20),
                    isScam: true,
                    details: report
                });
            }
        });

        // 2. Search known scam patterns
        SCAM_PATTERNS.forEach(pattern => {
            const keywordMatches = pattern.keywords.filter(k => lowerQuery.includes(k.toLowerCase()));
            if (keywordMatches.length > 0) {
                results.push({
                    source: 'local',
                    title: `Known Pattern: ${pattern.type}`,
                    snippet: `Common keywords: ${keywordMatches.join(', ')}. Counter: ${pattern.attackScript}`,
                    relevanceScore: Math.min(100, 60 + keywordMatches.length * 15),
                    isScam: true
                });
            }
        });

        // 3. Search learned patterns
        this.learnedPatterns.forEach(pattern => {
            const keywordMatches = pattern.keywords.filter(k => lowerQuery.includes(k.toLowerCase()));
            if (keywordMatches.length > 0) {
                results.push({
                    source: 'community',
                    title: `Learned Pattern: ${pattern.type}`,
                    snippet: pattern.attackScript,
                    relevanceScore: Math.min(100, 55 + keywordMatches.length * 15),
                    isScam: true
                });
            }
        });

        // 4. Simulate Google Search results (in real app, would use actual API)
        const googleResults = this.simulateGoogleSearch(query);
        results.push(...googleResults);

        // Sort by relevance
        results.sort((a, b) => b.relevanceScore - a.relevanceScore);

        // Cache results
        this.searchCache.set(lowerQuery, results);

        // Trigger callback
        this.onSearchComplete(results);

        return results;
    }

    /**
     * Simulate Google Search results (placeholder)
     * In production, would integrate with actual Google Search API
     */
    private simulateGoogleSearch(query: string): ScamSearchResult[] {
        const lowerQuery = query.toLowerCase();
        const results: ScamSearchResult[] = [];

        // Simulated search results based on common scam queries
        if (lowerQuery.includes('lhdn') || lowerQuery.includes('tax')) {
            results.push({
                source: 'google',
                title: 'LHDN Official Statement on Phone Scams - Hasil.gov.my',
                snippet: 'LHDN does not make phone calls requesting personal information or payment. All communications are via official mail.',
                url: 'https://www.hasil.gov.my',
                relevanceScore: 85,
                isScam: false // This is the legitimate source
            });
        }

        if (lowerQuery.includes('pdrm') || lowerQuery.includes('police') || lowerQuery.includes('arrest')) {
            results.push({
                source: 'google',
                title: 'Beware of Macau Scam - PDRM Official Warning',
                snippet: 'PDRM warns public about scammers impersonating police officers. Real warrants are served in person.',
                url: 'https://www.rmp.gov.my/awareness',
                relevanceScore: 90,
                isScam: false
            });
        }

        if (lowerQuery.includes('maybank') || lowerQuery.includes('cimb') || lowerQuery.includes('bank')) {
            results.push({
                source: 'google',
                title: 'Bank Negara Fraud Alert - Do Not Share OTP/TAC',
                snippet: 'Bank Negara Malaysia reminds public that banks NEVER call to request OTP, TAC, or PIN numbers.',
                url: 'https://www.bnm.gov.my/consumer-alert',
                relevanceScore: 88,
                isScam: false
            });
        }

        // Generic scam awareness
        results.push({
            source: 'google',
            title: 'NSRC - National Scam Response Centre',
            snippet: 'Report scams at NSRC hotline 997. Website: https://www.semakmule.rmp.gov.my',
            url: 'https://semakmule.rmp.gov.my',
            relevanceScore: 70,
            isScam: false
        });

        return results;
    }

    /**
     * Learn from community reports and update patterns
     */
    public async learnFromCommunityReports(): Promise<void> {
        console.log('📚 Learning from community reports...');

        // Analyze community reports for new patterns
        const tacticFrequency: Map<string, number> = new Map();
        const keywordFrequency: Map<string, number> = new Map();

        this.communityReports.forEach(report => {
            // Count tactics
            report.tactics.forEach(tactic => {
                tacticFrequency.set(tactic, (tacticFrequency.get(tactic) || 0) + report.reportCount);
            });

            // Count keywords
            report.keywords.forEach(keyword => {
                keywordFrequency.set(keyword, (keywordFrequency.get(keyword) || 0) + report.reportCount);
            });
        });

        // Log insights
        console.log('📊 Top tactics:', Array.from(tacticFrequency.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5));

        console.log('📊 Top keywords:', Array.from(keywordFrequency.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10));

        // Generate new attack scripts based on common patterns
        const topKeywords = Array.from(keywordFrequency.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([keyword]) => keyword);

        console.log(`📚 Updated scam intelligence with ${topKeywords.length} trending keywords`);
    }

    /**
     * Add a new community report
     */
    public addCommunityReport(report: Omit<ScamReport, 'id' | 'reportedAt' | 'reportCount' | 'verified'>): void {
        const newReport: ScamReport = {
            ...report,
            id: `report-${Date.now()}`,
            reportedAt: new Date(),
            reportCount: 1,
            verified: false
        };

        this.communityReports.set(newReport.id, newReport);
        console.log(`📝 New community report added: ${newReport.scamType}`);

        // Check if this reveals a new pattern
        this.analyzeForNewPattern(newReport);
    }

    /**
     * Analyze report for new scam patterns
     */
    private analyzeForNewPattern(report: ScamReport): void {
        // Check if keywords match any existing pattern
        let matchedExisting = false;

        [...SCAM_PATTERNS, ...this.learnedPatterns].forEach(pattern => {
            const overlap = report.keywords.filter(k =>
                pattern.keywords.some(pk => pk.toLowerCase() === k.toLowerCase())
            );
            if (overlap.length >= 2) {
                matchedExisting = true;
            }
        });

        // If no match, this might be a new pattern
        if (!matchedExisting && report.keywords.length >= 3) {
            const newPattern: ScamPattern = {
                type: `New: ${report.scamType}`,
                keywords: report.keywords,
                urgency: 'medium',
                attackScript: `Detected new scam pattern! Be careful of anyone mentioning: ${report.keywords.join(', ')}`
            };

            this.learnedPatterns.push(newPattern);
            this.onNewThreatLearned(newPattern);
            console.log(`🚨 New scam pattern learned: ${newPattern.type}`);
        }
    }

    /**
     * Get trending scam types
     */
    public getTrendingScams(): ScamReport[] {
        return Array.from(this.communityReports.values())
            .sort((a, b) => b.reportCount - a.reportCount)
            .slice(0, 5);
    }

    /**
     * Get learned patterns
     */
    public getLearnedPatterns(): ScamPattern[] {
        return this.learnedPatterns;
    }

    /**
     * Check if a phone number has been reported
     */
    public checkPhoneNumber(phoneNumber: string): ScamReport | undefined {
        for (const report of this.communityReports.values()) {
            if (report.phoneNumber === phoneNumber) {
                return report;
            }
        }
        return undefined;
    }

    /**
     * Get statistics
     */
    public getStatistics(): {
        totalReports: number;
        verifiedReports: number;
        learnedPatterns: number;
        topScamType: string;
    } {
        const reports = Array.from(this.communityReports.values());
        const scamTypeCounts: Map<string, number> = new Map();

        reports.forEach(report => {
            scamTypeCounts.set(report.scamType,
                (scamTypeCounts.get(report.scamType) || 0) + report.reportCount);
        });

        let topScamType = 'Unknown';
        let maxCount = 0;
        scamTypeCounts.forEach((count, type) => {
            if (count > maxCount) {
                maxCount = count;
                topScamType = type;
            }
        });

        return {
            totalReports: reports.reduce((sum, r) => sum + r.reportCount, 0),
            verifiedReports: reports.filter(r => r.verified).length,
            learnedPatterns: this.learnedPatterns.length,
            topScamType
        };
    }
}

// Export singleton for convenience
export const scamIntelligence = new ScamIntelligence();
