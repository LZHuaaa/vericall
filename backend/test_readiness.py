"""
KitaHack 2026 readiness checks (functionality-first).

Run:
  python test_readiness.py

Optional:
  set VERICALL_API_BASE_URL=http://localhost:5000/api
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
import wave
from array import array
from typing import Dict, Tuple

import requests

BASE_URL = os.getenv("VERICALL_API_BASE_URL", "http://localhost:5000/api")


def _print(title: str) -> None:
    print(f"\n=== {title} ===")


def _expect(
    response: requests.Response,
    expected: Tuple[int, ...],
    name: str,
) -> Dict:
    if response.status_code not in expected:
        raise AssertionError(
            f"{name} expected {expected}, got {response.status_code}: {response.text}"
        )
    try:
        return response.json()
    except Exception as exc:
        raise AssertionError(f"{name} returned non-JSON body: {response.text}") from exc


def _make_test_wav(path: str, seconds: float = 1.0, sr: int = 16000) -> None:
    n = int(seconds * sr)
    samples = array("h", [0] * n)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())


def main() -> None:
    print(f"Using API: {BASE_URL}")

    _print("Health")
    status = requests.get(f"{BASE_URL}/status", timeout=20)
    status_data = _expect(status, (200,), "status")
    firebase_ready = status_data.get("firebase_available") is True
    print(f"firebase_available={firebase_ready}")

    _print("Analyze Complete (transcript-only)")
    complete_payload = {
        "transcript": "Hello this is LHDN, pay RM5000 now or arrest warrant issued.",
        "caller_number": "+60112233445",
        "claimed_identity": "LHDN officer",
        "claimed_organization": "LHDN",
        "call_duration": 35,
    }
    complete = requests.post(
        f"{BASE_URL}/analyze/complete",
        json=complete_payload,
        timeout=45,
    )
    complete_data = _expect(complete, (200,), "analyze_complete")
    assert "threat_level" in complete_data
    assert "layers" in complete_data
    print("analyze_complete ok")

    _print("Analyze Pipeline (audio multipart)")
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = os.path.join(tmp, "sample.wav")
        _make_test_wav(wav_path)
        with open(wav_path, "rb") as fh:
            pipeline = requests.post(
                f"{BASE_URL}/analyze/pipeline",
                files={"audio": ("sample.wav", fh, "audio/wav")},
                data={"transcript": "Test call transcript"},
                timeout=60,
            )
    pipeline_data = _expect(pipeline, (200,), "analyze_pipeline")
    assert "verdict" in pipeline_data
    print("analyze_pipeline ok")

    _print("Family Link + Alerts + Reports")
    victim_id = f"victim_{uuid.uuid4().hex[:8]}"
    guardian_id = f"guardian_{uuid.uuid4().hex[:8]}"

    # Ensure user profile endpoint responds
    upsert = requests.post(
        f"{BASE_URL}/users",
        json={"user_id": victim_id, "name": "Victim Test"},
        timeout=20,
    )
    _expect(upsert, (200,), "users_upsert")

    # Family link code
    code_resp = requests.post(
        f"{BASE_URL}/family/link/code",
        json={"victim_id": victim_id, "victim_name": "Victim Test"},
        timeout=20,
    )
    if firebase_ready:
        code_data = _expect(code_resp, (200,), "family_link_code")
        code = code_data["code"]
        consume_resp = requests.post(
            f"{BASE_URL}/family/link/consume",
            json={"code": code, "guardian_id": guardian_id, "guardian_name": "Guardian"},
            timeout=20,
        )
        _expect(consume_resp, (200,), "family_link_consume")
        fam_resp = requests.get(f"{BASE_URL}/family/{victim_id}", timeout=20)
        fam_data = _expect(fam_resp, (200,), "family_get")
        assert isinstance(fam_data.get("family_members", []), list)
        print("family link flow ok")
    else:
        code_data = _expect(code_resp, (503,), "family_link_code_firebase_off")
        assert "action" in code_data
        print("family link returns actionable 503 when firebase unavailable")

    # Reports + evidence
    report_resp = requests.post(
        f"{BASE_URL}/reports",
        json={
            "user_id": victim_id,
            "scam_type": "lhdn",
            "phone_number": "+60112233445",
            "transcript": "Pay now",
            "deepfake_score": 0.91,
        },
        timeout=20,
    )
    if firebase_ready:
        report_data = _expect(report_resp, (200,), "reports_post")
        report_id = report_data["report_id"]
        evidence_resp = requests.post(
            f"{BASE_URL}/evidence",
            json={
                "report_id": report_id,
                "transcript": "Pay now",
                "quality_score": 80,
                "keywords_detected": ["LHDN", "urgent"],
            },
            timeout=20,
        )
        _expect(evidence_resp, (200,), "evidence_post")
        print("reports/evidence flow ok")
    else:
        report_data = _expect(report_resp, (503,), "reports_post_firebase_off")
        assert "action" in report_data
        print("reports returns actionable 503 when firebase unavailable")

    # Alerts and stats
    alerts = requests.get(
        f"{BASE_URL}/alerts",
        params={"user_id": victim_id, "limit": 20},
        timeout=20,
    )
    _expect(alerts, (200, 503), "alerts_get")
    stats = requests.get(f"{BASE_URL}/reports/stats", timeout=20)
    _expect(stats, (200, 503), "reports_stats")
    print("alerts/stats endpoint contract ok")

    _print("All readiness checks passed")
    print(json.dumps({"base_url": BASE_URL, "firebase_available": firebase_ready}, indent=2))


if __name__ == "__main__":
    main()
