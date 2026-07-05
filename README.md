# VeriCall Malaysia

**AI-assisted voice scam detection prototype for Malaysia**

[![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?style=flat-square)](https://flutter.dev)
[![React](https://img.shields.io/badge/React-Vite%20%7C%20TypeScript-61DAFB?style=flat-square)](https://react.dev)
[![Python](https://img.shields.io/badge/Python-Flask-3776AB?style=flat-square)](https://flask.palletsprojects.com)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%7C%20FCM%20%7C%20Auth-FFCA28?style=flat-square)](https://firebase.google.com)
[![Google Gemini](https://img.shields.io/badge/Google%20AI-Gemini-4285F4?style=flat-square)](https://ai.google.dev)
[![Made in Malaysia](https://img.shields.io/badge/Made%20in-Malaysia-CC0001?style=flat-square)]()

---

## Overview

VeriCall Malaysia is a prototype system that explores how AI, audio analysis, real-time alerts, and user education can help protect Malaysians from voice scam attempts.

The project focuses on common scam patterns such as bank impersonation, LHDN/PDRM impersonation, fake urgent payment requests, social engineering scripts, and voice-cloning risks. Instead of relying on only one detection method, VeriCall combines multiple signals from audio, conversation content, caller behaviour, and contextual verification.

The system includes:

* A **Flutter mobile app** for call monitoring, scam reports, alerts, and user training
* A **Python Flask backend** for scam analysis, audio-processing experiments, and threat scoring
* A **React/Vite web dashboard** for demo call simulation and live analysis
* **Firebase Firestore and FCM** for real-time sync and family alert notifications
* **Google Gemini-based analysis** for scam content reasoning, caller claim checks, and training scenario generation

> This is a prototype, not a production-ready replacement for telco-level scam blocking, police reporting, or bank fraud prevention systems.

---

## Why This Project Matters

Voice scams are becoming harder to detect because scammers may use real human callers, scripted social engineering, AI-generated voices, or cloned voices. Many detection tools focus mainly on whether a voice sounds synthetic, but real-world scams often depend more on what the caller says and how they pressure the victim.

VeriCall was built to explore a broader approach:

* Detect suspicious scam language and manipulation tactics
* Analyze whether the caller’s voice may be synthetic or suspicious
* Verify claimed organizations using external context
* Alert family members when a high-risk call is detected
* Train users through simulated scam scenarios
* Demonstrate how an AI decoy could delay scammers during a suspicious interaction

---

## Key Features

| Feature                             | Description                                                                                                      |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Multi-layer threat scoring          | Combines audio, content, behavioural, and contextual signals into a single risk assessment                       |
| Audio deepfake detection experiment | Uses WavLM and Gemini audio analysis to evaluate whether a voice may be synthetic                                |
| Scam content analysis               | Uses Gemini-based reasoning to detect suspicious language, threats, urgency, impersonation, and payment pressure |
| Caller claim verification           | Uses search-grounded checks to help verify claimed organizations or suspicious caller claims                     |
| Live call dashboard                 | Web interface for visualising call state, transcript, audio activity, and threat signals                         |
| Family alert network                | Sends push alerts to linked family members when a high-risk scam call is detected                                |
| Scam Vaccine training               | Provides voice-based scam simulation and response training for users                                             |
| Uncle Ah Hock AI decoy              | Demo AI persona designed to continue a suspicious conversation and waste scammer time                            |
| PDRM-style report generation        | Generates structured report data with transcript, score, timestamps, and evidence summary                        |
| Firebase real-time sync             | Keeps mobile, backend, and web demo state synchronized                                                           |

---

## Project Status

VeriCall is currently a prototype.

### Implemented

* Flutter mobile app screens for call monitoring, reports, alerts, settings, family linking, and scam training
* Flask backend API for threat analysis, Firebase sync, audio-processing experiments, and report generation
* React/Vite web dashboard for demo call simulation and live scam analysis
* Firestore-based real-time call state synchronization
* Firebase Cloud Messaging integration for family alerts
* Gemini-powered scam content analysis and training scenario generation
* WavLM-based audio deepfake detection experiment
* WebSocket audio relay for demo audio streaming
* Docker and local startup scripts

### Experimental

* Real-time audio risk scoring
* Anti-voice-cloning audio perturbation
* AI decoy conversation flow
* Grounded caller verification
* Auto-hangup decision rules
* Scam pattern retrieval and scoring fusion

### Future Work

* Real telco or OS-level call interception
* Production-grade privacy and security audit
* Larger benchmark testing across Malaysian languages and dialects
* Official police report submission integration
* Voice biometric verification for trusted contacts
* Community scam intelligence sharing
* WhatsApp / Telegram voice call protection

---

## System Architecture

```text
+--------------------------------------+
| Mobile App                           |
| Flutter                              |
|                                      |
| - Call monitoring UI                 |
| - Live scam risk display             |
| - Post-call threat report            |
| - Scam Vaccine training              |
| - Family alert management            |
+------------------+-------------------+
                   |
                   | REST API + Firestore sync
                   |
+------------------v-------------------+
| Backend API                          |
| Python Flask                         |
|                                      |
| - Threat Engine                      |
| - Audio deepfake detection           |
| - Gemini scam analysis               |
| - Firebase integration               |
| - WebSocket audio relay              |
| - Report generation                  |
+------------------+-------------------+
                   |
                   | HTTP + WebSocket + Firestore
                   |
+------------------v-------------------+
| Web Dashboard                        |
| React + Vite + TypeScript            |
|                                      |
| - Demo call simulation               |
| - Audio visualisation                |
| - Live transcript display            |
| - Threat analysis dashboard          |
| - Uncle Ah Hock decoy panel          |
+------------------+-------------------+
                   |
                   | Cloud services
                   |
+------------------v-------------------+
| Firebase + Google AI                 |
|                                      |
| - Firestore real-time database       |
| - Firebase Cloud Messaging           |
| - Firebase Auth                      |
| - Gemini API                         |
| - Grounding with Google Search       |
+--------------------------------------+
```

---

## Detection Approach

VeriCall uses a multi-signal approach instead of relying on one model only.

```text
Signal 1: Audio Deepfake Analysis
- WavLM-based audio representation
- Gemini audio analysis
- Synthetic voice risk signal

Signal 2: Scam Content Analysis
- Transcript and message analysis
- Suspicious intent detection
- Scam script and impersonation pattern recognition

Signal 3: Behavioural Pattern Analysis
- Urgency
- Threats
- Payment pressure
- Request for OTP or banking details
- Attempts to capture the user’s voice

Signal 4: Caller Claim Verification
- Organization claim checking
- Search-grounded context
- Malaysia-specific scam pattern lookup

Signal 5: User Protection Flow
- Risk report
- Family alert
- Training guidance
- AI decoy demo flow
```

The backend combines these signals into a threat score and returns a structured analysis result to the mobile app and web dashboard.

---

## Tech Stack

### Mobile App

| Technology              | Purpose                                      |
| ----------------------- | -------------------------------------------- |
| Flutter                 | Cross-platform mobile app                    |
| Dart                    | Mobile app programming language              |
| Firebase SDK            | Auth, Firestore sync, and push notifications |
| WebRTC / audio services | Demo audio capture and call simulation       |

### Backend

| Technology         | Purpose                                                 |
| ------------------ | ------------------------------------------------------- |
| Python             | Backend programming language                            |
| Flask              | REST API server                                         |
| WebSocket          | Real-time audio relay                                   |
| WavLM              | Audio deepfake detection experiment                     |
| Google Gemini API  | Scam reasoning, scenario generation, and audio analysis |
| Firebase Admin SDK | Firestore and FCM server integration                    |

### Web Dashboard

| Technology       | Purpose                    |
| ---------------- | -------------------------- |
| React            | Web interface              |
| Vite             | Frontend build tool        |
| TypeScript       | Safer frontend development |
| Firebase Web SDK | Real-time call state sync  |
| WebRTC           | Demo audio streaming       |

### Cloud / Services

| Technology               | Purpose                                     |
| ------------------------ | ------------------------------------------- |
| Firebase Firestore       | Real-time call state database               |
| Firebase Cloud Messaging | Family push alerts                          |
| Firebase Auth            | Anonymous or lightweight user identity      |
| Google AI / Gemini       | AI-powered scam analysis and training flows |

---

## Project Structure

```text
vericall-malaysia/
|
+-- backend/                          # Python Flask backend API
|   +-- app/
|   |   +-- api/
|   |   |   +-- routes.py             # API routes
|   |   +-- services/
|   |   |   +-- threat_orchestrator.py # Multi-signal threat scoring
|   |   |   +-- hangup_policy.py       # Auto-hangup decision rules
|   |   |   +-- deepfake_detector.py   # WavLM audio detection experiment
|   |   |   +-- gemini_audio_detector.py
|   |   |   +-- gemini_audio_analyzer.py
|   |   |   +-- scam_analyzer.py
|   |   |   +-- uncle_ah_hock.py
|   |   |   +-- scam_vaccine.py
|   |   |   +-- scam_intelligence.py
|   |   |   +-- scam_grounding.py
|   |   |   +-- firebase_service.py
|   |   |   +-- call_audio_bridge.py
|   |   |   +-- call_orchestrator.py
|   |   |   +-- retrieval_engine.py
|   |   |   +-- hybrid_detector.py
|   |   |   +-- pattern_learner.py
|   |   |   +-- redaction.py
|   |   |   +-- gemini_adapter.py
|   |   +-- config.py
|   +-- demo.py
|   +-- test_api.py
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- mobile/                            # Flutter mobile app
|   +-- lib/
|   |   +-- screens/
|   |   |   +-- home_screen.dart
|   |   |   +-- call_screen.dart
|   |   |   +-- incoming_call_screen.dart
|   |   |   +-- active_call_screen.dart
|   |   |   +-- call_report_screen.dart
|   |   |   +-- intelligence_screen.dart
|   |   |   +-- scam_vaccine_screen.dart
|   |   |   +-- family_link_screen.dart
|   |   |   +-- alerts_screen.dart
|   |   |   +-- settings_screen.dart
|   |   +-- services/
|   |   |   +-- api_service.dart
|   |   |   +-- audio_service.dart
|   |   |   +-- webrtc_service.dart
|   |   +-- main.dart
|   +-- pubspec.yaml
|
+-- uncle-ah-hock---johor-kopi-chat/   # React/Vite web dashboard
|   +-- App.tsx
|   +-- components/
|   |   +-- AudioVisualizer.tsx
|   |   +-- VictimPhone.tsx
|   +-- services/
|   |   +-- geminiService.ts
|   |   +-- firebaseService.ts
|   |   +-- webrtcService.ts
|   |   +-- scamAnalyzer.ts
|   |   +-- scamIntelligence.ts
|   |   +-- botDetector.ts
|   |   +-- contactVerifier.ts
|   |   +-- evidenceCollector.ts
|   |   +-- pdrmSubmit.ts
|   |   +-- apiKeyManager.ts
|   +-- Dockerfile
|   +-- nginx.conf
|
+-- docker-compose.yml
+-- start.bat
+-- start.sh
+-- SETUP.md
```

---

## Quick Start

### Option 1: Docker

```bash
docker compose up --build
```

### Option 2: One-Command Startup

Windows:

```bash
start.bat
```

macOS / Linux:

```bash
chmod +x start.sh
./start.sh
```

### Option 3: Manual Setup

#### Backend

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```

The backend runs on:

```text
http://localhost:5000
```

#### Web Dashboard

```bash
cd uncle-ah-hock---johor-kopi-chat
npm install
npm run dev
```

The web dashboard runs on:

```text
http://localhost:3000
```

#### Mobile App

```bash
cd mobile
flutter pub get
flutter run
```

For a physical device, pass the backend URL:

```bash
flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_LOCAL_IP:5000/api
```

---

## Environment Variables

### Backend `.env`

Create:

```text
backend/.env
```

Example:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_API_KEYS=optional_key_1,optional_key_2

FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_CREDENTIALS_PATH=path/to/firebase-service-account.json

PORT=5000
CALL_AUDIO_WS_PORT=8765

AUTO_HANGUP_ENABLED=true
```

### Web Dashboard `.env.local`

Create:

```text
uncle-ah-hock---johor-kopi-chat/.env.local
```

Example:

```env
VITE_API_KEY=your_gemini_api_key
VITE_BACKEND_URL=http://localhost:5000/api

VITE_FIREBASE_API_KEY=your_firebase_web_api_key
VITE_FIREBASE_PROJECT_ID=your_firebase_project_id
```

### Mobile App

Pass the backend URL using Dart define:

```bash
flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_LOCAL_IP:5000/api
```
