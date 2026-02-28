"""
Gemini SDK compatibility adapter.

Prefers `google.genai` and falls back to deprecated `google.generativeai`
when the newer SDK is not installed.
"""
import importlib
import os
import re
import threading
import time
from typing import Any, Optional


try:
    from google import genai as new_genai  # type: ignore
except Exception:  # pragma: no cover
    new_genai = None

legacy_genai: Optional[Any] = None


def _load_legacy_sdk():
    global legacy_genai
    if legacy_genai is not None:
        return legacy_genai
    legacy_genai = importlib.import_module("google.generativeai")  # type: ignore
    return legacy_genai


class GeminiAdapter:
    def __init__(self, api_key: str, model: str, api_keys: Optional[list[str]] = None):
        resolved_keys = self._resolve_api_keys(api_key, api_keys)
        if not resolved_keys:
            raise ValueError("GEMINI_API_KEY is required")
        self.api_keys = resolved_keys
        self.api_key = resolved_keys[0]
        self.model = model
        self.mode = "genai" if new_genai is not None else "legacy"
        self._client = None
        self._legacy_model = None
        self._active_key_index = 0
        self._key_cooldown_until: dict[int, float] = {}
        self._lock = threading.Lock()
        self._configure_active_client()

    @staticmethod
    def _resolve_api_keys(api_key: str, api_keys: Optional[list[str]]) -> list[str]:
        keys: list[str] = []
        env_multi = os.getenv("GEMINI_API_KEYS", "") or ""
        candidates: list[str] = []

        if api_keys:
            candidates.extend(api_keys)
        elif api_key:
            candidates.extend(api_key.split(","))
        for key in env_multi.split(","):
            candidates.append(key)

        for raw in candidates:
            key = (raw or "").strip()
            if key and key not in keys:
                keys.append(key)
        return keys

    def _configure_active_client(self) -> None:
        key = self.api_keys[self._active_key_index]
        self.api_key = key
        if self.mode == "genai":
            self._client = new_genai.Client(api_key=key)
            return
        try:
            sdk = _load_legacy_sdk()
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("No Gemini SDK available") from exc
        sdk.configure(api_key=key)
        self._legacy_model = sdk.GenerativeModel(self.model)

    @property
    def sdk_name(self) -> str:
        return self.mode

    @property
    def key_count(self) -> int:
        return len(self.api_keys)

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        tokens = (
            "resource_exhausted",
            "quota exceeded",
            "429",
            "rate limit",
            "ratelimit",
            "too many requests",
        )
        return any(token in msg for token in tokens)

    @staticmethod
    def _extract_retry_seconds(error_text: str) -> int:
        low = (error_text or "").lower()
        # Formats seen:
        # - "Please retry in 58.03s."
        # - "'retryDelay': '20s'"
        match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", low)
        if match:
            return max(1, int(float(match.group(1))))
        match = re.search(r"retrydelay['\"]?\s*:\s*['\"]([0-9]+)s", low)
        if match:
            return max(1, int(match.group(1)))
        return 30

    def _quota_cooldown_seconds(self, error_text: str) -> int:
        low = (error_text or "").lower()
        if "generaterequestsperday" in low or "perday" in low:
            return 24 * 60 * 60
        return self._extract_retry_seconds(error_text)

    def _is_key_available_unlocked(self, key_index: int, now: Optional[float] = None) -> bool:
        ts = now if now is not None else time.time()
        blocked_until = self._key_cooldown_until.get(key_index, 0.0)
        return blocked_until <= ts

    def _find_next_available_key_unlocked(self, start_index: int) -> Optional[int]:
        if len(self.api_keys) <= 1:
            return None
        now = time.time()
        total = len(self.api_keys)
        for step in range(1, total + 1):
            idx = (start_index + step) % total
            if self._is_key_available_unlocked(idx, now):
                return idx
        return None

    def _ensure_active_key_available_unlocked(self) -> None:
        if self._is_key_available_unlocked(self._active_key_index):
            return
        next_idx = self._find_next_available_key_unlocked(self._active_key_index)
        if next_idx is None:
            return
        self._active_key_index = next_idx
        self._configure_active_client()

    def _mark_key_quota_limited_unlocked(self, key_index: int, exc: Exception) -> None:
        cooldown_seconds = self._quota_cooldown_seconds(str(exc))
        self._key_cooldown_until[key_index] = time.time() + cooldown_seconds

    def _rotate_after_quota(self, used_key_index: int, exc: Exception) -> bool:
        with self._lock:
            self._mark_key_quota_limited_unlocked(used_key_index, exc)
            next_idx = self._find_next_available_key_unlocked(used_key_index)
            if next_idx is None:
                return False
            self._active_key_index = next_idx
            self._configure_active_client()
            print(
                "Gemini quota limit reached; rotated API key "
                f"({self._active_key_index + 1}/{len(self.api_keys)})."
            )
            return True

    def generate_content(
        self,
        contents: Any,
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
        timeout_seconds: int = 15,
        use_google_search: bool = False,
    ) -> str:
        attempts = max(1, len(self.api_keys))
        last_error: Optional[Exception] = None

        for _ in range(attempts):
            with self._lock:
                self._ensure_active_key_available_unlocked()
                mode = self.mode
                active_index = self._active_key_index
                client = self._client
                legacy_model = self._legacy_model

            try:
                if mode == "genai":
                    request_config = {
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    }
                    if use_google_search:
                        request_config["tools"] = [{"google_search": {}}]
                    response = client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=request_config,
                    )
                    return getattr(response, "text", "") or ""

                kwargs = {
                    "generation_config": {
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    },
                    "request_options": {"timeout": timeout_seconds},
                }
                response = legacy_model.generate_content(contents, **kwargs)
                return getattr(response, "text", "") or ""
            except Exception as exc:
                last_error = exc
                if not self._is_quota_error(exc):
                    raise
                if not self._rotate_after_quota(active_index, exc):
                    break

        if last_error is not None:
            raise last_error
        raise RuntimeError("Gemini request failed without a captured exception")

    async def generate_content_async(
        self,
        contents: Any,
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
        timeout_seconds: int = 15,
        use_google_search: bool = False,
    ) -> str:
        attempts = max(1, len(self.api_keys))
        last_error: Optional[Exception] = None

        for _ in range(attempts):
            with self._lock:
                self._ensure_active_key_available_unlocked()
                mode = self.mode
                active_index = self._active_key_index
                client = self._client
                legacy_model = self._legacy_model

            try:
                if mode == "genai":
                    request_config = {
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    }
                    if use_google_search:
                        request_config["tools"] = [{"google_search": {}}]
                    response = await client.aio.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=request_config,
                    )
                    return getattr(response, "text", "") or ""

                kwargs = {
                    "generation_config": {
                        "temperature": temperature,
                        "max_output_tokens": max_output_tokens,
                    },
                    "request_options": {"timeout": timeout_seconds},
                }
                response = await legacy_model.generate_content_async(contents, **kwargs)
                return getattr(response, "text", "") or ""
            except Exception as exc:
                last_error = exc
                if not self._is_quota_error(exc):
                    raise
                if not self._rotate_after_quota(active_index, exc):
                    break

        if last_error is not None:
            raise last_error
        raise RuntimeError("Gemini async request failed without a captured exception")

    def upload_file(self, path: str) -> Any:
        if self.mode == "genai":
            return self._client.files.upload(file=path)
        return _load_legacy_sdk().upload_file(path)

    def get_file(self, file_name: str) -> Any:
        if self.mode == "genai":
            return self._client.files.get(name=file_name)
        return _load_legacy_sdk().get_file(file_name)

    def delete_file(self, file_name: str) -> None:
        if self.mode == "genai":
            self._client.files.delete(name=file_name)
            return
        _load_legacy_sdk().delete_file(file_name)
