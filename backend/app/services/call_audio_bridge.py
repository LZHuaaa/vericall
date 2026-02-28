"""
Lightweight WebSocket bridge for demo call audio relay.
"""
import asyncio
import json
import threading
from typing import Any, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

import websockets

from app.config import config


class CallAudioBridge:
    def __init__(self) -> None:
        self.host = config.CALL_AUDIO_WS_HOST
        self.port = int(config.CALL_AUDIO_WS_PORT)
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        self._started = threading.Event()
        self._sessions: Dict[str, Dict[str, Set]] = {}

    def start(self) -> None:
        if not config.CALL_AUDIO_RELAY_ENABLED:
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._started.clear()
        self._thread = threading.Thread(
            target=self._run_thread,
            name="call-audio-bridge",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(lambda: None)

    def _run_thread(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve_forever())

    async def _serve_forever(self) -> None:
        try:
            async with websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                max_size=2**22,
                ping_interval=20,
            ):
                self._started.set()
                print(f"Call audio bridge listening on ws://{self.host}:{self.port}/ws/call-audio/<session_id>")
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.25)
        except Exception as exc:
            print(f"Call audio bridge failed to start: {exc}")

    @staticmethod
    def _normalize_role(raw: str) -> str:
        value = (raw or "").strip().lower()
        if value in {"caller", "victim"}:
            return value
        return "caller"

    @staticmethod
    def _extract_path(websocket: Any, explicit_path: Optional[str] = None) -> str:
        """Resolve request path across websockets versions."""
        if explicit_path:
            return str(explicit_path)

        request = getattr(websocket, "request", None)
        request_path = getattr(request, "path", None)
        if request_path:
            return str(request_path)

        legacy_path = getattr(websocket, "path", None)
        if legacy_path:
            return str(legacy_path)

        request_path = getattr(websocket, "request_path", None)
        if request_path:
            return str(request_path)

        return ""

    async def _handle_connection(self, websocket, path: Optional[str] = None) -> None:
        resolved_path = self._extract_path(websocket, path)
        if not resolved_path:
            print("Call audio bridge: missing request path; closing websocket.")
            await websocket.close(code=1008, reason="invalid_path")
            return

        try:
            parsed = urlparse(resolved_path)
        except Exception as exc:
            print(f"Call audio bridge: failed to parse path '{resolved_path}': {exc}")
            await websocket.close(code=1008, reason="invalid_path")
            return

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 3 or parts[0] != "ws" or parts[1] != "call-audio":
            print(f"Call audio bridge: invalid path '{resolved_path}'")
            await websocket.close(code=1008, reason="invalid_path")
            return

        session_id = parts[2]
        role = self._normalize_role(parse_qs(parsed.query).get("role", ["caller"])[0])

        bucket = self._sessions.setdefault(session_id, {"caller": set(), "victim": set()})
        bucket[role].add(websocket)

        try:
            async for raw in websocket:
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                message_type = str(payload.get("type", "")).strip().lower()
                if message_type == "audio_chunk":
                    await self._relay_audio_chunk(session_id, role, payload)
                elif message_type == "control":
                    await self._relay_control(session_id, role, payload)
        finally:
            peers = self._sessions.get(session_id)
            if peers and websocket in peers.get(role, set()):
                peers[role].remove(websocket)
            if peers and not peers["caller"] and not peers["victim"]:
                self._sessions.pop(session_id, None)

    async def _relay_audio_chunk(self, session_id: str, sender_role: str, payload: Dict) -> None:
        peers = self._sessions.get(session_id, {})
        # One-way audio in this phase: caller -> victim.
        if sender_role != "caller":
            return
        targets = list(peers.get("victim", set()))
        if not targets:
            return
        data = json.dumps(
            {
                "type": "audio_chunk",
                "session_id": session_id,
                "seq": int(payload.get("seq", 0) or 0),
                "ts": payload.get("ts"),
                "sample_rate": int(payload.get("sample_rate", 16000) or 16000),
                "pcm16_b64": payload.get("pcm16_b64"),
            }
        )
        await self._broadcast(targets, data)

    async def _relay_control(self, session_id: str, sender_role: str, payload: Dict) -> None:
        peers = self._sessions.get(session_id, {})
        targets = set(peers.get("caller", set())) | set(peers.get("victim", set()))
        if not targets:
            return
        data = json.dumps(
            {
                "type": "control",
                "session_id": session_id,
                "state": str(payload.get("state", "")).strip().lower(),
                "actor": sender_role,
                "reason_codes": payload.get("reason_codes") or [],
                "ts": payload.get("ts"),
            }
        )
        await self._broadcast(list(targets), data)

    async def _broadcast(self, sockets: list, message: str) -> None:
        stale = []
        for ws in sockets:
            try:
                await ws.send(message)
            except Exception:
                stale.append(ws)
        if not stale:
            return
        for session_id, peers in list(self._sessions.items()):
            for role in ("caller", "victim"):
                peers[role].difference_update(stale)
            if not peers["caller"] and not peers["victim"]:
                self._sessions.pop(session_id, None)


call_audio_bridge = CallAudioBridge()
