"""
VeriCall Malaysia - Real-Time Scam Verification via Gemini Grounding

Uses Gemini with Google Search grounding to fact-check caller claims
in real-time against live web data. No hardcoded rules needed --
the system searches Google for matching scam reports as the caller speaks.
"""
import json
from typing import Optional

from app.config import config
from app.services.gemini_adapter import GeminiAdapter


class ScamGroundingService:
    """
    Real-time scam verification using Gemini Grounding with Google Search.
    Searches Google to fact-check caller claims as they speak.
    """

    def __init__(self):
        self.client: Optional[GeminiAdapter] = None
        self._is_configured = False

    def _configure(self):
        if self._is_configured:
            return
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.client = GeminiAdapter(
            api_key=config.GEMINI_API_KEY,
            api_keys=config.GEMINI_API_KEYS,
            model=config.GEMINI_MODEL_FLASH,
        )
        self._is_configured = True

    def verify_caller_claims(
        self,
        transcript_chunk: str,
        caller_claimed_org: Optional[str] = None,
    ) -> dict:
        """
        Ground a live transcript segment against Google Search.
        Checks if the caller's SPECIFIC claims are real or match known scams.
        """
        self._configure()

        org_hint = ""
        if caller_claimed_org:
            org_hint = f"\nThe caller claims to be from: {caller_claimed_org}"

        prompt = f"""A caller in Malaysia just said this on a phone call:
"{transcript_chunk}"
{org_hint}

Verify these SPECIFIC claims by searching Google:
1. If they claim to be from an organization (LHDN, bank, polis, Mahkamah), search for that org's REAL contact methods and whether they actually call people like this
2. If they mention a case number, warrant number, or reference, search if that format is legitimate
3. Search for reports of SIMILAR scam scripts in Malaysia
4. Check if this matches any known scam patterns reported on SemakMule, NSRC, PDRM, or Malaysian news

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "is_verified": false,
    "verification_results": [
        {{
            "claim": "what they claimed",
            "verdict": "verified or unverified or scam_match",
            "evidence": "what Google found",
            "source_url": "where you found it"
        }}
    ],
    "similar_scams_found": 0,
    "risk_assessment": "low or medium or high or critical",
    "recommendation": "what user should do",
    "grounding_summary": "brief summary of what Google Search revealed"
}}"""

        try:
            response_text = self.client.generate_content(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=20,
                use_google_search=True,
            )
            return self._parse_grounding_response(response_text)
        except Exception as e:
            print(f"Grounding verification failed: {e}")
            return {
                "is_verified": False,
                "verification_results": [],
                "similar_scams_found": 0,
                "risk_assessment": "unknown",
                "recommendation": "Could not verify claims. Proceed with caution.",
                "grounding_summary": f"Verification failed: {e}",
                "error": str(e),
            }

    async def verify_caller_claims_async(
        self,
        transcript_chunk: str,
        caller_claimed_org: Optional[str] = None,
    ) -> dict:
        """Async version of verify_caller_claims."""
        self._configure()

        org_hint = ""
        if caller_claimed_org:
            org_hint = f"\nThe caller claims to be from: {caller_claimed_org}"

        prompt = f"""A caller in Malaysia just said this on a phone call:
"{transcript_chunk}"
{org_hint}

Verify these SPECIFIC claims by searching Google:
1. If they claim to be from an organization (LHDN, bank, polis, Mahkamah), search for that org's REAL contact methods and whether they actually call people like this
2. If they mention a case number, warrant number, or reference, search if that format is legitimate
3. Search for reports of SIMILAR scam scripts in Malaysia
4. Check if this matches any known scam patterns reported on SemakMule, NSRC, PDRM, or Malaysian news

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "is_verified": false,
    "verification_results": [
        {{
            "claim": "what they claimed",
            "verdict": "verified or unverified or scam_match",
            "evidence": "what Google found",
            "source_url": "where you found it"
        }}
    ],
    "similar_scams_found": 0,
    "risk_assessment": "low or medium or high or critical",
    "recommendation": "what user should do",
    "grounding_summary": "brief summary of what Google Search revealed"
}}"""

        try:
            response_text = await self.client.generate_content_async(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=20,
                use_google_search=True,
            )
            return self._parse_grounding_response(response_text)
        except Exception as e:
            print(f"Grounding verification failed (async): {e}")
            return {
                "is_verified": False,
                "verification_results": [],
                "similar_scams_found": 0,
                "risk_assessment": "unknown",
                "recommendation": "Could not verify claims. Proceed with caution.",
                "grounding_summary": f"Verification failed: {e}",
                "error": str(e),
            }

    def fetch_latest_scam_patterns(self, region: str = "Malaysia") -> dict:
        """
        Daily intelligence update -- fetches latest scam patterns from
        Google Search. No retraining needed.
        """
        self._configure()

        prompt = f"""Search for the latest voice scam and deepfake scam reports
in {region} from the past 7 days.

Find:
1. New scam tactics reported by PDRM, BNM, MCMC, or NSRC
2. New phone numbers flagged as scam on SemakMule
3. New deepfake voice scam cases in Malaysian news
4. Any government advisories about scams
5. Common scam scripts being used this week

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "region": "{region}",
    "intelligence_date": "today's date",
    "new_patterns": [
        {{
            "scam_type": "type of scam",
            "description": "how the scam works",
            "source": "where this was reported",
            "date_reported": "date",
            "phone_numbers": [],
            "keywords": [],
            "language": "language used"
        }}
    ],
    "government_advisories": [],
    "trending_scam_types": [],
    "total_reports_found": 0
}}"""

        try:
            response_text = self.client.generate_content(
                contents=prompt,
                temperature=0.2,
                max_output_tokens=4096,
                timeout_seconds=30,
                use_google_search=True,
            )
            return self._parse_intelligence_response(response_text)
        except Exception as e:
            print(f"Intelligence fetch failed: {e}")
            return {
                "region": region,
                "new_patterns": [],
                "government_advisories": [],
                "trending_scam_types": [],
                "total_reports_found": 0,
                "error": str(e),
            }

    def _parse_grounding_response(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = self._repair_json(text)
            data = json.loads(text)
            return data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Grounding response parse error: {e}")
            return {
                "is_verified": False,
                "verification_results": [],
                "similar_scams_found": 0,
                "risk_assessment": "unknown",
                "recommendation": "Could not parse verification results.",
                "grounding_summary": response_text[:500],
                "raw_response": response_text[:1000],
            }

    def _parse_intelligence_response(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = self._repair_json(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Intelligence response parse error: {e}")
            return {
                "new_patterns": [],
                "government_advisories": [],
                "trending_scam_types": [],
                "total_reports_found": 0,
                "raw_response": response_text[:1000],
            }

    @staticmethod
    def _repair_json(text: str) -> str:
        text = text.strip()
        open_braces = text.count("{")
        close_braces = text.count("}")
        open_brackets = text.count("[")
        close_brackets = text.count("]")
        if open_braces == close_braces and open_brackets == close_brackets:
            return text
        if text.endswith('"') or text.endswith(","):
            last_comma = text.rfind(",")
            if last_comma > 0:
                text = text[:last_comma]
        while open_brackets > close_brackets:
            text += "]"
            close_brackets += 1
        while open_braces > close_braces:
            text += "}"
            close_braces += 1
        return text


scam_grounding = ScamGroundingService()
