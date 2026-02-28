"""
Demo call orchestration (single victim phone).
"""
import random
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import config
from app.services.firebase_service import firebase_service


class CallOrchestrator:
    def __init__(self) -> None:
        self.current_session_id: Optional[str] = None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _demo_number() -> str:
        pool = [
            "+60 11-1234 5678",
            "+60 3-7722 9000",
            "+60 18-654 3210",
            "Private Number",
        ]
        return random.choice(pool)

    @staticmethod
    def _event(
        event_type: str,
        actor: str,
        risk_score: float = 0.0,
        call_action: str = "none",
        reason_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "actor": actor,
            "risk_score": float(risk_score),
            "call_action": call_action,
            "reason_codes": list(reason_codes or []),
        }

    @staticmethod
    def _default_threat_summary() -> Dict[str, Any]:
        return {
            "risk_level": "low",
            "risk_score": 0.0,
            "confidence": 0.0,
            "mode": "normal",
            "retrieval_status": "unknown",
            "reason_codes": [],
            "call_action": "none",
            "call_action_reason_codes": [],
        }

    @staticmethod
    def _normalize_device(device: Optional[str], default: str = "system") -> str:
        value = (device or "").strip().lower()
        if value in ("web", "mobile", "system", "threat_engine"):
            return value
        return default

    @staticmethod
    def _is_privileged_actor(actor: str) -> bool:
        normalized = (actor or "").strip().lower()
        return normalized in ("system", "threat_engine")

    def _load_session_from_storage(self, session_id: str) -> Optional[Dict[str, Any]]:
        remote = firebase_service.get_demo_call_state() if firebase_service.is_available else None
        if not isinstance(remote, dict):
            return None
        if str(remote.get("sessionId", "")).strip() != session_id:
            return None
        return remote

    def _get_session_locked(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session:
            return session
        loaded = self._load_session_from_storage(session_id)
        if loaded:
            self._sessions[session_id] = loaded
            return loaded
        return None

    def start_demo_call(
        self,
        session_id: str,
        caller_label: str,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        session_id = (session_id or "").strip() or f"demo_{int(datetime.now().timestamp() * 1000)}"
        caller_name = (caller_label or "").strip() or "Unknown Caller"
        caller_number = self._demo_number()
        victim_user_id = config.DEMO_VICTIM_USER_ID

        payload = {
            "state": "ringing",
            "sessionId": session_id,
            "callerId": session_id,
            "callerName": caller_name,
            "callerNumber": caller_number,
            "victimUserId": victim_user_id,
            "requiresAnswer": True,
            "ownerDevice": None,
            "ownerClientId": None,
            "answeredAtIso": None,
            "answeredByLabel": None,
            "aiHostDevice": "web",
            "aiHostClientId": None,
            "aiHostStatus": "waiting_for_answer",
            "startTimeIso": timestamp or self._now_iso(),
            "events": [self._event("ringing", "system")],
            "scamProbability": 0,
            "threatSummary": self._default_threat_summary(),
            "updatedAtIso": self._now_iso(),
        }
        with self._lock:
            self.current_session_id = session_id
            self._sessions[session_id] = payload

        if firebase_service.is_available:
            firebase_service.upsert_demo_call_state(payload)

        push_sent = False
        if firebase_service.is_available and config.FCM_INCOMING_CALL_ENABLED:
            push_sent = firebase_service.send_demo_incoming_call_push(
                victim_user_id=victim_user_id,
                session_id=session_id,
                caller_name=caller_name,
                caller_number=caller_number,
            )

        return {
            "session_id": session_id,
            "state": "ringing",
            "victim_user_id": victim_user_id,
            "requires_answer": True,
            "owner_device": None,
            "owner_client_id": None,
            "push_sent": bool(push_sent),
        }

    def answer_demo_call(
        self,
        session_id: str,
        device: str,
        client_id: str,
        answered_by_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        active_session_id = (session_id or "").strip()
        if not active_session_id:
            return {"accepted": False, "reason": "session_id_required"}

        normalized_device = self._normalize_device(device, default="web")
        normalized_client = (client_id or "").strip()
        if not normalized_client:
            return {"accepted": False, "reason": "client_id_required"}

        with self._lock:
            session = self._get_session_locked(active_session_id)
            if not session:
                return {"accepted": False, "reason": "session_not_found"}

            state = str(session.get("state", "idle")).strip().lower()
            owner_device = session.get("ownerDevice")
            owner_client_id = session.get("ownerClientId")
            if state == "connected":
                if owner_device == normalized_device and owner_client_id == normalized_client:
                    return {
                        "accepted": True,
                        "session_id": active_session_id,
                        "state": "connected",
                        "owner_device": owner_device,
                        "owner_client_id": owner_client_id,
                    }
                return {
                    "accepted": False,
                    "session_id": active_session_id,
                    "state": "connected",
                    "owner_device": owner_device,
                    "owner_client_id": owner_client_id,
                    "reason": "already_answered",
                }

            if state != "ringing":
                return {
                    "accepted": False,
                    "session_id": active_session_id,
                    "state": state,
                    "reason": "call_not_ringing",
                }

            answered_label = (answered_by_label or "").strip() or f"{normalized_device}_user"
            event = self._event(
                "connected",
                normalized_device,
                call_action="connected",
                reason_codes=[f"answered_by_{normalized_device}"],
            )
            payload = {
                "state": "connected",
                "sessionId": active_session_id,
                "ownerDevice": normalized_device,
                "ownerClientId": normalized_client,
                "answeredAtIso": self._now_iso(),
                "answeredByLabel": answered_label,
                "aiHostDevice": "web",
                "aiHostStatus": "pending_start",
                "events": [event],
                "updatedAtIso": self._now_iso(),
            }

            for key, value in payload.items():
                if key == "events":
                    continue
                session[key] = value
            session.setdefault("events", []).append(event)

        if firebase_service.is_available:
            firebase_service.upsert_demo_call_state(payload)

        return {
            "accepted": True,
            "session_id": active_session_id,
            "state": "connected",
            "owner_device": normalized_device,
            "owner_client_id": normalized_client,
        }

    def end_demo_call(
        self,
        session_id: Optional[str],
        ended_by: str,
        reason_codes: Optional[List[str]] = None,
        device: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        active_session_id = (session_id or "").strip()
        with self._lock:
            if not active_session_id:
                active_session_id = self.current_session_id
        if not active_session_id:
            return {"ok": True, "final_state": "idle", "session_id": None}

        normalized_actor = (ended_by or "system").strip() or "system"
        normalized_device = self._normalize_device(device, default=normalized_actor)
        normalized_client = (client_id or "").strip()
        with self._lock:
            session = self._get_session_locked(active_session_id) or {}
            current_state = str(session.get("state", "idle")).strip().lower()
            owner_device = str(session.get("ownerDevice", "") or "").strip().lower()
            owner_client_id = str(session.get("ownerClientId", "") or "").strip()

            if current_state == "connected" and not self._is_privileged_actor(normalized_actor):
                owner_match = owner_device == normalized_device and owner_client_id and owner_client_id == normalized_client
                if not owner_match:
                    return {
                        "ok": False,
                        "error": "not_owner",
                        "session_id": active_session_id,
                        "state": current_state,
                        "owner_device": owner_device or None,
                        "owner_client_id": owner_client_id or None,
                    }

        event = self._event("ended", ended_by or "system", call_action="ended", reason_codes=reason_codes)
        payload = {
            "state": "ended",
            "sessionId": active_session_id,
            "endedBy": ended_by or "system",
            "endedAtIso": self._now_iso(),
            "aiHostStatus": "ended",
            "events": [event],
            "updatedAtIso": self._now_iso(),
        }

        if firebase_service.is_available:
            firebase_service.upsert_demo_call_state(payload)

        with self._lock:
            if active_session_id == self.current_session_id:
                self.current_session_id = None

            if active_session_id in self._sessions:
                self._sessions[active_session_id]["state"] = "ended"
                self._sessions[active_session_id]["aiHostStatus"] = "ended"
                self._sessions[active_session_id].setdefault("events", []).append(event)

        return {
            "ok": True,
            "final_state": "ended",
            "session_id": active_session_id,
        }

    def record_call_action(
        self,
        session_id: str,
        call_action: str,
        risk_score: float,
        reason_codes: Optional[List[str]] = None,
    ) -> None:
        if not session_id:
            return

        normalized_action = (call_action or "none").strip().lower()
        if normalized_action not in ("warn", "challenge", "hangup"):
            return

        event = self._event(
            event_type=normalized_action,
            actor="threat_engine",
            risk_score=risk_score,
            call_action=normalized_action,
            reason_codes=reason_codes,
        )
        payload = {
            "sessionId": session_id,
            "events": [event],
            "updatedAtIso": self._now_iso(),
        }
        if firebase_service.is_available:
            firebase_service.upsert_demo_call_state(payload)

        if normalized_action == "hangup":
            self.end_demo_call(
                session_id=session_id,
                ended_by="threat_engine",
                reason_codes=reason_codes,
                device="threat_engine",
                client_id="threat_engine",
            )

    def record_threat_snapshot(self, session_id: str, assessment: Dict[str, Any]) -> None:
        if not session_id:
            return
        risk_score = float(assessment.get("risk_score", 0.0) or 0.0)
        threat_summary = {
            "risk_level": str(assessment.get("risk_level", "low")),
            "risk_score": risk_score,
            "confidence": float(assessment.get("confidence", 0.0) or 0.0),
            "mode": str(assessment.get("mode", "normal")),
            "retrieval_status": str(assessment.get("retrieval_status", "unknown")),
            "reason_codes": list(assessment.get("reason_codes") or [])[:8],
            "call_action": str(assessment.get("call_action", "none")),
            "call_action_reason_codes": list(assessment.get("call_action_reason_codes") or [])[:8],
        }
        payload: Dict[str, Any] = {
            "sessionId": session_id,
            "scamProbability": int(max(0, min(100, round(risk_score * 100)))),
            "threatSummary": threat_summary,
            "updatedAtIso": self._now_iso(),
        }

        with self._lock:
            session = self._get_session_locked(session_id)
            if session:
                if str(session.get("state", "")).strip().lower() == "connected":
                    payload["aiHostStatus"] = "connected"
                    payload["aiHostClientId"] = session.get("aiHostClientId") or "web_host"
                    session["aiHostStatus"] = "connected"
                    session["aiHostClientId"] = session.get("aiHostClientId") or "web_host"
                session["scamProbability"] = payload["scamProbability"]
                session["threatSummary"] = threat_summary
                session["updatedAtIso"] = payload["updatedAtIso"]

        if firebase_service.is_available:
            firebase_service.upsert_demo_call_state(payload)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._get_session_locked(session_id)
            if not session:
                return None
            return dict(session)


call_orchestrator = CallOrchestrator()
