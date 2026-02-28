# VeriCall Malaysia - Complete Function Reference & Testing Guide

## 🎯 Quick Start

```bash
cd backend

# Run component tests (no server needed)
set PYTHONIOENCODING=utf-8 && python test_backend.py

# Start API server
set PYTHONIOENCODING=utf-8 && python -m app.main

# Run API tests (separate terminal, with server running)
set PYTHONIOENCODING=utf-8 && python test_api.py
```

---

## 📦 Backend Services (11 modules)

### 1. DeepfakeDetector (`deepfake_detector.py`)
**Purpose:** Detects AI-generated voices using WavLM model

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `analyze_audio(path)` | Analyze audio file | File path | `DeepfakeAnalysis` |
| `analyze_audio_bytes(bytes)` | Real-time streaming | Raw bytes | `DeepfakeAnalysis` |
| `_heuristic_detection()` | Fallback detection | Waveform | Score 0-1 |

**Test:**
```bash
python test_backend.py  # Test #5
```

---

### 2. ScamAnalyzer (`scam_analyzer.py`)
**Purpose:** Analyzes call transcripts for Malaysian scam patterns using Gemini

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `analyze_content_sync()` | Scam detection | Transcript + score | `ScamAnalysis` |
| `analyze_content()` | Async version | Transcript + score | `ScamAnalysis` |
| `_fallback_analysis()` | Keyword matching | Transcript | `ScamAnalysis` |

**Test:**
```bash
python test_backend.py  # Test #4
```

---

### 3. UncleAhHock (`uncle_ah_hock.py`)
**Purpose:** AI decoy that wastes scammer's time

| Function | Purpose | Returns |
|----------|---------|---------|
| `start_session()` | Start decoy session | Session ID |
| `generate_response(session_id, text)` | Get Uncle's reply | Response text |
| `end_session(session_id)` | End & get stats | Stats dict |
| `get_session_stats(session_id)` | Current stats | Stats dict |

**Test:**
```bash
python test_backend.py  # Test #3
```

---

### 4. HybridDetector (`hybrid_detector.py`)
**Purpose:** Combines WavLM + Gemini for best accuracy

| Function | Purpose | Mode Options |
|----------|---------|--------------|
| `analyze(audio_path, mode)` | Hybrid analysis | FAST, ACCURATE, WAVLM_ONLY, GEMINI_ONLY |
| `analyze_call(audio_path, transcript)` | Full pipeline | Auto |

---

### 5. FirebaseService (`firebase_service.py`)
**Purpose:** Firestore database for scam reports & family alerts

| Function | Purpose |
|----------|---------|
| `report_scam(data)` | Save scam report |
| `get_recent_scams(limit)` | Get community reports |
| `save_evidence(report_id, data)` | Store call evidence |
| `track_scam_pattern(type, keywords)` | Analytics tracking |
| `send_family_alert(user_id, scam_type, risk)` | FCM push notification |

---

### 6. GeminiAudioDetector (`gemini_audio_detector.py`)
**Purpose:** Deepfake detection using Gemini Native Audio

| Function | Purpose |
|----------|---------|
| `analyze_audio(path)` | Gemini-based detection |
| `analyze_audio_async(path)` | Async version |

---

### 7. ScamIntelligence (`scam_intelligence.py`)
**Purpose:** Real-time scam trends with Google Search grounding

| Function | Purpose |
|----------|---------|
| `get_intelligence()` | Get active scam trends |

---

## 🌐 API Endpoints

### Call Analysis

| Endpoint | Method | Audio? | Purpose |
|----------|--------|--------|---------|
| `/api/analyze` | POST | ✅ Yes | WavLM + Scam analysis |
| `/api/analyze/text` | POST | ❌ No | Text-only scam detection |
| `/api/analyze/pipeline` | POST | ✅ Yes | Full 3-stage hybrid |
| `/api/analyze/complete` | POST | ⚠️ Optional | 5-layer defense |

### Uncle Ah Hock Decoy

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/decoy/start` | POST | Start decoy session |
| `/api/decoy/respond` | POST | Get Uncle's response |
| `/api/decoy/end` | POST | End session, get stats |

### Firebase / Reports

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/reports` | POST | Submit scam report |
| `/api/reports/recent` | GET | Get community reports |
| `/api/reports/stats` | GET | Aggregated statistics |
| `/api/evidence` | POST | Save call evidence |
| `/api/evidence/<id>` | GET | Get evidence by report |
| `/api/analytics/pattern` | POST | Track scam pattern |
| `/api/analytics/trending` | GET | Get trending scams |

### Family Protection

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/family/alert` | POST | Send FCM alert to family |

---

## 🧪 Testing Commands

### 1️⃣ Component Tests (No Server)

```bash
cd backend
set PYTHONIOENCODING=utf-8 && python test_backend.py
```

**Tests:**
- ✅ Imports
- ✅ Flask App
- ✅ Deepfake Detector (heuristic)
- ✅ Scam Analyzer
- ✅ Uncle Ah Hock

---

### 2️⃣ API Tests (Server Required)

**Terminal 1 - Start Server:**
```bash
cd backend
set PYTHONIOENCODING=utf-8 && python -m app.main
```

**Terminal 2 - Run Tests:**
```bash
cd backend
set PYTHONIOENCODING=utf-8 && python test_api.py
```

**Tests:**
- ✅ API Health
- ✅ Scam Analysis (multiple scenarios)
- ✅ Uncle Ah Hock conversation
- ✅ 5-Layer Defense (no audio)
- ✅ Intelligence endpoint

---

### 3️⃣ Manual API Testing with curl

**Text Analysis:**
```bash
curl -X POST http://localhost:5000/api/analyze/text ^
  -H "Content-Type: application/json" ^
  -d "{\"transcript\": \"This is LHDN. You owe RM8000 tax!\"}"
```

**Uncle Ah Hock:**
```bash
# Start session
curl -X POST http://localhost:5000/api/decoy/start

# Send scammer text (replace SESSION_ID)
curl -X POST http://localhost:5000/api/decoy/respond ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\": \"SESSION_ID\", \"scammer_text\": \"You owe tax!\"}"
```

**5-Layer Defense:**
```bash
curl -X POST http://localhost:5000/api/analyze/complete ^
  -H "Content-Type: application/json" ^
  -d "{\"transcript\": \"This is LHDN calling about your tax\", \"caller_number\": \"+60123456789\"}"
```

**Full Pipeline (with audio):**
```bash
curl -X POST http://localhost:5000/api/analyze/pipeline ^
  -F "audio=@test_call.wav" ^
  -F "transcript=Hello this is LHDN"
```

---

## 📱 Uncle Ah Hock Frontend (`uncle-ah-hock---johor-kopi-chat/`)

### Key Services

| File | Purpose |
|------|---------|
| `geminiService.ts` | Gemini Live voice connection |
| `botDetector.ts` | Silence/bot detection |
| `evidenceCollector.ts` | Forensic evidence gathering |
| `scamAnalyzer.ts` | Real-time scam scoring |
| `contactVerifier.ts` | Known contact detection |
| `firebaseService.ts` | Backend API bridge |

### Test Frontend

```bash
cd uncle-ah-hock---johor-kopi-chat
npm install
npm run dev
```

---

## 🔑 Environment Variables

Create `backend/.env`:
```
GEMINI_API_KEY=your_gemini_api_key
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

---

## ✅ KitaHack Compliance

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| Google AI | Gemini 2.5 Flash (Live Voice) | ✅ |
| Google Tech | Firebase Firestore + FCM | ✅ |
| Prototype | Working backend + frontend | ✅ |
