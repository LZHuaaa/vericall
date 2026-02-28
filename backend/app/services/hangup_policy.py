"""
Auto hang-up policy engine for live call protection.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


def _now_seconds() -> float:
    return datetime.now(timezone.utc).timestamp()


@dataclass
class HangupDecision:
    action: str
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    hangup_after_ms: Optional[int] = None


@dataclass
class HangupState:
    state: str = "none"
    warn_issued: bool = False
    challenge_count: int = 0
    consecutive_high_deepfake_windows: int = 0
    hard_bot_started_at: Optional[float] = None
    updated_at: float = field(default_factory=_now_seconds)


class HangupPolicyEngine:
    """
    Hybrid policy tuned for fast bot defense:
    - Rule A1: 3s silence => one challenge prompt.
    - Rule A2: 8s silence => hang up immediately (possible silent bot).
    - Rule B:  deepfake >= 0.85 for 3 windows + risk >= 0.60 => hang up.
    - Rule C:  deepfake >= 0.95 for 5s + no recent human speech >= 6s => hang up.
    - Rule D:  caller speaking + very high deepfake confidence => hang up directly.
    - Guardrail: human speech ratio > 0.15 resets pending escalation.
    """

    def evaluate(
        self,
        state: Optional[HangupState],
        silence_metrics: Optional[Dict],
        deepfake_score: float,
        deepfake_confidence: float,
        risk_score: float,
    ) -> HangupDecision:
        policy_state = state or HangupState()
        metrics = silence_metrics or {}

        speech_ratio = float(metrics.get("speech_ratio", 0.0) or 0.0)
        silent_for_seconds = float(metrics.get("silent_for_seconds", 0.0) or 0.0)
        no_recent_human_speech_seconds = float(
            metrics.get("no_recent_human_speech_seconds", 0.0) or 0.0
        )
        challenge_prompts_sent = int(metrics.get("challenge_prompts_sent", 0) or 0)
        call_elapsed_seconds = float(metrics.get("call_elapsed_seconds", 0.0) or 0.0)
        caller_is_speaking = speech_ratio >= 0.08 and no_recent_human_speech_seconds <= 2.0
        high_conf_spoken_deepfake = (
            caller_is_speaking and deepfake_score >= 0.92 and deepfake_confidence >= 0.75
        )

        # Guardrail: speech resumed with healthy activity.
        if speech_ratio > 0.15 and not high_conf_spoken_deepfake:
            policy_state.state = "none"
            policy_state.warn_issued = False
            policy_state.challenge_count = 0
            policy_state.consecutive_high_deepfake_windows = 0
            policy_state.hard_bot_started_at = None
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="none",
                confidence=0.2,
                reason_codes=["human_speech_resumed"],
            )

        # Track deepfake streak for Rule B.
        if deepfake_score >= 0.85 and deepfake_confidence >= 0.6:
            policy_state.consecutive_high_deepfake_windows += 1
        else:
            policy_state.consecutive_high_deepfake_windows = 0

        # Track hard bot window for Rule C.
        if deepfake_score >= 0.95:
            if policy_state.hard_bot_started_at is None:
                policy_state.hard_bot_started_at = _now_seconds()
        else:
            policy_state.hard_bot_started_at = None

        reasons: List[str] = []

        # Rule D: direct hangup for strongly synthetic speaking voice.
        # This is independent from scam intent because the voice authenticity signal is dominant.
        if high_conf_spoken_deepfake:
            policy_state.state = "hangup"
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="hangup",
                confidence=0.96,
                reason_codes=["auto_hangup_rule_d_spoken_high_deepfake"],
                hangup_after_ms=500,
            )

        # Rule A2: fast silent-bot hangup after challenge window.
        if (
            silent_for_seconds >= 8
            and speech_ratio < 0.05
            and call_elapsed_seconds >= 8
            and challenge_prompts_sent >= 1
        ):
            policy_state.state = "hangup"
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="hangup",
                confidence=0.94,
                reason_codes=["auto_hangup_rule_a_silence_fast"],
                hangup_after_ms=450,
            )

        # Rule A1: one challenge prompt at ~3s silence.
        if (
            silent_for_seconds >= 3
            and speech_ratio < 0.05
            and policy_state.challenge_count < 1
            and challenge_prompts_sent < 1
        ):
            policy_state.state = "challenge"
            policy_state.challenge_count = 1
            policy_state.warn_issued = True
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="challenge",
                confidence=0.82,
                reason_codes=["challenge_rule_a_initial_3s_silence"],
            )

        # Rule B.
        if (
            policy_state.consecutive_high_deepfake_windows >= 3
            and risk_score >= 0.60
        ):
            policy_state.state = "hangup"
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="hangup",
                confidence=0.9,
                reason_codes=["auto_hangup_rule_b_deepfake_and_risk"],
                hangup_after_ms=900,
            )

        # Rule C.
        if policy_state.hard_bot_started_at is not None:
            hard_bot_elapsed = _now_seconds() - policy_state.hard_bot_started_at
            if hard_bot_elapsed >= 5 and no_recent_human_speech_seconds >= 6:
                policy_state.state = "hangup"
                policy_state.updated_at = _now_seconds()
                return HangupDecision(
                    action="hangup",
                    confidence=0.95,
                    reason_codes=["auto_hangup_rule_c_hard_bot"],
                    hangup_after_ms=700,
                )

        suspicious_silence = silent_for_seconds >= 2 and speech_ratio < 0.06
        suspicious_bot = deepfake_score >= 0.8 and risk_score >= 0.5
        is_suspicious = suspicious_silence or suspicious_bot

        if suspicious_silence:
            reasons.append("warning_sustained_silence")
        if suspicious_bot:
            reasons.append("warning_deepfake_risk_cluster")

        if is_suspicious and not policy_state.warn_issued:
            policy_state.warn_issued = True
            policy_state.state = "warn"
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="warn",
                confidence=0.68,
                reason_codes=reasons or ["warning_general_suspicion"],
            )

        if is_suspicious and policy_state.warn_issued and policy_state.challenge_count < 2:
            policy_state.challenge_count += 1
            policy_state.state = "challenge"
            policy_state.updated_at = _now_seconds()
            return HangupDecision(
                action="challenge",
                confidence=0.74,
                reason_codes=(reasons or ["challenge_general_suspicion"])
                + [f"challenge_count_{policy_state.challenge_count}"],
            )

        policy_state.state = "none"
        policy_state.updated_at = _now_seconds()
        return HangupDecision(
            action="none",
            confidence=0.25,
            reason_codes=[],
        )


hangup_policy_engine = HangupPolicyEngine()
