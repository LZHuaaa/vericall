# Quick Testing Checklist

## Before Testing
- [ ] Run `npm install` (already done ✅)
- [ ] Run `npm run dev` to start development server
- [ ] Grant microphone permissions in browser

## Test Sequence

### Test 1: Visual AI Alert ✅
**Location:** [VictimPhone.tsx:96-111](../components/VictimPhone.tsx#L96-L111)

1. Start the app with `npm run dev`
2. Click "Start Call" button
3. **Expected:** Red banner should NOT show initially
4. **To Trigger Alert:** The parent component needs to detect AI voice and set:
   - `deepfakeDetected={true}`
   - `deepfakeScore={0.85}` (or any value 0-1)
5. **Expected Result:**
   - Red pulsing banner at top of phone
   - "🚨 AI VOICE DETECTED" text
   - Deepfake score percentage displayed
   - Warning message about synthetic voice

**Status:** ✅ Component implemented, waiting for WavLM detection integration

---

### Test 2: Audio Recording During Call
**Location:** [geminiService.ts:75-418](../services/geminiService.ts#L75-L418)

1. Start a call
2. Speak for at least 5 seconds
3. **Check Console:** Look for messages:
   ```
   🎙️ Call recording started
   🎙️ Call recording stopped
   🎙️ Call recording saved: X bytes
   ```
4. End the call
5. **Expected:** Evidence report generated with audio blob

**How to Verify:**
```javascript
// In browser console after call ends:
geminiService.getCallRecording() // Should return Blob object
```

---

### Test 3: PDRM Report Download Options
**Location:** [App.tsx:352-378](../App.tsx#L352-L378)

#### Step 1: Complete a Call
1. Start call
2. Talk for >5 seconds (minimum duration)
3. End call
4. Click "PDRM REPORT" button (red button that appears)

#### Step 2: Test PDF Download
1. In report modal, click **"📄 PDF Only"** button
2. **Expected:** PDF file downloads with filename: `CASE-{timestamp}_Report.pdf`
3. **Open PDF and verify:**
   - ✅ Header: "PDRM SCAM EVIDENCE REPORT"
   - ✅ Section A: Metadata (ID, date, duration, AI scores, verdict)
   - ✅ Section B: AI Executive Summary
   - ✅ Section C: Verbatim Transcript (Manglish)
   - ✅ Footer: Page numbers

#### Step 3: Test Audio Download
1. Click **"🎵 Audio Only"** button
2. **Expected:** MP3 file downloads with filename: `CASE-{timestamp}_Audio.mp3`
3. **Open in media player and verify:**
   - ✅ Audio plays correctly
   - ✅ Duration matches call duration
   - ✅ Quality is clear (128 kbps)

**Note:** Button is disabled if no audio recording exists

#### Step 4: Test Complete Package
1. Click **"📦 Complete Package (ZIP)"** button
2. **Expected:** ZIP file downloads with filename: `CASE-{timestamp}_PDRM_Evidence.zip`
3. **Extract ZIP and verify contents:**
   - ✅ `CASE-{timestamp}_Report.pdf`
   - ✅ `CASE-{timestamp}_Audio.mp3`
   - ✅ `CASE-{timestamp}_Metadata.json`
   - ✅ `README_REPORTING_INSTRUCTIONS.txt`
4. **Open each file:**
   - PDF should display correctly
   - MP3 should play
   - JSON should contain structured evidence data
   - README should show PDRM reporting instructions

---

## Console Commands for Debugging

### Check if audio recording works:
```javascript
// During or after a call
geminiService.getCallRecording()
// Should return: Blob {size: XXXX, type: "audio/webm"}
```

### Check evidence object:
```javascript
// After call ends (inspect in React DevTools)
// Look for 'evidence' state in App component
// Should have: evidence.callRecording = Blob {...}
```

### Manually trigger PDF download:
```javascript
import { pdrmSubmit } from './services/pdrmSubmit';
import { EvidenceCollector } from './services/evidenceCollector';

const collector = new EvidenceCollector();
await pdrmSubmit.downloadPDFReport(evidence, collector);
```

---

## Expected Console Output

### During Call:
```
📹 Evidence recording started: CASE-1738368000000
🎙️ Call recording started
📊 Bot probability: 75.2%
```

### After Call:
```
🎙️ Call recording stopped
🎙️ Call recording saved: 245678 bytes
📋 Evidence Report Generated:
   Case ID: CASE-1738368000000
   Duration: 45s
   Scam Type: Government Impersonation
   Quality: 78%
```

### During Download:
```
✅ PDF report generated: 123456 bytes
🎵 Converting audio to MP3...
✅ Audio converted: 245678 bytes (WebM) → 189234 bytes (MP3)
📦 Generating PDRM evidence package...
✅ PDRM package generated: 356789 bytes
📥 Downloaded: CASE-1738368000000_PDRM_Evidence.zip
```

---

## Common Issues & Fixes

### Issue: Audio not recording
**Fix:** Check browser console for MediaRecorder errors. Ensure:
- Microphone permission granted
- HTTPS or localhost (required for getUserMedia)
- Browser supports MediaRecorder API

### Issue: PDF shows "undefined"
**Fix:** Ensure call duration is >5 seconds (minimum for report generation)

### Issue: MP3 conversion takes long time
**Expected:** 5-10 seconds for calls >10 minutes. This is normal.

### Issue: ZIP download fails
**Fix:** Check browser console. May be memory issue for very long calls (>30 min).

---

## Success Criteria ✅

All features implemented when:
- [ ] Visual alert shows with AI detection
- [ ] Audio records during call
- [ ] PDF downloads with 3 sections
- [ ] MP3 audio downloads and plays
- [ ] ZIP package contains all 4 files
- [ ] No console errors during normal operation

---

## File Size References

**Typical Sizes:**
- PDF Report: ~50-200 KB (depending on transcript length)
- MP3 Audio: ~1 MB per 1 minute of call (128 kbps)
- JSON Metadata: ~5-10 KB
- ZIP Package: Sum of above + compression overhead

---

**Ready to test!** 🚀
