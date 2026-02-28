# VeriCall Malaysia - Backend API

🛡️ **5-Layer AI Defense System for Voice Scam Protection**

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
copy .env.example .env
# Add your GEMINI_API_KEY to .env
# Optional: add GEMINI_API_KEYS=key1,key2,key3 for auto-rotation on quota limits
# Optional: set FIREBASE_CREDENTIALS_PATH to your Firebase service account JSON absolute path

# Run server
python -m app.main

# Run demo (in another terminal)
python demo.py

# Run tests
python test_api.py
```

## 🛡️ 5-Layer Defense System

| Layer | Technology | Catches |
|-------|------------|---------|
| **1. Audio Detection** | WavLM + Gemini Native Audio | AI-generated voices (30%) |
| **2. Content Analysis** | Gemini 2.5 Pro | Scam scripts - AI OR human (95%) |
| **3. Caller Verification** | Phone database | Spoofed caller IDs |
| **4. Behavioral Analysis** | Pattern matching | Manipulation, voice capture attempts |
| **5. Anti-Cloning** | Adversarial noise | Prevents voice cloning attacks |

## API Endpoints

### 🔴 Core Analysis (NEW!)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analyze/complete` | POST | **5-Layer Defense** (no audio needed!) |
| `/api/analyze/pipeline` | POST | Full audio pipeline (WavLM + Gemini) |
| `/api/analyze/text` | POST | Text-only scam analysis |
| `/api/analyze` | POST | Audio file analysis |

### 🎭 Uncle Ah Hock Decoy
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/decoy/start` | POST | Start decoy session |
| `/api/decoy/respond` | POST | Get Uncle's response |
| `/api/decoy/end` | POST | End session, get stats |

### 🌐 Intelligence
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/intelligence` | GET | Latest scam reports |
| `/api/family/alert` | POST | Alert family members |

## Quick Test

```bash
# 5-Layer Defense Analysis (No audio needed!)
curl -X POST http://localhost:5000/api/analyze/complete \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "This is LHDN. Pay RM8000 tax now or police arrest!",
    "caller_number": "+60123456789",
    "claimed_organization": "LHDN"
  }'

# Expected: threat_level: "high", layers showing scam detection
```

## Demo Script

```bash
python demo.py
```

Options:
1. **Full presentation** - Problem → Solution → Live demo → Uncle Ah Hock
2. **Quick demo** - Live detection only
3. **Uncle Ah Hock only** - Crowd favorite!

## Project Structure

```
backend/
├── app/
│   ├── api/routes.py                      # API endpoints
│   ├── services/
│   │   ├── complete_vericall_implementation.py  # 5-Layer Defense
│   │   ├── deepfake_detector.py           # WavLM detection
│   │   ├── gemini_audio_detector.py       # Gemini Native Audio
│   │   ├── scam_analyzer.py               # Content analysis
│   │   ├── uncle_ah_hock.py               # AI decoy
│   │   ├── scam_intelligence.py           # Real-time intel
│   │   └── hybrid_detector.py             # Combined pipeline
│   └── config.py                          # Configuration
├── demo.py                                # KitaHack demo script
├── test_api.py                            # API test suite
└── requirements.txt                       # Dependencies
```

## Google Technologies Used

| Technology | Purpose |
|------------|---------|
| Gemini 2.5 Pro | Scam content analysis |
| Gemini Native Audio | Audio deepfake detection |
| Gemini Grounding | Real-time scam intelligence |
| Firebase | User data, notifications |
| Flutter | Mobile app |

---

**Built for KitaHack 2026 🇲🇾**
