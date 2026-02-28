"""
VeriCall Malaysia - Real-Time Scam Intelligence
"""
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Dict, List

from app.config import config
from app.services.gemini_adapter import GeminiAdapter


class ScamIntelligence:
    """
    Real-time retrieval for scam patterns and organization verification.
    """

    def __init__(self):
        self.client: GeminiAdapter | None = None
        self._is_configured = False
        self.cache = {}
        self.cache_ttl = 3600
        self.request_timeout_seconds = 15

    def _run_with_timeout(self, func, timeout_seconds: int, *args, **kwargs):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            future.cancel()
            raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _configure(self):
        if self._is_configured:
            return
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")

        self.client = GeminiAdapter(
            api_key=config.GEMINI_API_KEY,
            api_keys=config.GEMINI_API_KEYS,
            model=config.GEMINI_MODEL,
        )
        self._is_configured = True
        print(f"Scam Intelligence configured (sdk={self.client.sdk_name})")

    def search_recent_scams(self, scam_type: str = "all") -> dict:
        if not config.GEMINI_API_KEY:
            return self._get_fallback_intel()

        self._configure()
        cache_key = f"scam_{scam_type}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < self.cache_ttl:
                return cached["data"]

        prompt = f"""Search for recent voice/deepfake scam reports in Malaysia.
Type focus: {scam_type if scam_type != "all" else "all types"}.
Return JSON:
{{
  "total_cases_this_week": number,
  "scam_types": {{"lhdn": number, "police": number, "bank": number, "family": number}},
  "average_loss_rm": number,
  "hotspot_states": ["state"],
  "new_tactics": ["tactic"],
  "recent_headlines": ["headline"],
  "sources": ["url"]
}}"""

        try:
            response_text = self._run_with_timeout(
                lambda: self.client.generate_content(
                    contents=prompt,
                    temperature=0.1,
                    max_output_tokens=1024,
                    timeout_seconds=self.request_timeout_seconds,
                    use_google_search=True,
                ),
                self.request_timeout_seconds + 2,
            )
            result = self._parse_intel_response(response_text)
            self.cache[cache_key] = {"timestamp": datetime.now(), "data": result}
            return result
        except Exception as e:
            print(f"Error fetching scam intel: {e}")
            return self._get_fallback_intel()

    async def search_recent_scams_async(self, scam_type: str = "all") -> dict:
        if not config.GEMINI_API_KEY:
            return self._get_fallback_intel()

        self._configure()
        prompt = (
            "Search latest Malaysian voice scam reports. "
            f"Type: {scam_type}. Return JSON with total_cases, tactics, affected_areas, average_loss."
        )

        try:
            response_text = await self.client.generate_content_async(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=1024,
                timeout_seconds=self.request_timeout_seconds,
                use_google_search=True,
            )
            return self._parse_intel_response(response_text)
        except TimeoutError:
            return self._get_fallback_intel()
        except Exception as e:
            print(f"Error: {e}")
            return self._get_fallback_intel()

    def verify_organization(self, org_name: str, phone_number: str = None) -> dict:
        if not config.GEMINI_API_KEY:
            return {
                "organization": org_name,
                "number_verified": "unknown",
                "recommendation": "No Gemini key configured; verify with official hotline.",
            }

        self._configure()
        prompt = f"""Verify legitimacy for this Malaysian organization and caller number.
Organization: {org_name}
Phone Number: {phone_number if phone_number else "Not provided"}
Return JSON:
{{
  "organization": "{org_name}",
  "is_legitimate_org": true,
  "official_numbers": ["number"],
  "number_verified": true/false/"unknown",
  "verification_method": "how to verify",
  "scam_warning": "warning if any",
  "official_website": "official URL"
}}"""

        try:
            response_text = self._run_with_timeout(
                lambda: self.client.generate_content(
                    contents=prompt,
                    temperature=0.1,
                    max_output_tokens=768,
                    timeout_seconds=self.request_timeout_seconds,
                    use_google_search=True,
                ),
                self.request_timeout_seconds + 2,
            )
            return self._parse_verification(response_text)
        except TimeoutError:
            return {
                "organization": org_name,
                "number_verified": "unknown",
                "recommendation": "Verification timed out; call official hotline directly.",
            }
        except Exception as e:
            print(f"Error verifying: {e}")
            return {"error": str(e), "recommendation": "Call official number to verify"}

    def get_community_alerts(self, location: str = "Malaysia") -> List[dict]:
        return [
            {
                "id": "alert_001",
                "type": "lhdn",
                "description": "LHDN impersonation targeting Johor residents",
                "reported_by": "Community",
                "timestamp": datetime.now().isoformat(),
                "verified": True,
                "affected_area": "Johor Bahru",
            },
            {
                "id": "alert_002",
                "type": "police",
                "description": "Fake police calls claiming drug involvement",
                "reported_by": "NSRC",
                "timestamp": datetime.now().isoformat(),
                "verified": True,
                "affected_area": "Selangor",
            },
        ]

    def _parse_intel_response(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception:
            return self._get_fallback_intel()

    def _parse_verification(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception:
            return {"error": "Could not parse", "recommendation": "Verify manually"}

    def _get_fallback_intel(self) -> dict:
        return {
            "total_cases_this_week": 47,
            "scam_types": {"lhdn": 18, "police": 12, "bank": 10, "family": 7},
            "average_loss_rm": 5800,
            "hotspot_states": ["Selangor", "Johor", "Penang", "Kuala Lumpur"],
            "new_tactics": [
                "AI voice cloning of family members",
                "Fake enforcement calls demanding instant transfer",
            ],
            "recent_headlines": [
                "Authorities warn of increasing AI voice scams",
                "Victims lose savings to impersonation calls",
            ],
            "sources": ["NSRC (997)", "Bank Negara Malaysia", "Local news"],
            "note": "Fallback data - live retrieval unavailable",
        }


scam_intelligence = ScamIntelligence()
