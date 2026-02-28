# Uncle Ah Hock v2.0 - Advanced AI Defense System

## 🛡️ Project Overview
**Uncle Ah Hock** is an advanced AI-powered "active defense" system designed to protect Malaysians from phone scams. Unlike passive call blockers, Uncle Ah Hock answers the call using a realistic persona (a 75-year-old retired taxi driver from Johor Bahru) to engage scammers, waste their time, and gather evidence.

---

## 🚀 Key Features (Implemented)

### 1. 🤖 Bot Defense Protocol (Voice Cloning Protection)
Scammers often use bots that stay silent to record the victim's "Hello" for voice cloning.
- **Silence Detection:** Monitors audio levels at call start via `BotDetector` class
- **Active Interception:** If caller silent >3 seconds, triggers "BOT DETECTED" alert
- **Auto-Speak:** Uncle Ah Hock automatically says "Hello?? You still there ah?" to prevent voice capture
- **Bot Probability Score:** 0-100% calculation based on silence duration, first speaker, background noise

### 2. 📹 Forensic Evidence Collection
The system treats every call as a crime scene.
- **Real-Time Logging:** Records full transcripts with timestamps
- **Keyword Trapping:** Auto-detects scam keywords (TAC, LHDN, Warrant, etc.)
- **Audio Recording:** Records all audio chunks as evidence
- **SHA-256 Hash:** Cryptographic evidence hash for data integrity
- **Evidence Quality Score:** 0-100% assessment of evidence completeness
- **PDRM-Ready Reports:** Generates bilingual (EN/BM) police reports

### 3. 🧠 Real-Time Scam Intelligence
- **Dynamic Threat Meter:** Visual gauge (0-100%) that rises based on keyword detection
- **Pattern Recognition:** Identifies Macau Scam, Bank Scam, LHDN Scam, Love Scam, Investment Scam
- **Auto-Aggression:** Critical threats auto-inject counter-attack instructions
- **Auto-Search:** When scam probability ≥30%, searches intelligence database and injects info

### 4. 👤 Contact Verification
Differentiates between known contacts and potential scammers.
- **Phone Number Matching:** Checks against known contacts database
- **Topic Analysis:** Compares conversation topics to contact's typical topics
- **Identity Claim Detection:** Detects when caller claims to be someone they're not
- **Voice Signature Comparison:** (Placeholder for ML-based voice matching)
- **Verification Questions:** Generates questions to challenge suspicious callers

### 5. 🔍 Scam Intelligence Database
- **Community Reports:** Database of known scam patterns and tactics
- **searchScamReports():** Searches for relevant scam information
- **learnFromCommunityReports():** Updates patterns from community data
- **Trending Scams:** Tracks most common scam types

### 6. 📤 Police Submission System
Auto-generates and prepares evidence for official agencies.
- **PDRM Submission:** Royal Malaysian Police (placeholder API)
- **SKMM Submission:** Malaysian Communications Commission
- **BNM Submission:** Bank Negara for financial scams
- **Submission Tracking:** Reference numbers and status

### 7. 🔑 API Key Rotation
- **Multi-Key Support:** Up to 5 API keys from different accounts
- **Auto-Rotation:** Automatically switches keys on 429 rate limit errors
- **Status Tracking:** Shows which key is active and which are exhausted

### 8. 🎤 Gemini Live Interaction (Voice Mode)
- **Model:** `gemini-2.5-flash-native-audio-preview-12-2025`
- **Tools:**
  - `googleSearch`: Real-time fact verification
  - `check_scam_database`: Local scam records check
  - `analyze_foreign_speech`: Non-English threat translation

### 9. 🎬 Director Mode
Manual guidance during calls:
- **Fake Heart Attack:** Medical emergency script
- **Demand ID:** Force verification
- **No Money:** Feign poverty

---

## 📁 Module Structure

```
services/
├── geminiService.ts       # Main Gemini Live connection
├── botDetector.ts         # Bot/silence detection
├── evidenceCollector.ts   # Evidence & PDRM reports
├── scamAnalyzer.ts        # Scam pattern detection
├── contactVerifier.ts     # Friend vs scammer verification
├── scamIntelligence.ts    # Search & community learning
├── pdrmSubmit.ts          # Police submission
├── apiKeyManager.ts       # Multi-key rotation
└── types/scamTypes.ts     # Shared interfaces
```

---

## 🔧 How to Access Features

### Contact Verifier
```typescript
import { geminiService } from './services/geminiService';

// Set callback for verification results
geminiService.onContactVerified = (result) => {
  console.log('Contact verified:', result.recommendation); // TRUST, CAUTIOUS, SUSPICIOUS, BLOCK
  console.log('Confidence:', result.confidence);
  console.log('Suspicious indicators:', result.suspiciousIndicators);
};

// Manually trigger verification
geminiService.contactVerifier.verifyContact('+60123456789', transcript);
```

### API Key Rotation
```
# .env.local - Add comma-separated keys
API_KEY=key1,key2,key3,key4,key5
```

```typescript
// Callback when key rotates
geminiService.onApiKeyRotated = (index, total) => {
  console.log(`Using key ${index}/${total}`);
};

geminiService.onAllApiKeysExhausted = () => {
  alert('All API keys exhausted!');
};
```

---

## 🚨 OFFICIAL MALAYSIAN SCAM REPORTING PROCEDURES

Based on official government sources, here are the correct channels to report scam calls:

### 1. NSRC - National Scam Response Centre (FIRST STEP!)
**Hotline:** 997
**Hours:** 8AM-8PM daily (From Sept 2025: 24 hours)
**Purpose:** Rapid response to freeze scammer accounts
**Note:** NSRC only RECEIVES calls - they NEVER call you!

### 2. PDRM - Royal Malaysian Police
**CCID Infoline:** 013-211 1222
**CCID Scam Response:** 03-2610 1559 / 03-2610 1599
**Website:** https://semakmule.rmp.gov.my (verify suspicious numbers)
**Action:** Lodge formal police report within 24 hours

### 3. Bank (If Money Transferred)
Contact your bank's 24/7 hotline immediately to freeze accounts

### 4. SKMM/MCMC - Communications Commission
**Website:** https://aduan.skmm.gov.my
**WhatsApp:** 016-2206262
**Email:** aduanskmm@mcmc.gov.my
**Purpose:** Telecommunications complaints

### 5. BNM - Bank Negara Malaysia
**Hotline:** 1-300-88-5465
**Website:** https://telelink.bnm.gov.my
**Purpose:** Financial fraud and banking scams

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript | Reactive UI |
| **AI Core** | Google GenAI SDK | Voice interaction |
| **Analysis** | `gemini-3-pro-preview` | Text analysis |
| **Audio** | Web Audio API | 16kHz PCM streaming |
| **Visualizer** | HTML5 Canvas | Audio visualization |

---

## 📊 Scam Patterns Detected

| Type | Keywords | Urgency |
|------|----------|---------|
| Macau Scam | warrant, arrest, police, court, PDRM | 🔴 Critical |
| Bank Scam | TAC, OTP, PIN, transfer, blocked | 🔴 Critical |
| LHDN Scam | LHDN, cukai, tax, refund, arrears | 🟠 High |
| Love Scam | parcel, customs, gift, overseas | 🟡 Medium |
| Investment Scam | guaranteed, profit, forex, crypto | 🟠 High |

---

## 📝 Evidence Report Format

The system generates PDRM-ready bilingual reports with:
- Case ID & Timestamp
- Suspect Information (phone number, claimed identity)
- Scam Classification & Type
- Bot Probability & AI Voice Analysis
- Detected Keywords
- Verification Attempts Q&A
- Inconsistencies Found
- Full Transcript
- Evidence Hash (SHA-256)
- Quality Score & Police Readiness Status
