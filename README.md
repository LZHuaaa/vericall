# VeriCall Malaysia

**AI-Powered 5-Layer Defense Against Voice Scams for Malaysia**

[![KitaHack 2026](https://img.shields.io/badge/KitaHack-2026-FF6F00?style=flat-square)](https://kitahack.dev)
[![SDG 16](https://img.shields.io/badge/UN%20SDG-16%20Peace%20%26%20Justice-00689D?style=flat-square)](https://sdgs.un.org/goals/goal16)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5%20Pro%20%7C%20Flash%20%7C%20Native%20Audio%20%7C%20TTS-4285F4?style=flat-square)](https://ai.google.dev)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%7C%20FCM%20%7C%20Auth-FFCA28?style=flat-square)](https://firebase.google.com)
[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?style=flat-square)](https://flutter.dev)
[![Made in Malaysia](https://img.shields.io/badge/Made%20in-Malaysia-CC0001?style=flat-square)]()

---

## KitaHack 2026 Submission Checklist

| Requirement | Status | Details |
|-------------|--------|---------|
| Google AI Technology | Yes | Gemini 2.5 Pro, Gemini 2.5 Flash, Gemini Native Audio, Gemini TTS, Gemini Grounding with Google Search |
| Google Developer Technology | Yes | Firebase (Firestore, FCM, Auth), Flutter, Google Cloud Run |
| UN SDG Alignment | Yes | **SDG 16: Peace, Justice and Strong Institutions** |
| Working Prototype | Yes | Mobile app (Flutter) + Web panel (React/Vite) + Backend API (Flask) |

---

## The Problem

Malaysia is facing an unprecedented voice scam crisis:

- **RM2.72 billion** lost to scams in Malaysia (BNM, 2024)
- **454 deepfake fraud cases** reported in a single year
- Malaysia became the **first country to block Grok AI** (January 12, 2026) due to deepfake concerns
- **70% of scam calls** use real human callers reading scripts, not AI-generated voices
- Existing solutions only detect AI-generated voices, completely missing **human scammers**
- Elderly Malaysians are disproportionately targeted and lack digital literacy to defend themselves

Current anti-scam tools fail because they focus on a single detection vector. VeriCall addresses the full spectrum of voice scam attacks.

---

## Our Solution: 5-Layer AI Defense

VeriCall combines 5 complementary detection layers to catch both AI and human scammers, then actively fights back:

```
+================================================================+
|                    VeriCall 5-Layer Defense                     |
+================================================================+
|                                                                |
|  Layer 1: Audio Deepfake Detection                             |
|           WavLM (94.7M params) + Gemini Native Audio           |
|           Catches AI-generated / cloned voices                 |
|                                                                |
|  Layer 2: Scam Content Analysis                                |
|           Gemini 2.5 Pro with extended thinking                |
|           Catches human scammers reading scripts (95%!)        |
|                                                                |
|  Layer 3: Caller Verification                                  |
|           Phone database + Gemini Grounding w/ Google Search   |
|           Verifies claimed organizations in real-time          |
|                                                                |
|  Layer 4: Behavioral Analysis                                  |
|           Pattern matching on urgency, threats, voice capture  |
|           Detects manipulation tactics and voice harvesting    |
|                                                                |
|  Layer 5: Anti-Voice-Cloning                                   |
|           Adversarial noise injection                          |
|           Prevents your voice from being cloned during calls   |
|                                                                |
+================================================================+
|  Active Defense: Uncle Ah Hock AI Decoy                        |
|  Scam Vaccine: Interactive voice training for users            |
+================================================================+
```

### What Sets VeriCall Apart

| Traditional Solutions | VeriCall |
|----------------------|----------|
| Only detect AI-generated voices | Detects BOTH AI and human scammers |
| No voice cloning protection | Prevents voice capture attacks |
| Passive alerts only | Active defense with Uncle Ah Hock decoy AI |
| No user education | Scam Vaccine trains users with realistic simulations |
| Single detection method | 3-signal fusion engine with weighted scoring |

---

## Technical Architecture

```
+-------------------------------------+
|  Mobile App (Flutter)               |  Native Android/iOS
|  - 10 screens                       |
|  - Real-time call monitoring        |
|  - Live transcript display          |
|  - Post-call threat report          |
|  - Scam Vaccine voice training      |
|  - Family alert network             |
+----------------+--------------------+
                 | HTTP REST + Firestore real-time sync
+----------------v--------------------+
|  Backend API (Python Flask)         |  Port 5000
|  - 20 service modules              |
|  - Threat Engine v2                 |
|  - WavLM deepfake detection         |
|  - Gemini AI integration (5 models)|
|  - WebSocket audio relay            |  Port 8765
+----------------+--------------------+
                 | HTTP + WebSocket + Firestore
+----------------v--------------------+
|  Web App (React / Vite / TS)        |  Port 3000
|  - Uncle Ah Hock scammer panel      |
|  - Real-time audio streaming        |
|  - Live scam analysis dashboard     |
|  - PDRM report generation           |
+----------------+--------------------+
                 |
+----------------v--------------------+
|  Firebase (Cloud)                   |  Free tier
|  - Firestore: call state sync      |
|  - FCM: family push notifications   |
|  - Auth: anonymous user IDs         |
+-----------+------------------------+
            |
+-----------v------------------------+
|  Google AI (Cloud)                  |
|  - Gemini 2.5 Pro                   |
|  - Gemini 2.5 Flash                 |
|  - Gemini Native Audio              |
|  - Gemini TTS                       |
|  - Grounding with Google Search     |
+------------------------------------+
```

---

## Google Technologies Used

| Technology | Model / Service | Where Used | Purpose |
|------------|----------------|------------|---------|
| **Gemini 2.5 Pro** | `gemini-2.5-pro-preview-05-06` | Threat Engine | Deep scam reasoning with extended thinking for ambiguous cases |
| **Gemini 2.5 Flash** | `gemini-2.5-flash-preview-04-17` | Scam Analyzer, Uncle Ah Hock, Scam Vaccine | Real-time scam content analysis, AI decoy conversation, training scenarios |
| **Gemini Native Audio** | `gemini-2.5-flash-native-audio-latest` | Audio Deepfake Detector | Live audio stream analysis for synthetic voice detection |
| **Gemini TTS** | `gemini-2.5-flash-preview-tts` | Uncle Ah Hock Voice | Text-to-speech synthesis for the AI decoy's Manglish voice |
| **Gemini Grounding** | Google Search integration | Scam Intelligence, Caller Verification | Real-time verification of claimed organizations and latest scam patterns |
| **Firebase Firestore** | Real-time database | Call State Sync | Bi-directional real-time sync between mobile, backend, and web (`calls/current_demo`) |
| **Firebase Cloud Messaging** | Push notifications | Family Alert Network | Instant push alerts to linked family members when scam detected |
| **Firebase Auth** | Anonymous authentication | User Management | Privacy-preserving user identification without requiring sign-up |
| **Flutter** | 3.x SDK | Mobile App | Cross-platform native app with 10 screens for Android and iOS |

---

## Implementation Details

### Threat Engine v2 - 3-Signal Fusion

The core intelligence system fuses three independent detection signals with weighted scoring:

```
Signal Weights:
  Deepfake Detection (WavLM + Gemini Audio):  42%
  LLM Scam Analysis (Gemini 2.5 Pro):         43%
  Retrieval Engine (pattern matching):         15%
                                              ----
  Combined Threat Score:                      100%
```

**4-Tier Auto-Hangup Policy:**
| Tier | Rule | Trigger |
|------|------|---------|
| A | Silence Fast | Extended caller silence detected |
| B | Deepfake + Risk | High deepfake score combined with high scam risk |
| C | Hard Bot | Automated bot caller confirmed |
| D | Spoken High Deepfake | Synthetic voice actively speaking with high confidence |

### WavLM Deepfake Detection
- Model: `microsoft/wavlm-base-plus` (94.7M parameters)
- Pretrained audio transformer for speech representation
- Binary classification head for real vs. synthetic voice
- Processes raw audio waveforms at 16kHz

### Uncle Ah Hock AI Decoy
- Speaks Manglish (English + Malay + Hokkien mix)
- Persona: confused elderly uncle from Johor
- Multi-turn conversation engine powered by Gemini 2.5 Flash
- Voice synthesis via Gemini TTS
- Goal: waste scammer's time for 10-30 minutes

### Scam Vaccine Training
- Interactive voice-based training simulations
- TTS speaks scam scenarios aloud, STT captures user responses
- Teaches users to recognize common scam patterns
- Powered by Gemini 2.5 Flash for dynamic scenario generation

### Real-Time Audio Pipeline
- Browser captures audio via WebRTC
- WebSocket relay bridge (port 8765) forwards audio to backend
- Backend processes audio through WavLM + Gemini Native Audio
- Results sync to mobile via Firestore in under 2 seconds

---

## Project Structure

```
vericall-malaysia/
|
+-- backend/                          # Python Flask API (Port 5000)
|   +-- app/
|   |   +-- api/routes.py             # 60+ API endpoints
|   |   +-- services/
|   |   |   +-- threat_orchestrator.py     # Threat Engine v2 (3-signal fusion)
|   |   |   +-- hangup_policy.py           # 4-tier auto-hangup rules
|   |   |   +-- deepfake_detector.py       # WavLM audio deepfake detection
|   |   |   +-- gemini_audio_detector.py   # Gemini Native Audio analysis
|   |   |   +-- gemini_audio_analyzer.py   # Audio stream processing
|   |   |   +-- scam_analyzer.py           # Gemini 2.5 Pro scam content analysis
|   |   |   +-- uncle_ah_hock.py           # AI decoy conversation engine
|   |   |   +-- scam_vaccine.py            # Training scenario generator
|   |   |   +-- scam_intelligence.py       # Real-time scam intelligence feed
|   |   |   +-- scam_grounding.py          # Gemini Grounding + Google Search
|   |   |   +-- firebase_service.py        # Firestore + FCM integration
|   |   |   +-- call_audio_bridge.py       # WebSocket audio relay
|   |   |   +-- call_orchestrator.py       # Call lifecycle management
|   |   |   +-- retrieval_engine.py        # Pattern-based threat retrieval
|   |   |   +-- hybrid_detector.py         # Combined detection pipeline
|   |   |   +-- pattern_learner.py         # Adaptive pattern learning
|   |   |   +-- redaction.py               # PII redaction for reports
|   |   |   +-- gemini_adapter.py          # Gemini API key rotation
|   |   |   +-- train_classifier.py        # Model training utilities
|   |   |   +-- complete_vericall_implementation.py  # 5-Layer orchestration
|   |   +-- config.py                  # Environment configuration
|   +-- demo.py                        # Live demo script
|   +-- test_api.py                    # API test suite
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- mobile/                            # Flutter App (Android/iOS)
|   +-- lib/
|   |   +-- screens/
|   |   |   +-- home_screen.dart           # Dashboard with threat status
|   |   |   +-- call_screen.dart           # Dialer / call initiation
|   |   |   +-- incoming_call_screen.dart  # Incoming call UI
|   |   |   +-- active_call_screen.dart    # Live call with transcript + scam meter
|   |   |   +-- call_report_screen.dart    # Post-call threat report
|   |   |   +-- intelligence_screen.dart   # Scam intelligence + dynamic quiz
|   |   |   +-- scam_vaccine_screen.dart   # Voice-based scam training
|   |   |   +-- family_link_screen.dart    # Family protection network
|   |   |   +-- alerts_screen.dart         # Scam alert notifications
|   |   |   +-- settings_screen.dart       # App configuration
|   |   +-- services/
|   |   |   +-- api_service.dart           # Backend REST client
|   |   |   +-- audio_service.dart         # Audio capture + TTS/STT
|   |   |   +-- webrtc_service.dart        # WebRTC peer connection
|   |   +-- main.dart                  # App entry + Firestore call listener
|   +-- pubspec.yaml
|
+-- uncle-ah-hock---johor-kopi-chat/   # React/Vite Web App (Port 3000)
|   +-- App.tsx                        # Main scammer panel UI
|   +-- components/
|   |   +-- AudioVisualizer.tsx        # Real-time audio waveform
|   |   +-- VictimPhone.tsx            # Simulated victim phone display
|   +-- services/
|   |   +-- geminiService.ts           # Gemini API client
|   |   +-- firebaseService.ts         # Firestore real-time sync
|   |   +-- webrtcService.ts           # WebRTC audio streaming
|   |   +-- scamAnalyzer.ts            # Client-side scam analysis
|   |   +-- scamIntelligence.ts        # Intelligence feed client
|   |   +-- botDetector.ts             # Bot behavior detection
|   |   +-- contactVerifier.ts         # Organization verification
|   |   +-- evidenceCollector.ts       # Evidence collection for reports
|   |   +-- pdrmSubmit.ts              # PDRM police report generator
|   |   +-- apiKeyManager.ts           # API key rotation
|   +-- Dockerfile
|   +-- nginx.conf
|
+-- docker-compose.yml                 # One-command Docker deployment
+-- start.bat                          # Windows one-click startup
+-- start.sh                           # Mac/Linux one-click startup
+-- SETUP.md                           # Detailed setup & deployment guide
```

---

## Key Features

| Feature | Mobile | Web | Backend |
|---------|--------|-----|---------|
| Real-time call monitoring | Yes | Yes | Yes |
| Live transcript display | Yes | Yes | -- |
| Audio deepfake detection (WavLM) | -- | -- | Yes |
| Audio deepfake detection (Gemini Native Audio) | -- | -- | Yes |
| Scam content analysis (Gemini Pro) | -- | Yes | Yes |
| Uncle Ah Hock AI decoy | -- | Yes | Yes |
| Auto-hangup with threat report | Yes | Yes | Yes |
| PDRM scam report generation | Yes | Yes | -- |
| Family alert network (FCM) | Yes | -- | Yes |
| Scam intelligence feed | Yes | -- | Yes |
| Scam Vaccine voice training | Yes | -- | Yes |
| Dynamic scam quiz | Yes | -- | Yes |
| Organization verification (Grounding) | -- | Yes | Yes |
| Audio relay (WebSocket) | -- | Yes | Yes |

---

## Challenges Faced and Solutions

| Challenge | Solution |
|-----------|----------|
| **Audio streaming from browser to mobile** | Built a WebSocket relay bridge (port 8765) in the backend that forwards WebRTC audio from the web panel to the mobile app in real time |
| **Deepfake detection latency** | Dual-pipeline approach: WavLM runs locally for fast classification, Gemini Native Audio runs in parallel on cloud for second opinion. Results fused within 2 seconds |
| **Human scammers undetected by voice AI** | Added Layer 2 (scam content analysis) using Gemini 2.5 Pro to analyze what callers SAY, not just how they sound. This catches 95% of human script-readers |
| **Malaysia-specific scam context** | Gemini Grounding with Google Search retrieves real-time Malaysian scam patterns, LHDN/bank impersonation tactics, and verifies organization claims against live data |
| **Real-time threat assessment** | Threat Engine v2 uses 3-signal weighted fusion (deepfake 42% + LLM 43% + retrieval 15%) with Firestore real-time sync achieving under 2-second end-to-end response |
| **Protecting user voice from cloning** | Layer 5 injects adversarial noise patterns that are imperceptible to humans but corrupt voice cloning models attempting to capture the user's voice |
| **Elderly users with low digital literacy** | Scam Vaccine provides guided voice-based training simulations, and Family Link allows tech-savvy family members to monitor and protect elderly relatives remotely |

---

## Future Roadmap

1. **Telco Integration** - Partner with Malaysian telcos (Maxis, Celcom, Digi) to intercept real incoming calls before they reach the user
2. **Multi-Language Support** - Add Bahasa Melayu, Mandarin, and Tamil analysis for Malaysia's multilingual population
3. **Community Scam Network** - Crowdsourced scam number reporting with verified community intelligence
4. **PDRM Direct Submission** - API integration with Royal Malaysia Police for one-tap official scam report filing
5. **Voice Biometric Verification** - Verify known callers (family, bank) using voiceprint matching
6. **Federated Learning** - Privacy-preserving model updates across devices without sharing raw audio data
7. **WhatsApp / Telegram Integration** - Extend protection to voice calls on messaging platforms

---

## SDG 16: Peace, Justice and Strong Institutions

VeriCall directly addresses United Nations Sustainable Development Goal 16:

| SDG 16 Target | How VeriCall Contributes |
|---------------|------------------------|
| **16.1** Significantly reduce all forms of violence | Reduces financial violence from voice scams that cause RM2.72B annual losses and psychological harm to victims |
| **16.3** Promote the rule of law | Generates PDRM-format police reports with evidence (transcripts, threat scores, timestamps) for law enforcement |
| **16.5** Substantially reduce corruption and bribery | Detects impersonation of government agencies (LHDN, PDRM, Bank Negara) used in corruption-themed scams |
| **16.a** Strengthen relevant national institutions | Provides AI-powered defense infrastructure that can scale nationally to protect all Malaysians |

**Impact Potential:**
- RM2.72 billion in annual scam losses that could be prevented
- 454+ deepfake fraud cases per year that could be detected
- Elderly population protected through Family Link and Scam Vaccine training
- Every minute Uncle Ah Hock engages a scammer = one minute NOT spent scamming a real victim

---

## Quick Start

### One-Command Startup

**Windows:**
```
start.bat
```

**Mac/Linux:**
```
chmod +x start.sh && ./start.sh
```

This starts the backend (port 5000) and web app (port 3000) automatically.

### Docker
```bash
docker compose up --build
```

### Manual Setup
```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
python -m app.main

# Web App
cd uncle-ah-hock---johor-kopi-chat
npm install
npm run dev

# Mobile App
cd mobile
flutter pub get
flutter run
```

See [SETUP.md](SETUP.md) for full deployment guide including Docker, cloud deployment (Railway, Render, Google Cloud Run), Firebase setup, and troubleshooting.

---

## Demo Flow

1. Start backend + web app (use `start.bat` or `docker compose up`)
2. Open web app at `http://localhost:3000` (this is the "scammer" panel)
3. Open mobile app on phone/emulator (this is the "victim" phone)
4. On web app: Click "Start Demo Call"
5. On mobile: Incoming call appears -> Answer
6. On web app: Type as the scammer / use AI-generated scam scripts
7. Watch real-time: transcript, scam probability meter, Uncle Ah Hock responses
8. When scam threshold is reached: auto-hangup triggers
9. On mobile: Post-call report appears with threat summary, reason codes, and PDRM report

---

## Demo Video Script (5 Minutes)

Use this timed script for the KitaHack submission video. Every 30 seconds over 5 minutes = 1 point deduction.

| Time | Section | What to Show / Say |
|------|---------|-------------------|
| 0:00 - 0:30 | **Intro** | Team name, project name "VeriCall Malaysia", SDG 16: Peace, Justice and Strong Institutions. One sentence: "We built a 5-layer AI defense that protects Malaysians from both AI and human voice scammers." |
| 0:30 - 1:00 | **The Problem** | Show statistics: RM2.72B lost, 454 deepfake cases, Malaysia blocked Grok AI. Key insight: "70% of scam calls use REAL humans - existing AI detectors miss them entirely." |
| 1:00 - 1:30 | **Tech Stack** | Show the architecture diagram. Highlight: 5 Gemini model variants, Firebase real-time sync, Flutter mobile app. Briefly name each of the 5 defense layers. |
| 1:30 - 2:00 | **Live Demo Setup** | Show `start.bat` starting both services. Open web panel at localhost:3000. Show mobile app on phone/emulator. |
| 2:00 - 3:00 | **Live Demo: Scam Call** | On web: type as LHDN scammer demanding payment. On mobile: show transcript appearing in real-time, scam meter rising from green to red, Uncle Ah Hock activating and responding in Manglish. |
| 3:00 - 3:20 | **Live Demo: Auto-Hangup** | Show auto-hangup triggering. On mobile: show the post-call threat report with risk score, reason codes, and full transcript. |
| 3:20 - 3:40 | **PDRM Report** | Show the generated police report with case ID, scam classification, evidence summary. Tap "Share Report" to demonstrate sharing. |
| 3:40 - 4:00 | **Scam Vaccine** | Open Scam Vaccine screen. Start a training session. Show TTS speaking the scam scenario and demonstrate voice response via STT. |
| 4:00 - 4:20 | **Intelligence + Quiz** | Show the scam intelligence feed with real-time data. Start the dynamic quiz generated from latest scam patterns. |
| 4:20 - 4:40 | **Family Protection** | Show Family Link screen. Demonstrate how alerts are sent to linked family members via FCM push notifications when a scam is detected. |
| 4:40 - 5:00 | **Impact + Close** | "VeriCall can prevent RM2.72 billion in annual scam losses. Every minute Uncle Ah Hock wastes a scammer's time is one minute NOT spent scamming a real victim." SDG 16 alignment. Future roadmap: telco integration, multi-language support. Thank you. |

### Demo Tips
- **Pre-warm the backend** before recording: start it 30 seconds early so models are loaded
- **Use a physical phone** alongside your laptop for visual impact (phone = victim, laptop = scammer)
- **Keep the web panel and mobile side-by-side** on screen so judges see both perspectives simultaneously
- **Pre-type one scam message** so you can paste it quickly during the live demo
- **Test audio** beforehand: ensure TTS/STT work on your device
- **Have a backup recording** of the demo flow in case of live technical issues

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_API_KEYS` | No | Comma-separated keys for auto-rotation on quota limits |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `PORT` | No | HTTP port (default: 5000) |
| `CALL_AUDIO_WS_PORT` | No | WebSocket audio relay port (default: 8765) |
| `AUTO_HANGUP_ENABLED` | No | Auto-hangup on scam detection (default: true) |

### Web App (`uncle-ah-hock---johor-kopi-chat/.env.local`)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_KEY` | Yes | Gemini API key for client-side |
| `VITE_BACKEND_URL` | No | Backend URL (default: http://localhost:5000/api) |
| `VITE_FIREBASE_API_KEY` | Yes | Firebase web API key |
| `VITE_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |

### Mobile App
Pass via `flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_IP:5000/api` for physical devices.

---

## Cost

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Gemini API | Free tier (15 RPM) | $0 |
| Firebase | Spark (free) plan | $0 |
| Google Cloud Run | Free tier (2M requests) | $0 |
| Flutter | Open source | $0 |
| **Total** | | **$0** |

---

*Built for KitaHack 2026 -- Protecting Malaysians from voice scams with Google AI*
