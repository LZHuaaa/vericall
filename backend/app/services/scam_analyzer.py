"""
VeriCall Malaysia - Malaysian Scam Content Analyzer

Uses Gemini models to analyze call transcripts for scam patterns.
"""
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Optional

from app.config import config
from app.models.schemas import (
    RecommendedAction,
    ScamAnalysis,
    ScamType,
    UrgencyLevel,
)
from app.services.gemini_adapter import GeminiAdapter


class ScamAnalyzer:
    """
    Analyze call content for Malaysian scam patterns with low hardcoding.
    """

    def __init__(self):
        self.client: Optional[GeminiAdapter] = None
        self._is_configured = False
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
            raise ValueError("GEMINI_API_KEY not set in environment")
        self.client = GeminiAdapter(
            api_key=config.GEMINI_API_KEY,
            api_keys=config.GEMINI_API_KEYS,
            model=config.GEMINI_MODEL_FLASH,
        )
        self._is_configured = True
        print(
            f"Scam Analyzer using {config.GEMINI_MODEL_FLASH} "
            f"(sdk={self.client.sdk_name})"
        )

    async def analyze_content(
        self,
        transcript: str,
        deepfake_score: float,
        artifacts_detected: list,
    ) -> ScamAnalysis:
        if not config.GEMINI_API_KEY:
            return self._fallback_analysis(transcript)

        self._configure()
        if self.client.sdk_name != "genai":
            return self._fallback_analysis(transcript)
        prompt = self._build_analysis_prompt(transcript, deepfake_score, artifacts_detected)

        try:
            response_text = await self.client.generate_content_async(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=self.request_timeout_seconds,
            )
            return self._parse_response(response_text)
        except Exception as e:
            print(f"Error analyzing content: {e}")
            return self._fallback_analysis(transcript)

    def analyze_content_sync(
        self,
        transcript: str,
        deepfake_score: float,
        artifacts_detected: list,
    ) -> ScamAnalysis:
        if not config.GEMINI_API_KEY:
            return self._fallback_analysis(transcript)

        self._configure()
        if self.client.sdk_name != "genai":
            return self._fallback_analysis(transcript)
        prompt = self._build_analysis_prompt(transcript, deepfake_score, artifacts_detected)

        try:
            response_text = self._run_with_timeout(
                lambda: self.client.generate_content(
                    contents=prompt,
                    temperature=0.1,
                    max_output_tokens=2048,
                    timeout_seconds=self.request_timeout_seconds,
                ),
                self.request_timeout_seconds + 2,
            )
            return self._parse_response(response_text)
        except TimeoutError:
            print("Scam analysis timed out; using fallback keyword analysis")
            return self._fallback_analysis(transcript)
        except Exception as e:
            print(f"Error analyzing content: {e}")
            return self._fallback_analysis(transcript)

    def _build_analysis_prompt(
        self,
        transcript: str,
        deepfake_score: float,
        artifacts_detected: list,
    ) -> str:
        return f"""You are analyzing a phone call in Malaysia for potential scam.

TRANSCRIPT:
"{transcript}"

AUDIO ANALYSIS:
- Deepfake Score: {deepfake_score:.2f} (0=genuine, 1=synthetic)
- Artifacts Detected: {', '.join(artifacts_detected) if artifacts_detected else 'None'}

MALAYSIAN SCAM PATTERNS TO CHECK:

1. LHDN (Tax Department) Scam:
   - Keywords: LHDN, cukai, tax, refund, Lembaga Hasil
   - Pattern: Claims victim owes taxes, threatens arrest

2. Police/Mahkamah Scam:
   - Keywords: Mahkamah, polis, court, arrest, tangkap, warrant
   - Pattern: Claims victim is involved in crime, demands payment

3. Bank Fraud:
   - Keywords: bank account, akaun bank, PIN, TAC, transfer
   - Pattern: Claims account compromised, requests banking details

4. Family Emergency Scam:
   - Keywords: accident, kemalangan, hospital, urgent, emergency
   - Pattern: Claims family member in trouble, needs immediate money

5. Voice Harvesting / Silent Call:
   - Keywords: "can you say yes", "say your name", silence, "can you hear me"
   - Pattern: Caller is silent or asks victim to say specific words for voice cloning

6. Investment Scam:
   - Keywords: investment, forex, crypto, Bitcoin, guaranteed return, profit, Macau
   - Pattern: Promises high returns, asks for money transfer to "investment account"

7. Courier / Parcel Scam:
   - Keywords: PosLaju, J&T, parcel, bungkusan, customs, kastam, delivery
   - Pattern: Claims parcel held by customs, demands payment or personal details

8. Love / Romance Scam:
   - Keywords: love, sayang, darling, lonely, send money, help me, gift
   - Pattern: Builds romantic relationship, then asks for money

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "is_scam": true or false,
    "confidence": 0.0 to 1.0,
    "scam_type": "lhdn" | "police" | "bank" | "family" | "voice_harvesting" | "investment" | "courier" | "love" | "unknown",
    "claimed_identity": "who the caller claims to be",
    "amount_requested": "RM amount if mentioned, else null",
    "urgency_level": "low" | "medium" | "high" | "critical",
    "red_flags": ["list", "of", "suspicious", "elements"],
    "recommendation": "hang_up" | "verify" | "report_997",
    "reasoning": "brief explanation of your analysis"
}}"""

    def _parse_response(self, response_text: str) -> ScamAnalysis:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = self._repair_truncated_json(text)
            data = json.loads(text)

            return ScamAnalysis(
                is_scam=data.get("is_scam", False),
                confidence=float(data.get("confidence", 0.0)),
                scam_type=ScamType(data.get("scam_type") or "unknown"),
                claimed_identity=data.get("claimed_identity"),
                amount_requested=data.get("amount_requested"),
                urgency_level=UrgencyLevel(data.get("urgency_level") or "low"),
                red_flags=data.get("red_flags") or [],
                recommendation=RecommendedAction(data.get("recommendation") or "verify"),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response_text[:200]}...")
            if '"is_scam": true' in response_text.lower():
                return ScamAnalysis(
                    is_scam=True,
                    confidence=0.8,
                    scam_type=ScamType.UNKNOWN,
                    claimed_identity=None,
                    amount_requested=None,
                    urgency_level=UrgencyLevel.HIGH,
                    red_flags=["Response truncated but scam detected"],
                    recommendation=RecommendedAction.VERIFY,
                )
            return self._fallback_analysis("")

    def _repair_truncated_json(self, text: str) -> str:
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

    def _fallback_analysis(self, transcript: str) -> ScamAnalysis:
        transcript_lower = transcript.lower()
        is_scam = False
        scam_type = ScamType.UNKNOWN
        red_flags = []
        hits_by_type = {}

        for stype, keywords in config.SCAM_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in transcript_lower:
                    is_scam = True
                    hits_by_type[stype] = hits_by_type.get(stype, 0) + 1
                    red_flags.append(f"Keyword detected: {keyword}")

        if hits_by_type:
            dominant_type = max(hits_by_type.items(), key=lambda item: item[1])[0]
            scam_type = ScamType(dominant_type)

        urgency = UrgencyLevel.LOW
        confidence = 0.2
        if is_scam:
            critical_phrases = (
                "otp",
                "tac",
                "pin",
                "password",
                "transfer",
                "bank account",
                "akaun bank",
                "frozen",
                "blocked",
                "suspended",
                "arrest",
                "warrant",
                "mahkamah",
            )
            critical_hits = sum(1 for phrase in critical_phrases if phrase in transcript_lower)
            total_hits = sum(hits_by_type.values())

            confidence = min(0.95, 0.55 + min(0.3, total_hits * 0.08))
            if critical_hits >= 2:
                urgency = UrgencyLevel.CRITICAL
                confidence = max(confidence, 0.9)
            elif critical_hits == 1 or total_hits >= 3:
                urgency = UrgencyLevel.HIGH
                confidence = max(confidence, 0.78)
            else:
                urgency = UrgencyLevel.MEDIUM

        return ScamAnalysis(
            is_scam=is_scam,
            confidence=confidence,
            scam_type=scam_type,
            claimed_identity=None,
            amount_requested=None,
            urgency_level=urgency,
            red_flags=red_flags,
            recommendation=RecommendedAction.VERIFY,
        )


scam_analyzer = ScamAnalyzer()
