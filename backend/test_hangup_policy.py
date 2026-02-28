"""
Unit tests for auto hang-up policy engine.
"""
import unittest

from app.services.hangup_policy import HangupPolicyEngine, HangupState


class HangupPolicyTests(unittest.TestCase):
    def setUp(self):
        self.engine = HangupPolicyEngine()

    def test_rule_a_first_challenge_after_three_seconds(self):
        state = HangupState()
        decision = self.engine.evaluate(
            state=state,
            silence_metrics={
                "speech_ratio": 0.01,
                "silent_for_seconds": 3.2,
                "challenge_prompts_sent": 0,
                "no_recent_human_speech_seconds": 3.2,
                "call_elapsed_seconds": 3.2,
            },
            deepfake_score=0.2,
            deepfake_confidence=0.4,
            risk_score=0.3,
        )
        self.assertEqual(decision.action, "challenge")
        self.assertIn("challenge_rule_a_initial_3s_silence", decision.reason_codes)

    def test_rule_a_silence_hangup(self):
        state = HangupState(challenge_count=1, warn_issued=True)
        decision = self.engine.evaluate(
            state=state,
            silence_metrics={
                "speech_ratio": 0.01,
                "silent_for_seconds": 8.2,
                "challenge_prompts_sent": 1,
                "no_recent_human_speech_seconds": 8.2,
                "call_elapsed_seconds": 8.2,
            },
            deepfake_score=0.2,
            deepfake_confidence=0.4,
            risk_score=0.3,
        )
        self.assertEqual(decision.action, "hangup")
        self.assertIn("auto_hangup_rule_a_silence_fast", decision.reason_codes)

    def test_rule_b_requires_consecutive_windows(self):
        state = HangupState()
        for _ in range(2):
            decision = self.engine.evaluate(
                state=state,
                silence_metrics={"speech_ratio": 0.04, "silent_for_seconds": 5},
                deepfake_score=0.9,
                deepfake_confidence=0.8,
                risk_score=0.7,
            )
            self.assertNotEqual(decision.action, "hangup")

        decision = self.engine.evaluate(
            state=state,
            silence_metrics={"speech_ratio": 0.04, "silent_for_seconds": 6},
            deepfake_score=0.9,
            deepfake_confidence=0.8,
            risk_score=0.7,
        )
        self.assertEqual(decision.action, "hangup")
        self.assertIn("auto_hangup_rule_b_deepfake_and_risk", decision.reason_codes)

    def test_rule_d_high_deepfake_speaking_hangup(self):
        state = HangupState()
        decision = self.engine.evaluate(
            state=state,
            silence_metrics={
                "speech_ratio": 0.18,
                "silent_for_seconds": 0.6,
                "challenge_prompts_sent": 0,
                "no_recent_human_speech_seconds": 0.6,
                "call_elapsed_seconds": 6.0,
            },
            deepfake_score=0.94,
            deepfake_confidence=0.81,
            risk_score=0.2,
        )
        self.assertEqual(decision.action, "hangup")
        self.assertIn("auto_hangup_rule_d_spoken_high_deepfake", decision.reason_codes)

    def test_guardrail_resets_on_human_speech(self):
        state = HangupState(
            state="challenge",
            warn_issued=True,
            challenge_count=2,
            consecutive_high_deepfake_windows=2,
            hard_bot_started_at=1234,
        )
        decision = self.engine.evaluate(
            state=state,
            silence_metrics={
                "speech_ratio": 0.22,
                "silent_for_seconds": 0.2,
                "challenge_prompts_sent": 2,
                "no_recent_human_speech_seconds": 0.2,
            },
            deepfake_score=0.4,
            deepfake_confidence=0.4,
            risk_score=0.2,
        )
        self.assertEqual(decision.action, "none")
        self.assertIn("human_speech_resumed", decision.reason_codes)
        self.assertEqual(state.challenge_count, 0)
        self.assertFalse(state.warn_issued)


if __name__ == "__main__":
    unittest.main()
