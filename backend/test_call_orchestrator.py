"""
Unit tests for demo call ownership and sync behavior.
"""
import unittest

import app.services.call_orchestrator as call_orchestrator_module
from app.services.call_orchestrator import CallOrchestrator


class _FakeFirebaseService:
    is_available = False

    def upsert_demo_call_state(self, _data):
        return True

    def get_demo_call_state(self):
        return None

    def send_demo_incoming_call_push(self, **_kwargs):
        return False


class CallOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self._original_firebase = call_orchestrator_module.firebase_service
        call_orchestrator_module.firebase_service = _FakeFirebaseService()
        self.orchestrator = CallOrchestrator()

    def tearDown(self):
        call_orchestrator_module.firebase_service = self._original_firebase

    def test_first_answer_wins(self):
        self.orchestrator.start_demo_call("demo_1", "Caller")

        accepted = self.orchestrator.answer_demo_call(
            session_id="demo_1",
            device="web",
            client_id="web_1",
            answered_by_label="Web",
        )
        rejected = self.orchestrator.answer_demo_call(
            session_id="demo_1",
            device="mobile",
            client_id="mobile_1",
            answered_by_label="Mobile",
        )

        self.assertTrue(accepted["accepted"])
        self.assertFalse(rejected["accepted"])
        self.assertEqual(rejected["reason"], "already_answered")
        self.assertEqual(rejected["owner_device"], "web")
        self.assertEqual(rejected["owner_client_id"], "web_1")

    def test_connected_end_requires_owner(self):
        self.orchestrator.start_demo_call("demo_2", "Caller")
        self.orchestrator.answer_demo_call(
            session_id="demo_2",
            device="web",
            client_id="web_owner",
        )

        non_owner = self.orchestrator.end_demo_call(
            session_id="demo_2",
            ended_by="mobile_client",
            device="mobile",
            client_id="mobile_other",
            reason_codes=["manual_end_attempt"],
        )
        owner = self.orchestrator.end_demo_call(
            session_id="demo_2",
            ended_by="web_client",
            device="web",
            client_id="web_owner",
            reason_codes=["owner_hangup"],
        )

        self.assertFalse(non_owner["ok"])
        self.assertEqual(non_owner["error"], "not_owner")
        self.assertTrue(owner["ok"])
        self.assertEqual(owner["final_state"], "ended")

    def test_ringing_end_allowed_for_any_device(self):
        self.orchestrator.start_demo_call("demo_3", "Caller")
        ended = self.orchestrator.end_demo_call(
            session_id="demo_3",
            ended_by="mobile_client",
            device="mobile",
            client_id="mobile_1",
            reason_codes=["declined"],
        )
        self.assertTrue(ended["ok"])
        self.assertEqual(ended["final_state"], "ended")

    def test_record_threat_snapshot_updates_session_summary(self):
        self.orchestrator.start_demo_call("demo_4", "Caller")
        self.orchestrator.answer_demo_call(
            session_id="demo_4",
            device="web",
            client_id="web_2",
        )
        self.orchestrator.record_threat_snapshot(
            session_id="demo_4",
            assessment={
                "risk_level": "high",
                "risk_score": 0.62,
                "confidence": 0.77,
                "mode": "normal",
                "retrieval_status": "ok",
                "reason_codes": ["llm_scam_type_bank", "llm_red_flag_otp_request"],
                "call_action": "warn",
                "call_action_reason_codes": ["warning_sustained_silence"],
            },
        )

        session = self.orchestrator.get_session("demo_4")
        self.assertIsNotNone(session)
        self.assertEqual(session["scamProbability"], 62)
        self.assertEqual(session["aiHostStatus"], "connected")
        summary = session["threatSummary"]
        self.assertEqual(summary["risk_level"], "high")
        self.assertEqual(summary["call_action"], "warn")
        self.assertIn("llm_scam_type_bank", summary["reason_codes"])


if __name__ == "__main__":
    unittest.main()
