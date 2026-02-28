"""
Threat engine v2 orchestrator.
"""
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import config
from app.models.threat_schema import (
    EvidenceItem,
    ThreatAssessment,
    ThreatLiveEvent,
    ThreatSessionState,
    ThreatSignal,
)
from app.services.firebase_service import firebase_service
from app.services.hangup_policy import HangupState, hangup_policy_engine
from app.services.redaction import redaction_service
from app.services.retrieval_engine import RetrievalEngine, retrieval_engine
from app.services.scam_analyzer import ScamAnalyzer, scam_analyzer


class ThreatOrchestrator:
    def __init__(
        self,
        analyzer: Optional[ScamAnalyzer] = None,
        retrieval: Optional[RetrievalEngine] = None,
    ):
        self.analyzer = analyzer or scam_analyzer
        self.retrieval = retrieval or retrieval_engine
        self.redactor = redaction_service
        self.sessions: Dict[str, ThreatSessionState] = {}
        self.version = config.THREAT_ENGINE_VERSION
        self.llm_min_interval_seconds = float(config.THREAT_LLM_MIN_INTERVAL_SECONDS)
        self.retrieval_min_interval_seconds = float(config.THREAT_RETRIEVAL_MIN_INTERVAL_SECONDS)
        self._llm_cache: Dict[str, Dict[str, Any]] = {}
        self._retrieval_cache: Dict[str, Dict[str, Any]] = {}
        self.hangup_policy = hangup_policy_engine

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_or_create_session(self, session_id: str) -> ThreatSessionState:
        session = self.sessions.get(session_id)
        if session:
            return session
        session = ThreatSessionState(session_id=session_id)
        self.sessions[session_id] = session
        return session

    @staticmethod
    def _merge_transcript(current: str, delta: str) -> str:
        if not delta:
            return current
        if not current:
            return delta
        if current.endswith((" ", "\n")):
            return current + delta
        return f"{current} {delta}"

    def _build_deepfake_signal(
        self, deepfake_snapshot: Optional[Dict[str, Any]]
    ) -> Tuple[ThreatSignal, List[EvidenceItem], List[str]]:
        if not deepfake_snapshot:
            return (
                ThreatSignal(
                    name="deepfake",
                    score=0.0,
                    confidence=0.0,
                    active=False,
                    details="no_snapshot",
                ),
                [],
                [],
            )

        score = float(deepfake_snapshot.get("score", 0.0))
        confidence = float(deepfake_snapshot.get("confidence", 0.0))
        active = score >= 0.7 and confidence >= 0.6
        reason_codes: List[str] = []
        evidence: List[EvidenceItem] = []
        if active:
            reason_codes.append("deepfake_signal_active")
            evidence.append(
                EvidenceItem(
                    source="wavlm",
                    source_tier=1,
                    title="Deepfake voice signal",
                    summary=(
                        f"Deepfake score={score:.2f}, confidence={confidence:.2f}, "
                        f"artifacts={deepfake_snapshot.get('artifacts', [])}"
                    ),
                    supports_risk=True,
                    timestamp=self._now_iso(),
                )
            )
        return (
            ThreatSignal(
                name="deepfake",
                score=score,
                confidence=confidence,
                active=active,
                details=deepfake_snapshot.get("decision_reason") or "",
            ),
            evidence,
            reason_codes,
        )

    def _build_llm_signal(
        self,
        transcript: str,
        deepfake_score: float,
    ) -> Tuple[ThreatSignal, List[EvidenceItem], List[str], Optional[str]]:
        transcript = transcript.strip()
        if not transcript:
            return (
                ThreatSignal(
                    name="llm_scam",
                    score=0.0,
                    confidence=0.0,
                    active=False,
                    details="empty_transcript",
                ),
                [],
                [],
                None,
            )

        snippet = transcript[-1200:]
        analysis = self.analyzer.analyze_content_sync(snippet, deepfake_score, [])
        urgency_value = getattr(analysis.urgency_level, "value", "low")
        urgency_floor = {
            "critical": 0.95,
            "high": 0.82,
            "medium": 0.65,
            "low": 0.45,
        }.get(urgency_value, 0.45)

        if analysis.is_scam:
            llm_score = max(float(analysis.confidence), urgency_floor)
        else:
            llm_score = max(0.05, min(0.35, float(analysis.confidence) * 0.4))
        llm_active = bool(analysis.is_scam and llm_score >= 0.55)
        reason_codes: List[str] = []
        evidence: List[EvidenceItem] = []

        if llm_active:
            reason_codes.append(f"llm_scam_type_{analysis.scam_type.value}")
            reason_codes.append(f"llm_urgency_{urgency_value}")
            if analysis.red_flags:
                reason_codes.extend(
                    [f"llm_red_flag_{flag.lower().replace(' ', '_')}" for flag in analysis.red_flags[:3]]
                )
            evidence.append(
                EvidenceItem(
                    source="llm_reasoning",
                    source_tier=2,
                    title=f"LLM scam intent: {analysis.scam_type.value}",
                    summary=(
                        f"confidence={analysis.confidence:.2f}, urgency={analysis.urgency_level.value}, "
                        f"red_flags={analysis.red_flags[:3]}"
                    ),
                    supports_risk=True,
                    timestamp=self._now_iso(),
                )
            )
        return (
            ThreatSignal(
                name="llm_scam",
                score=llm_score,
                confidence=float(analysis.confidence),
                active=llm_active,
                details=analysis.scam_type.value,
            ),
            evidence,
            reason_codes,
            analysis.recommendation.value,
        )

    def _get_llm_signal_cached(
        self,
        session_id: str,
        transcript: str,
        deepfake_score: float,
    ) -> Tuple[ThreatSignal, List[EvidenceItem], List[str], Optional[str]]:
        now = datetime.now(timezone.utc)
        transcript_len = len(transcript)
        cache = self._llm_cache.get(session_id)
        if cache:
            elapsed = (now - cache["at"]).total_seconds()
            grew = transcript_len - int(cache.get("transcript_len", 0))
            if elapsed < self.llm_min_interval_seconds and grew < 80:
                return (
                    cache["signal"],
                    list(cache["evidence"]),
                    list(cache["reasons"]),
                    cache["action"],
                )

        signal, evidence, reasons, action = self._build_llm_signal(transcript, deepfake_score)
        self._llm_cache[session_id] = {
            "at": now,
            "transcript_len": transcript_len,
            "signal": signal,
            "evidence": list(evidence),
            "reasons": list(reasons),
            "action": action,
        }
        return signal, evidence, reasons, action

    def _get_retrieval_cached(
        self,
        session_id: str,
        transcript: str,
        claimed_organization: Optional[str],
        caller_number: Optional[str],
    ):
        now = datetime.now(timezone.utc)
        transcript_len = len(transcript)
        cache = self._retrieval_cache.get(session_id)
        cache_key = f"{(claimed_organization or '').lower()}|{caller_number or ''}"
        if cache and cache.get("key") == cache_key:
            elapsed = (now - cache["at"]).total_seconds()
            grew = transcript_len - int(cache.get("transcript_len", 0))
            if elapsed < self.retrieval_min_interval_seconds and grew < 160:
                return cache["result"]

        result = self.retrieval.verify(
            transcript=transcript[-1200:],
            claimed_organization=claimed_organization,
            caller_number=caller_number,
        )
        self._retrieval_cache[session_id] = {
            "at": now,
            "transcript_len": transcript_len,
            "key": cache_key,
            "result": result,
        }
        return result

    @staticmethod
    def _recommended_actions(risk_level: str, llm_action: Optional[str]) -> List[str]:
        if risk_level == "critical":
            return [
                "hang_up_immediately",
                "block_caller",
                "report_to_nsrc_997",
                "notify_family_guardian",
            ]
        if risk_level == "high":
            return [
                "hang_up_now",
                "call_official_hotline",
                "report_to_nsrc_997",
            ]
        if risk_level == "medium":
            return [
                "stop_sharing_sensitive_data",
                "verify_identity_with_official_channel",
            ]
        if risk_level == "low":
            return ["verify_identity_with_official_channel"]
        actions = ["continue_call_cautiously"]
        if llm_action:
            actions.append(llm_action)
        return actions

    @staticmethod
    def _level_from_score(score: float) -> str:
        if score < 0.2:
            return "safe"
        if score < 0.4:
            return "low"
        if score < 0.65:
            return "medium"
        if score < 0.82:
            return "high"
        return "critical"

    def _fuse_assessment(
        self,
        deepfake_signal: ThreatSignal,
        llm_signal: ThreatSignal,
        retrieval_status: str,
        retrieval_corroborated: bool,
        retrieval_confidence: float,
        reason_codes: List[str],
        evidence_items: List[EvidenceItem],
        llm_action: Optional[str],
    ) -> ThreatAssessment:
        risk_score = min(
            1.0,
            max(
                0.0,
                (deepfake_signal.score * deepfake_signal.confidence * 0.42)
                + (llm_signal.score * 0.43)
                + (retrieval_confidence * 0.15),
            ),
        )
        if retrieval_corroborated:
            risk_score = max(risk_score, 0.72)

        risk_level = self._level_from_score(risk_score)
        signal_count_for_high = 0
        if deepfake_signal.active and deepfake_signal.score >= 0.75:
            signal_count_for_high += 1
        if llm_signal.active and llm_signal.score >= 0.7:
            signal_count_for_high += 1
        if retrieval_corroborated:
            signal_count_for_high += 1

        # Gating rule: high/critical require at least two independent signals.
        if risk_level in ("high", "critical") and signal_count_for_high < 2:
            risk_level = "medium"

        # Gating rule: critical requires corroboration or strong multisignal consensus.
        strong_multisignal = (
            deepfake_signal.active
            and llm_signal.active
            and deepfake_signal.score >= 0.9
            and llm_signal.score >= 0.85
            and min(deepfake_signal.confidence, llm_signal.confidence) >= 0.75
        )
        if risk_level == "critical" and not (retrieval_corroborated or strong_multisignal):
            risk_level = "high" if signal_count_for_high >= 2 else "medium"

        if risk_level == "safe" and (deepfake_signal.active or llm_signal.active):
            risk_level = "low"

        confidence = min(
            0.99,
            max(
                0.05,
                (
                    deepfake_signal.confidence * 0.35
                    + llm_signal.confidence * 0.45
                    + retrieval_confidence * 0.20
                ),
            ),
        )

        mode = "normal"
        if retrieval_status in ("timeout", "error"):
            mode = "degraded_local"
            reason_codes.append("degraded_mode_retrieval_failure")

        return ThreatAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            reason_codes=list(dict.fromkeys(reason_codes))[:20],
            recommended_actions=self._recommended_actions(risk_level, llm_action),
            evidence_items=evidence_items[:20],
            retrieval_status=retrieval_status,
            signals=[deepfake_signal, llm_signal, ThreatSignal(
                name="retrieval",
                score=float(retrieval_confidence),
                confidence=float(retrieval_confidence),
                active=bool(retrieval_corroborated),
                details=retrieval_status,
            )],
            mode=mode,
            version=self.version,
        )

    @staticmethod
    def _restore_hangup_state(raw_state: Optional[Dict[str, Any]]) -> HangupState:
        state = raw_state or {}
        return HangupState(
            state=str(state.get("state", "none")),
            warn_issued=bool(state.get("warn_issued", False)),
            challenge_count=int(state.get("challenge_count", 0) or 0),
            consecutive_high_deepfake_windows=int(
                state.get("consecutive_high_deepfake_windows", 0) or 0
            ),
            hard_bot_started_at=(
                float(state["hard_bot_started_at"])
                if state.get("hard_bot_started_at") is not None
                else None
            ),
            updated_at=float(state.get("updated_at", datetime.now(timezone.utc).timestamp())),
        )

    @staticmethod
    def _store_hangup_state(state: HangupState) -> Dict[str, Any]:
        return {
            "state": state.state,
            "warn_issued": state.warn_issued,
            "challenge_count": state.challenge_count,
            "consecutive_high_deepfake_windows": state.consecutive_high_deepfake_windows,
            "hard_bot_started_at": state.hard_bot_started_at,
            "updated_at": state.updated_at,
        }

    def _persist_session_state(
        self,
        session: ThreatSessionState,
        assessment: ThreatAssessment,
        event: ThreatLiveEvent,
    ) -> None:
        if not firebase_service.is_available:
            return
        try:
            firebase_service.save_threat_session(
                session.session_id,
                {
                    "updated_at": self._now_iso(),
                    "latest_risk_level": assessment.risk_level,
                    "latest_risk_score": assessment.risk_score,
                    "retrieval_status": assessment.retrieval_status,
                    "mode": assessment.mode,
                    "call_action": assessment.call_action,
                    "call_action_reason_codes": assessment.call_action_reason_codes[:6],
                    "finalized": session.finalized,
                    "claimed_organization": event.claimed_organization,
                    "caller_number": self.redactor.redact_phone(event.caller_number),
                    "transcript_summary": self.redactor.redact_text(session.transcript[-600:]),
                    "reason_codes": assessment.reason_codes[:10],
                    "version": assessment.version,
                },
            )
            firebase_service.save_threat_assessment(
                session.session_id,
                assessment.to_dict(),
            )
            terms = self.redactor.extract_terms(event.transcript_delta)
            if terms:
                pattern_seed = "|".join(sorted(set(assessment.reason_codes[:6] + terms[:6])))
                pattern_id = hashlib.sha256(pattern_seed.encode("utf-8")).hexdigest()[:24]
                firebase_service.upsert_threat_pattern(
                    pattern_id,
                    {
                        "reason_codes": assessment.reason_codes[:10],
                        "observed_terms": terms[:20],
                        "risk_level": assessment.risk_level,
                        "source_quality": min(
                            [item.source_tier for item in assessment.evidence_items] or [3]
                        ),
                        "last_seen": self._now_iso(),
                    },
                )
        except Exception as exc:
            print(f"Threat persistence failed for {session.session_id}: {exc}")

    def assess_live(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        event = ThreatLiveEvent.from_dict(payload)
        if not event.session_id:
            raise ValueError("session_id is required")
        if event.timestamp == "":
            raise ValueError("timestamp is required")

        safe_payload = self.redactor.sanitize_event_payload(payload)
        event.transcript_delta = safe_payload.get("transcript_delta", event.transcript_delta)
        event.caller_number = safe_payload.get("caller_number", event.caller_number)

        session = self._get_or_create_session(event.session_id)
        session.transcript = self._merge_transcript(session.transcript, event.transcript_delta)

        deepfake_signal, deepfake_evidence, reason_codes = self._build_deepfake_signal(
            event.deepfake_snapshot
        )
        llm_signal, llm_evidence, llm_reasons, llm_action = self._get_llm_signal_cached(
            session_id=event.session_id,
            transcript=session.transcript,
            deepfake_score=deepfake_signal.score,
        )
        reason_codes.extend(llm_reasons)

        retrieval = self._get_retrieval_cached(
            session_id=event.session_id,
            transcript=session.transcript,
            claimed_organization=event.claimed_organization,
            caller_number=event.caller_number,
        )
        reason_codes.extend(retrieval.reason_codes)
        evidence_items = deepfake_evidence + llm_evidence + retrieval.evidence

        assessment = self._fuse_assessment(
            deepfake_signal=deepfake_signal,
            llm_signal=llm_signal,
            retrieval_status=retrieval.status,
            retrieval_corroborated=retrieval.corroborated,
            retrieval_confidence=retrieval.confidence,
            reason_codes=reason_codes,
            evidence_items=evidence_items,
            llm_action=llm_action,
        )

        hangup_state = self._restore_hangup_state(session.call_policy_state)
        hangup_decision = self.hangup_policy.evaluate(
            state=hangup_state,
            silence_metrics=event.silence_metrics,
            deepfake_score=deepfake_signal.score,
            deepfake_confidence=deepfake_signal.confidence,
            risk_score=assessment.risk_score,
        )
        session.call_policy_state = self._store_hangup_state(hangup_state)
        if hangup_decision.reason_codes:
            reason_codes.extend(hangup_decision.reason_codes)
            assessment.reason_codes = list(dict.fromkeys(assessment.reason_codes + hangup_decision.reason_codes))[:20]

        if config.AUTO_HANGUP_ENABLED:
            assessment.call_action = hangup_decision.action
            assessment.call_action_confidence = hangup_decision.confidence
            assessment.call_action_reason_codes = list(hangup_decision.reason_codes)
            assessment.hangup_after_ms = hangup_decision.hangup_after_ms
        else:
            assessment.call_action = "none"
            assessment.call_action_confidence = hangup_decision.confidence
            assessment.call_action_reason_codes = list(hangup_decision.reason_codes)
            assessment.hangup_after_ms = None
            if hangup_decision.action != "none":
                assessment.reason_codes = list(
                    dict.fromkeys(assessment.reason_codes + ["auto_hangup_shadow_only"])
                )[:20]

        session.latest_assessment = assessment
        session.updated_at = self._now_iso()
        for item in assessment.evidence_items:
            session.evidence_timeline.append(item.to_dict())

        self._persist_session_state(session, assessment, event)
        return assessment.to_dict()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if session:
            return session.to_dict()

        if not firebase_service.is_available:
            return None

        remote = firebase_service.get_threat_session(session_id)
        if not remote:
            return None
        timeline = firebase_service.get_threat_assessments(session_id, limit=200)
        return {
            "session_id": session_id,
            "latest_assessment": remote.get("latest_assessment"),
            "evidence_timeline": timeline,
            "created_at": remote.get("created_at"),
            "updated_at": remote.get("updated_at"),
            "finalized": bool(remote.get("finalized")),
        }

    def finalize_session(self, session_id: str) -> Dict[str, Any]:
        session = self._get_or_create_session(session_id)
        session.finalized = True
        session.updated_at = self._now_iso()
        latest = session.latest_assessment.to_dict() if session.latest_assessment else None

        if firebase_service.is_available:
            try:
                firebase_service.save_threat_session(
                    session_id,
                    {
                        "finalized": True,
                        "updated_at": session.updated_at,
                        "latest_assessment": latest,
                    },
                )
            except Exception as exc:
                print(f"Threat finalize persistence failed for {session_id}: {exc}")

        return {
            "session_id": session_id,
            "finalized": True,
            "latest_assessment": latest,
            "evidence_timeline_count": len(session.evidence_timeline),
            "version": self.version,
        }


threat_orchestrator = ThreatOrchestrator()
