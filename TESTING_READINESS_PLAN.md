# KitaHack 2026 Readiness Testing Plan

## Goal
Validate that VeriCall delivers:
- Multi-layer scam/deepfake detection
- Active defense (Uncle Ah Hock)
- Family protection + alerts
- Malaysia-specific scam intelligence
- End-to-end mobile usability

## Quick Execution
1. Start backend:
```bash
cd backend
python -m app.main
```
2. Run automated API readiness checks:
```bash
cd backend
python test_readiness.py
```
3. Run extended API suite (optional):
```bash
cd backend
python test_api.py
```

## Automated Coverage (`backend/test_readiness.py`)
- `GET /api/status`
- `POST /api/analyze/complete` (transcript-only path)
- `POST /api/analyze/pipeline` (multipart audio path)
- `POST /api/users`
- `POST /api/family/link/code`
- `POST /api/family/link/consume`
- `GET /api/family/<user_id>`
- `POST /api/reports`
- `POST /api/evidence`
- `GET /api/alerts?user_id=&limit=`
- `GET /api/reports/stats`

It validates both:
- Happy path when Firebase is available
- Actionable `503` behavior when Firebase is unavailable

## Manual Mobile Scenarios

### 1) End-to-end call analysis
1. Open `Call` tab.
2. Record 10-20s audio.
3. Tap `Analyze Call`.
4. Verify threat/deepfake/scam fields are shown.

Expected:
- No placeholder error.
- Pipeline results render.

### 2) Transcript-only fallback
1. Skip recording.
2. Paste transcript.
3. Tap `Analyze Call`.

Expected:
- Analysis succeeds via complete endpoint.

### 3) Report + evidence submission
1. Complete analysis.
2. Tap `Submit Report + Evidence`.

Expected:
- Snackbar shows `report_id`.
- Report/evidence appear in backend data.

### 4) Family protection
1. Victim tab: generate code/QR.
2. Guardian tab: scan QR.
3. Repeat with manual code.
4. Try invalid/expired code.

Expected:
- Valid codes link successfully.
- Invalid cases show explicit error reason.

### 5) Alerts + dashboard
1. Trigger/send alert.
2. Open Alerts screen and refresh.
3. Open Home screen and refresh.

Expected:
- Alert feed updates from backend.
- Home metrics reflect backend values (reports/family/high-risk 24h).

### 6) Settings persistence
1. Toggle settings.
2. Restart app.
3. Open settings again.

Expected:
- Toggles persist.
- Profile edits persist locally and sync via backend when available.

## Regression Focus (must-pass before pilot)
- No hardcoded report user IDs in mobile submission flow.
- `/api/alerts` errors are surfaced, not silently returned as empty.
- Alert queries work with or without Firestore composite index (fallback path).
- QR generation failure still allows manual linking using visible code.
- Audio preview state resets when playback completes.
- API base URL is configurable via `--dart-define=VERICALL_API_BASE_URL=...`.

## KitaHack Alignment Checks
- Multi-layer detection demonstrated in API output and UI.
- Uncle Ah Hock active defense flow demonstrated.
- Family-link and alert propagation demonstrated.
- Malaysia-specific scam content patterns demonstrated.
- Demo works without manual code edits during rehearsal.
