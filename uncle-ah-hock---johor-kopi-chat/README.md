<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Uncle Ah Hock Web Panel

Web control panel for the VeriCall demo call flow.

## Run Locally

Prerequisites:
- Node.js 20+

Setup:
1. Install dependencies: `npm install`
2. Copy `.env.example` to `.env.local`
3. Set at least your API key in `.env.local`
4. Run: `npm run dev`

## Environment Variables

Required:
- `GEMINI_API_KEY`: Gemini key for live model access.

Recommended:
- `VITE_BACKEND_URL`: Backend API base (default is `http://localhost:5000/api`).

Optional (Firestore realtime sync primary path):
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`

Optional (call audio relay):
- `VITE_CALL_AUDIO_RELAY_ENABLED=true`
- `VITE_CALL_AUDIO_WS_PORT=8765`
- `VITE_CALL_AUDIO_WS_URL` (override full ws base URL if needed)

## Call State Sync Behavior

- Primary: Firestore `calls/current_demo` snapshot (`listenToDemoCallState`).
- Fallback: If Firebase config/auth/snapshot fails, web auto-polls backend every 1 second via:
  - `GET /api/call/demo/session/<session_id>`
- Result: web still transitions `idle -> ringing -> connected` without Firebase web config.

## Audio Relay Requirements

For scammer-to-victim relay audio:

- Backend `.env` must include:
  - `CALL_AUDIO_RELAY_ENABLED=true`
  - `CALL_AUDIO_WS_PORT=8765` (or your chosen port)
- Web should set:
  - `VITE_CALL_AUDIO_RELAY_ENABLED=true`

If relay is disabled, demo call state and AI flow still run, but relay stream won't be forwarded.
