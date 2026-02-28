# VeriCall Malaysia - Setup & Deployment Guide

## Quick Start (No Docker)

### Prerequisites
- Python 3.11+ ([python.org](https://www.python.org/downloads/))
- Node.js 18+ ([nodejs.org](https://nodejs.org/))
- Flutter 3.x ([flutter.dev](https://flutter.dev/docs/get-started/install))
- Git

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

### Manual Setup

#### 1. Backend (Python Flask + Gemini AI)
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```
Backend runs at `http://localhost:5000`

#### 2. Web App (Uncle Ah Hock Scammer Panel)
```bash
cd uncle-ah-hock---johor-kopi-chat
npm install
npm run dev
```
Web app runs at `http://localhost:3000`

#### 3. Mobile App (Flutter - Victim Phone)
```bash
cd mobile
flutter pub get

# Android Emulator (auto-connects to localhost backend)
flutter run

# Physical Android device on same WiFi
flutter run --dart-define=VERICALL_API_BASE_URL=http://YOUR_COMPUTER_IP:5000/api
```

> **Finding your IP:** Run `ipconfig` (Windows) or `ifconfig` (Mac/Linux) and use the WiFi adapter IPv4 address.

---

## Docker Deployment

### Prerequisites
- Docker Desktop ([docker.com](https://www.docker.com/products/docker-desktop/))

### Start Everything
```bash
docker compose up --build
```

This starts:
- Backend API at `http://localhost:5000`
- Web App at `http://localhost:3000`
- Audio Relay at `ws://localhost:8765`

### Stop
```bash
docker compose down
```

---

## Free Cloud Deployment Options

### Option A: Railway (Recommended for hackathons)

1. Sign up at [railway.app](https://railway.app/) (free tier: 500 hours/month)
2. Connect your GitHub repo
3. Deploy backend:
   - New Project > Deploy from GitHub > select `backend/` folder
   - Add environment variables from `backend/.env`
   - Railway auto-detects Python and deploys
4. Deploy web:
   - Add another service > select `uncle-ah-hock---johor-kopi-chat/` folder
   - Set `VITE_BACKEND_URL` to the backend's Railway URL + `/api`

### Option B: Render

1. Sign up at [render.com](https://render.com/) (free tier available)
2. New Web Service > connect GitHub
3. Backend: Set build command `pip install -r requirements.txt`, start command `gunicorn --bind 0.0.0.0:$PORT --timeout 120 --workers 1 app.main:app`
4. Web: New Static Site, build command `npm run build`, publish directory `dist`

### Option C: Google Cloud Run (Free tier: 2M requests/month)

```bash
# Backend
cd backend
gcloud run deploy vericall-backend --source . --allow-unauthenticated

# Web (build and deploy static)
cd uncle-ah-hock---johor-kopi-chat
npm run build
# Deploy dist/ to Firebase Hosting (free)
firebase deploy --only hosting
```

---

## Architecture

```
┌─────────────────────────────────┐
│  Mobile App (Flutter)           │  Port: N/A (native app)
│  - Victim's phone               │
│  - Receives calls               │
│  - Shows live transcript         │
│  - Post-call reports            │
└──────────┬──────────────────────┘
           │ HTTP + Firestore
┌──────────▼──────────────────────┐
│  Backend (Python Flask)          │  Port: 5000
│  - Gemini AI scam analysis       │
│  - WavLM deepfake detection      │
│  - Threat engine v2              │
│  - Audio relay (WebSocket)       │  Port: 8765
└──────────▲──────────────────────┘
           │ HTTP + WebSocket + Firestore
┌──────────┴──────────────────────┐
│  Web App (React/Vite)            │  Port: 3000
│  - Uncle Ah Hock scammer panel   │
│  - Initiates demo calls          │
│  - Real-time audio streaming     │
│  - PDRM report generation        │
└─────────────────────────────────┘
           │
┌──────────▼──────────────────────┐
│  Firebase (Cloud)                │  Free tier
│  - Firestore: call state sync    │
│  - Auth: anonymous user IDs      │
│  - FCM: push notifications       │
└─────────────────────────────────┘
```

## Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_API_KEYS` | No | Comma-separated keys for rotation |
| `FIREBASE_PROJECT_ID` | Yes | Firebase project ID |
| `FIREBASE_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `PORT` | No | HTTP port (default: 5000) |
| `CALL_AUDIO_WS_PORT` | No | WebSocket port (default: 8765) |
| `AUTO_HANGUP_ENABLED` | No | Auto-hangup on scam detection (default: true) |
| `CALL_AUDIO_RELAY_ENABLED` | No | Enable audio relay bridge (default: true) |

### Web App (`uncle-ah-hock---johor-kopi-chat/.env.local`)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_KEY` | Yes | Gemini API key for client-side |
| `VITE_BACKEND_URL` | No | Backend URL (default: http://localhost:5000/api) |
| `VITE_FIREBASE_API_KEY` | Yes | Firebase web API key |
| `VITE_FIREBASE_PROJECT_ID` | Yes | Firebase project ID |

### Mobile App
| Variable | Setting | Description |
|----------|---------|-------------|
| `VERICALL_API_BASE_URL` | `--dart-define` | Backend URL override |

---

## Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create project named `vericall-malaysia`
3. Enable **Firestore Database** (test mode for hackathon)
4. Enable **Authentication** > Anonymous sign-in
5. Download service account key:
   - Project Settings > Service Accounts > Generate New Private Key
   - Save as `backend/firebase-credentials.json`
6. Copy web config to `uncle-ah-hock---johor-kopi-chat/.env.local`

---

## Demo Flow

1. Start backend + web app
2. Open web app at `http://localhost:3000` (this is the "scammer" panel)
3. Open mobile app on phone/emulator (this is the "victim" phone)
4. On web app: Click "Start Demo Call"
5. On mobile: Incoming call appears -> Answer
6. On web app: Type as the scammer / use AI-generated scam scripts
7. Watch real-time: transcript, scam probability meter, Uncle Ah Hock responses
8. When scam threshold is reached: auto-hangup triggers
9. On mobile: Post-call report appears with PDRM report + share option

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `torch` install fails | Install PyTorch separately: `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| Mobile can't reach backend | Ensure phone and computer are on same WiFi. Use `--dart-define=VERICALL_API_BASE_URL=http://YOUR_IP:5000/api` |
| Firebase errors | Check `firebase-credentials.json` exists in `backend/` folder |
| Port already in use | Change `PORT` in `backend/.env` or kill existing process |
| Audio relay not connecting | Check `CALL_AUDIO_RELAY_ENABLED=true` in backend `.env` |
