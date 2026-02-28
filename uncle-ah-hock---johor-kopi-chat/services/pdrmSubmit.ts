/**
 * PDRM Submit Module
 * Handles automatic submission of scam evidence to authorities
 * Currently a placeholder - would integrate with actual PDRM/SKMM APIs
 */

import jsPDF from 'jspdf';
import JSZip from 'jszip';
import { convertToMp3 } from '../utils/audioConverter';
import { EvidenceCollector } from './evidenceCollector';
import { ScamEvidence } from './types/scamTypes';

/**
 * Submission status
 */
export interface SubmissionStatus {
    submitted: boolean;
    referenceNumber?: string;
    timestamp?: Date;
    agency: 'PDRM' | 'SKMM' | 'BNM' | 'NSRC';
    status: 'pending' | 'submitted' | 'received' | 'investigating' | 'closed';
    error?: string;
}

/**
 * Agency contact information
 */
export interface AgencyInfo {
    name: string;
    fullName: string;
    website: string;
    hotline: string;
    reportingUrl?: string;
    description: string;
}

/**
 * PDRM Submit Class
 * Provides automatic and manual submission capabilities
 */
export class PDRMSubmit {
    private submissionHistory: Map<string, SubmissionStatus> = new Map();
    private pendingSubmissions: ScamEvidence[] = [];

    // Callbacks
    public onSubmissionComplete: (status: SubmissionStatus) => void = () => { };
    public onSubmissionError: (error: string) => void = () => { };

    /**
     * Agency information for reference (Verified from official sources)
     */
    public readonly agencies: Record<string, AgencyInfo> = {
        NSRC: {
            name: 'NSRC',
            fullName: 'National Scam Response Centre (Pusat Respons Scam Kebangsaan)',
            website: 'https://www.bnm.gov.my/nsrc',
            hotline: '997',
            description: 'FIRST STEP! Rapid response to freeze scammer accounts. Hours: 8AM-8PM (24hrs from Sept 2025). NOTE: NSRC only RECEIVES calls - they NEVER call you!'
        },
        PDRM: {
            name: 'PDRM/CCID',
            fullName: 'Polis Diraja Malaysia - Commercial Crime Investigation Dept',
            website: 'https://www.rmp.gov.my',
            hotline: '013-211 1222 (CCID Infoline) | 03-2610 1559/1599 (Scam Response)',
            reportingUrl: 'https://semakmule.rmp.gov.my',
            description: 'Lodge formal police report within 24 hours. Use SemakMule to verify suspicious numbers.'
        },
        SKMM: {
            name: 'SKMM/MCMC',
            fullName: 'Suruhanjaya Komunikasi dan Multimedia Malaysia',
            website: 'https://www.mcmc.gov.my',
            hotline: '1-800-888-030 | WhatsApp: 016-2206262',
            reportingUrl: 'https://aduan.skmm.gov.my',
            description: 'Telecommunications complaints. Email: aduanskmm@mcmc.gov.my'
        },
        BNM: {
            name: 'BNM',
            fullName: 'Bank Negara Malaysia',
            website: 'https://www.bnm.gov.my',
            hotline: '1-300-88-5465',
            reportingUrl: 'https://telelink.bnm.gov.my',
            description: 'Financial fraud and banking scams'
        }
    };

    constructor() {
        console.log('📤 PDRMSubmit: Initialized (placeholder mode)');
    }

    /**
     * Submit evidence to PDRM (placeholder)
     * In production, this would use actual PDRM API or web scraping
     */
    public async submitToPDRM(evidence: ScamEvidence): Promise<SubmissionStatus> {
        console.log(`📤 Submitting evidence ${evidence.id} to PDRM...`);

        // Simulate API call delay
        await this.delay(1000);

        // Generate mock reference number
        const refNumber = `PDRM-${Date.now().toString(36).toUpperCase()}`;

        const status: SubmissionStatus = {
            submitted: true,
            referenceNumber: refNumber,
            timestamp: new Date(),
            agency: 'PDRM',
            status: 'pending'
        };

        // Store in history
        this.submissionHistory.set(evidence.id, status);

        // Log the submission (in real implementation, would POST to API)
        console.log(`✅ Evidence submitted to PDRM. Reference: ${refNumber}`);
        console.log(`   Case ID: ${evidence.id}`);
        console.log(`   Scam Type: ${evidence.scamType}`);
        console.log(`   Keywords: ${evidence.scamKeywords.join(', ')}`);

        this.onSubmissionComplete(status);
        return status;
    }

    /**
     * Submit evidence to SKMM (placeholder)
     */
    public async submitToSKMM(evidence: ScamEvidence): Promise<SubmissionStatus> {
        console.log(`📤 Submitting evidence ${evidence.id} to SKMM...`);

        await this.delay(800);

        const refNumber = `SKMM-${Date.now().toString(36).toUpperCase()}`;

        const status: SubmissionStatus = {
            submitted: true,
            referenceNumber: refNumber,
            timestamp: new Date(),
            agency: 'SKMM',
            status: 'received'
        };

        this.submissionHistory.set(`${evidence.id}-skmm`, status);
        this.onSubmissionComplete(status);
        return status;
    }

    /**
     * Submit to Bank Negara Malaysia (for banking scams)
     */
    public async submitToBNM(evidence: ScamEvidence): Promise<SubmissionStatus> {
        console.log(`📤 Submitting evidence ${evidence.id} to BNM...`);

        await this.delay(800);

        const refNumber = `BNM-${Date.now().toString(36).toUpperCase()}`;

        const status: SubmissionStatus = {
            submitted: true,
            referenceNumber: refNumber,
            timestamp: new Date(),
            agency: 'BNM',
            status: 'received'
        };

        this.submissionHistory.set(`${evidence.id}-bnm`, status);
        this.onSubmissionComplete(status);
        return status;
    }

    /**
     * Auto-submit to all relevant agencies based on scam type
     */
    public async autoSubmitAll(evidence: ScamEvidence): Promise<SubmissionStatus[]> {
        const results: SubmissionStatus[] = [];

        // Always submit to PDRM
        results.push(await this.submitToPDRM(evidence));

        // Submit to SKMM for phone scams
        results.push(await this.submitToSKMM(evidence));

        // Submit to BNM for banking/financial scams
        if (evidence.scamType.toLowerCase().includes('bank') ||
            evidence.scamKeywords.some(k => ['otp', 'tac', 'pin', 'transfer'].includes(k.toLowerCase()))) {
            results.push(await this.submitToBNM(evidence));
        }

        console.log(`✅ Auto-submitted to ${results.length} agencies`);
        return results;
    }

    /**
     * Queue evidence for later submission
     */
    public queueForSubmission(evidence: ScamEvidence): void {
        this.pendingSubmissions.push(evidence);
        console.log(`📋 Evidence queued for submission. Queue size: ${this.pendingSubmissions.length}`);
    }

    /**
     * Process all pending submissions
     */
    public async processPendingSubmissions(): Promise<void> {
        console.log(`📤 Processing ${this.pendingSubmissions.length} pending submissions...`);

        while (this.pendingSubmissions.length > 0) {
            const evidence = this.pendingSubmissions.shift()!;
            await this.submitToPDRM(evidence);
        }

        console.log('✅ All pending submissions processed');
    }

    /**
     * Get submission status by case ID
     */
    public getSubmissionStatus(caseId: string): SubmissionStatus | undefined {
        return this.submissionHistory.get(caseId);
    }

    /**
     * Get all submission history
     */
    public getSubmissionHistory(): Map<string, SubmissionStatus> {
        return this.submissionHistory;
    }

    /**
     * Generate downloadable report for manual submission (Text format)
     */
    public generateDownloadableReport(evidence: ScamEvidence, collector: EvidenceCollector): Blob {
        const report = collector.generatePoliceReport(evidence);
        return new Blob([report], { type: 'text/plain;charset=utf-8' });
    }

    /**
     * Generate PDF report with 3 sections
     * Section A: Metadata
     * Section B: AI Summary
     * Section C: Evidence Transcript
     */
    public async generatePDFReport(evidence: ScamEvidence, collector: EvidenceCollector): Promise<Blob> {
        const doc = new jsPDF();
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 15;
        const maxWidth = pageWidth - 2 * margin;
        let yPos = margin;

        // Helper: Add text with word wrap and page breaks
        const addText = (text: string, fontSize: number = 10, isBold: boolean = false) => {
            doc.setFontSize(fontSize);
            doc.setFont('helvetica', isBold ? 'bold' : 'normal');
            
            // Split text to fit page width
            const lines = doc.splitTextToSize(text, maxWidth);
            
            for (const line of lines) {
                // Check if we need a new page
                if (yPos > pageHeight - margin - 15) {
                    doc.addPage();
                    yPos = margin;
                }
                
                doc.text(line, margin, yPos);
                yPos += fontSize * 0.35; // Tighter line spacing
            }
            
            yPos += 2; // Small gap after paragraph
        };

        // Helper: Add section separator (use ASCII = instead of Unicode)
        const addSeparator = () => {
            const separator = '='.repeat(70); // Regular = character
            addText(separator, 10, false);
        };

        // ===== HEADER =====
        doc.setFillColor(200, 0, 0);
        doc.rect(0, 0, pageWidth, 20, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text('PDRM SCAM EVIDENCE REPORT', pageWidth / 2, 12, { align: 'center' });
        doc.setTextColor(0, 0, 0);
        yPos = 30;

        // ===== SECTION A: METADATA =====
        addSeparator();
        addText('SECTION A: CASE METADATA', 12, true);
        addSeparator();
        yPos += 3;

        addText(`Reference ID: ${evidence.id}`, 10, true);
        addText(`Date/Time: ${evidence.timestamp.toLocaleString('en-MY')}`, 10);
        addText(`Duration: ${Math.floor(evidence.duration / 60)}m ${evidence.duration % 60}s`, 10);
        addText(`Caller ID: ${evidence.callerNumber || 'UNKNOWN'}`, 10);
        yPos += 3;

        // AI Detection Results
        addText('AI DETECTION RESULTS:', 11, true);
        // Normalize values because some fields are ratios (0-1) while others are percentages (0-100).
        const asPercent = (value?: number | null): number | null => {
            if (typeof value !== 'number' || !Number.isFinite(value)) return null;
            if (value <= 1) return Math.max(0, Math.min(100, value * 100));
            return Math.max(0, Math.min(100, value));
        };

        const botProbabilityPct = asPercent(evidence.botProbability) ?? 0;
        const aiVoicePct = asPercent(evidence.aiVoiceProbability);
        const deepfakeScore = aiVoicePct !== null ? `${aiVoicePct.toFixed(1)}%` : 'N/A';
        addText(`  Deepfake Score: ${deepfakeScore}`, 10);
        addText(`  Bot Probability: ${botProbabilityPct.toFixed(1)}%`, 10);
        addText(`  Evidence Quality: ${evidence.evidenceQuality || 0}%`, 10);
        yPos += 3;

        // AI Verdict
        const riskLevel = botProbabilityPct >= 80
            ? 'HIGH RISK' 
            : botProbabilityPct >= 50
            ? 'MEDIUM RISK' 
            : 'LOW RISK';
        addText(`AI VERDICT: ${riskLevel}`, 11, true);
        addText(`Scam Type: ${evidence.scamType}`, 10);
        yPos += 5;

        // ===== SECTION B: AI SUMMARY =====
        addSeparator();
        addText('SECTION B: AI EXECUTIVE SUMMARY', 12, true);
        addSeparator();
        yPos += 3;

        const aiSummary = collector.generateAISummary(evidence);
        addText(aiSummary, 10);
        yPos += 3;

        // Keywords
        if (evidence.scamKeywords.length > 0) {
            addText('SCAM KEYWORDS DETECTED:', 11, true);
            addText(`  ${evidence.scamKeywords.join(', ')}`, 10);
            yPos += 2;
        }

        // Inconsistencies
        if (evidence.inconsistencies.length > 0) {
            addText('INCONSISTENCIES FOUND:', 11, true);
            evidence.inconsistencies.forEach(inc => {
                addText(`  - ${inc}`, 10);
            });
            yPos += 5;
        }

        // ===== SECTION C: TRANSCRIPT =====
        addSeparator();
        addText('SECTION C: VERBATIM TRANSCRIPT (MANGLISH)', 12, true);
        addSeparator();
        yPos += 3;

        // Format transcript
        const transcriptLines = evidence.fullTranscript
            .split('\n')
            .filter(line => line.trim());
        
        transcriptLines.forEach(line => {
            addText(line, 9);
        });

        // ===== FOOTER =====
        const pageCount = doc.getNumberOfPages();
        for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i);
            doc.setFontSize(8);
            doc.setTextColor(128, 128, 128);
            doc.text(
                `Generated by Uncle Ah Hock AI Defense System | Page ${i} of ${pageCount}`,
                pageWidth / 2,
                pageHeight - 10,
                { align: 'center' }
            );
        }

        // Convert to blob
        const pdfBlob = doc.output('blob');
        console.log('✅ PDF report generated:', pdfBlob.size, 'bytes');
        return pdfBlob;
    }

    /**
     * Generate complete PDRM evidence package (ZIP file)
     * Contains: PDF report + MP3 audio + metadata JSON
     */
    public async generatePDRMPackage(evidence: ScamEvidence, collector: EvidenceCollector): Promise<Blob> {
        console.log('📦 Generating PDRM evidence package...');

        const zip = new JSZip();

        // 1. Add PDF report
        const pdfBlob = await this.generatePDFReport(evidence, collector);
        zip.file(`${evidence.id}_Report.pdf`, pdfBlob);

        // 2. Add audio recording (convert to MP3 if available)
        if (evidence.callRecording) {
            console.log('🎵 Converting audio to MP3...');
            const mp3Blob = await convertToMp3(evidence.callRecording);
            zip.file(`${evidence.id}_Audio.mp3`, mp3Blob);
        }

        // 3. Add metadata JSON
        const metadata = {
            caseId: evidence.id,
            timestamp: evidence.timestamp.toISOString(),
            duration: evidence.duration,
            callerNumber: evidence.callerNumber,
            scamType: evidence.scamType,
            botProbability: evidence.botProbability,
            aiVoiceProbability: evidence.aiVoiceProbability,
            evidenceQuality: evidence.evidenceQuality,
            scamKeywords: evidence.scamKeywords,
            inconsistencies: evidence.inconsistencies,
            evidenceHash: evidence.evidenceHash,
            generatedBy: 'Uncle Ah Hock AI Defense System',
            version: '1.0'
        };
        zip.file(`${evidence.id}_Metadata.json`, JSON.stringify(metadata, null, 2));

        // 4. Add README with instructions
        const readme = this.getManualReportingInstructions(evidence);
        zip.file('README_REPORTING_INSTRUCTIONS.txt', readme);

        // Generate ZIP
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        console.log('✅ PDRM package generated:', zipBlob.size, 'bytes');

        return zipBlob;
    }

    /**
     * Download PDF report only
     */
    public async downloadPDFReport(evidence: ScamEvidence, collector: EvidenceCollector): Promise<void> {
        const pdfBlob = await this.generatePDFReport(evidence, collector);
        this.downloadBlob(pdfBlob, `${evidence.id}_Report.pdf`);
    }

    /**
     * Download audio recording only (as MP3)
     */
    public async downloadAudioRecording(evidence: ScamEvidence): Promise<void> {
        console.log('🎵 Attempting to download audio recording...');
        console.log('Evidence has callRecording:', !!evidence.callRecording);
        
        if (!evidence.callRecording) {
            console.error('⚠️ No audio recording available in evidence object');
            alert('No audio recording is available for this call. Make sure the call lasted more than 5 seconds.');
            return;
        }

        try {
            console.log('🎵 Converting WebM to MP3...');
            const mp3Blob = await convertToMp3(evidence.callRecording);
            console.log('✅ MP3 conversion complete:', mp3Blob.size, 'bytes');
            
            this.downloadBlob(mp3Blob, `${evidence.id}_Audio.mp3`);
        } catch (error) {
            console.error('❌ Audio download failed:', error);
            alert(`Failed to download audio: ${error}`);
        }
    }

    /**
     * Download complete PDRM package (ZIP)
     */
    public async downloadCompletePackage(evidence: ScamEvidence, collector: EvidenceCollector): Promise<void> {
        const zipBlob = await this.generatePDRMPackage(evidence, collector);
        this.downloadBlob(zipBlob, `${evidence.id}_PDRM_Evidence.zip`);
    }

    /**
     * Helper: Download blob to user's device
     */
    private downloadBlob(blob: Blob, filename: string): void {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log(`📥 Downloaded: ${filename}`);
    }

    /**
     * Get agency information
     */
    public getAgencyInfo(agency: keyof typeof this.agencies): AgencyInfo {
        return this.agencies[agency];
    }

    /**
     * Generate instructions for manual reporting
     */
    public getManualReportingInstructions(evidence: ScamEvidence): string {
        return `
═══════════════════════════════════════════════════════════════
ARAHAN MELAPORKAN SECARA MANUAL / MANUAL REPORTING INSTRUCTIONS
═══════════════════════════════════════════════════════════════

ID Kes / Case ID: ${evidence.id}
Jenis Penipuan / Scam Type: ${evidence.scamType}

LANGKAH 1 / STEP 1: PDRM
─────────────────────────
• Hubungi / Call: 999 atau 03-2266 2222
• Layari / Visit: https://semakmule.rmp.gov.my
• Bawa / Bring: Laporan ini, bukti transaksi (jika ada)

LANGKAH 2 / STEP 2: SKMM
─────────────────────────
• Layari / Visit: https://aduan.skmm.gov.my
• Hubungi / Call: 1-800-888-030
• Aduan mengenai nombor telefon penipu

LANGKAH 3 / STEP 3: NSRC (Jika melibatkan wang)
───────────────────────────────────────────────
• Hubungi / Call: 997 (dalam masa 24 jam)
• Untuk membekukan akaun penipu segera
• For freezing scammer's account immediately

DOKUMEN YANG PERLU / REQUIRED DOCUMENTS:
────────────────────────────────────────
✓ Laporan bukti ini / This evidence report
✓ Tangkap layar perbualan / Screenshots of conversation
✓ Bukti transaksi bank / Bank transaction proof (if any)
✓ Salinan IC / Copy of IC

═══════════════════════════════════════════════════════════════
`;
    }

    /**
     * Helper: Delay function
     */
    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Export singleton for convenience
export const pdrmSubmit = new PDRMSubmit();
