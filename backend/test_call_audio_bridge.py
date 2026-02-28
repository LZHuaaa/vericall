"""
Unit tests for call audio bridge websocket compatibility behavior.
"""
from types import SimpleNamespace
import unittest

from app.services.call_audio_bridge import CallAudioBridge


class _FakeWebSocket:
    def __init__(self, request_path=None, legacy_path=None):
        if request_path is not None:
            self.request = SimpleNamespace(path=request_path)
        if legacy_path is not None:
            self.path = legacy_path
        self.closed = None
        self.sent_messages = []

    async def close(self, code=None, reason=None):
        self.closed = (code, reason)

    async def send(self, message):
        self.sent_messages.append(message)

    def __aiter__(self):
        return self

    async def __anext__(self):
        raise StopAsyncIteration


class CallAudioBridgeTests(unittest.IsolatedAsyncioTestCase):
    def test_extract_path_prefers_explicit(self):
        ws = _FakeWebSocket(request_path="/ws/call-audio/from-request")
        resolved = CallAudioBridge._extract_path(ws, "/ws/call-audio/from-explicit")
        self.assertEqual(resolved, "/ws/call-audio/from-explicit")

    def test_extract_path_from_request(self):
        ws = _FakeWebSocket(request_path="/ws/call-audio/from-request")
        resolved = CallAudioBridge._extract_path(ws)
        self.assertEqual(resolved, "/ws/call-audio/from-request")

    def test_extract_path_from_legacy_path(self):
        ws = _FakeWebSocket(legacy_path="/ws/call-audio/from-legacy")
        resolved = CallAudioBridge._extract_path(ws)
        self.assertEqual(resolved, "/ws/call-audio/from-legacy")

    async def test_handle_connection_rejects_invalid_path(self):
        bridge = CallAudioBridge()
        ws = _FakeWebSocket(request_path="/invalid/path")
        await bridge._handle_connection(ws)
        self.assertEqual(ws.closed, (1008, "invalid_path"))

    async def test_handle_connection_accepts_valid_path(self):
        bridge = CallAudioBridge()
        ws = _FakeWebSocket(request_path="/ws/call-audio/demo_session?role=victim")
        await bridge._handle_connection(ws)
        self.assertIsNone(ws.closed)
        self.assertNotIn("demo_session", bridge._sessions)


if __name__ == "__main__":
    unittest.main()
