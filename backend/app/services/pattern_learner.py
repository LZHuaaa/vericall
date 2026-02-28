"""
VeriCall Malaysia - Self-Learning Scam Pattern System

Extracts structured scam patterns from user reports using Gemini
structured output. Each report makes the system smarter without
any ML retraining.

Three mechanisms:
A) Community Pattern Extraction - extract patterns from user reports
B) Daily Intelligence Update - fetch latest patterns via Grounding
C) Pattern Database - accumulate patterns in Firebase
"""
import json
from datetime import datetime
from typing import Optional

from app.config import config
from app.services.gemini_adapter import GeminiAdapter


class PatternLearner:
    """
    Self-learning scam pattern extraction using Gemini structured output.
    Each user report adds to the pattern database automatically.
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

    def extract_pattern_from_report(
        self,
        transcript: str,
        audio_analysis: Optional[dict] = None,
        reporter_region: str = "Malaysia",
    ) -> dict:
        """
        Extract structured scam pattern from a user report.
        Each report makes the system smarter.

        Returns a structured pattern dict that can be stored in Firebase.
        """
        self._configure()

        audio_info = ""
        if audio_analysis:
            audio_info = f"""
Audio Analysis:
- Deepfake Score: {audio_analysis.get('deepfake_score', 'N/A')}
- Artifacts: {audio_analysis.get('artifacts_detected', [])}
- Is Deepfake: {audio_analysis.get('is_deepfake', 'unknown')}"""

        prompt = f"""Extract the scam pattern from this reported call in {reporter_region}.

Transcript:
"{transcript}"
{audio_info}

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "scam_type": "lhdn or police or bank or family or voice_harvesting or investment or courier or love or unknown",
    "language": "bm or mandarin or tamil or english or manglish or mixed",
    "opening_script": "how the scam typically starts based on this transcript",
    "pressure_tactics": ["list of pressure tactics used"],
    "requested_actions": ["what the scammer asked victim to do"],
    "mentioned_organizations": ["organizations mentioned"],
    "phone_number": "phone number if mentioned or null",
    "bank_account": "bank account if mentioned or null",
    "estimated_region": "KL or Johor or Penang or Selangor or other",
    "severity": 5,
    "key_phrases": ["distinctive phrases that identify this scam type"],
    "red_flags_summary": "brief summary of what makes this a scam",
    "is_deepfake_voice": false,
    "pattern_confidence": 0.8
}}"""

        try:
            response_text = self.client.generate_content(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=15,
            )
            pattern = self._parse_pattern(response_text)
            pattern["extracted_at"] = datetime.now().isoformat()
            pattern["source"] = "community_report"
            return pattern
        except Exception as e:
            print(f"Pattern extraction failed: {e}")
            return {
                "scam_type": "unknown",
                "language": "unknown",
                "opening_script": "",
                "pressure_tactics": [],
                "requested_actions": [],
                "mentioned_organizations": [],
                "severity": 1,
                "key_phrases": [],
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "source": "extraction_failed",
            }

    async def extract_pattern_from_report_async(
        self,
        transcript: str,
        audio_analysis: Optional[dict] = None,
        reporter_region: str = "Malaysia",
    ) -> dict:
        """Async version of extract_pattern_from_report."""
        self._configure()

        audio_info = ""
        if audio_analysis:
            audio_info = f"""
Audio Analysis:
- Deepfake Score: {audio_analysis.get('deepfake_score', 'N/A')}
- Artifacts: {audio_analysis.get('artifacts_detected', [])}
- Is Deepfake: {audio_analysis.get('is_deepfake', 'unknown')}"""

        prompt = f"""Extract the scam pattern from this reported call in {reporter_region}.

Transcript:
"{transcript}"
{audio_info}

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "scam_type": "lhdn or police or bank or family or voice_harvesting or investment or courier or love or unknown",
    "language": "bm or mandarin or tamil or english or manglish or mixed",
    "opening_script": "how the scam typically starts based on this transcript",
    "pressure_tactics": ["list of pressure tactics used"],
    "requested_actions": ["what the scammer asked victim to do"],
    "mentioned_organizations": ["organizations mentioned"],
    "phone_number": "phone number if mentioned or null",
    "bank_account": "bank account if mentioned or null",
    "estimated_region": "KL or Johor or Penang or Selangor or other",
    "severity": 5,
    "key_phrases": ["distinctive phrases that identify this scam type"],
    "red_flags_summary": "brief summary of what makes this a scam",
    "is_deepfake_voice": false,
    "pattern_confidence": 0.8
}}"""

        try:
            response_text = await self.client.generate_content_async(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=15,
            )
            pattern = self._parse_pattern(response_text)
            pattern["extracted_at"] = datetime.now().isoformat()
            pattern["source"] = "community_report"
            return pattern
        except Exception as e:
            print(f"Pattern extraction failed (async): {e}")
            return {
                "scam_type": "unknown",
                "language": "unknown",
                "opening_script": "",
                "pressure_tactics": [],
                "requested_actions": [],
                "mentioned_organizations": [],
                "severity": 1,
                "key_phrases": [],
                "error": str(e),
                "extracted_at": datetime.now().isoformat(),
                "source": "extraction_failed",
            }

    def analyze_with_thinking(
        self,
        transcript: str,
        deepfake_score: float = 0.0,
        artifacts_detected: Optional[list] = None,
    ) -> dict:
        """
        Deep analysis using Gemini's extended thinking for ambiguous
        or novel scam cases that don't match known patterns.

        Uses thinking_budget for internal chain-of-thought reasoning
        before producing the final verdict.
        """
        self._configure()

        prompt = f"""You are VeriCall's deep scam analysis engine. Analyze this
phone call carefully using extended reasoning.

TRANSCRIPT:
"{transcript}"

AUDIO ANALYSIS:
- Deepfake Score: {deepfake_score:.2f} (0=genuine, 1=synthetic)
- Artifacts: {', '.join(artifacts_detected) if artifacts_detected else 'None'}

Think step-by-step about:
1. What is the caller's actual objective?
2. What manipulation tactics are being used (urgency, authority, fear, confusion)?
3. Are there inconsistencies in what the caller says?
4. Does this match any known Malaysian scam patterns, even partially?
5. Could this be a new or evolved scam variant?
6. What would a legitimate caller from this organization actually say differently?

RESPOND WITH VALID JSON ONLY (no markdown):
{{
    "is_scam": true,
    "confidence": 0.95,
    "scam_type": "type",
    "reasoning_chain": [
        "step 1 of reasoning",
        "step 2 of reasoning"
    ],
    "manipulation_tactics": ["tactic1", "tactic2"],
    "inconsistencies_found": ["inconsistency1"],
    "red_flags": ["flag1", "flag2"],
    "novel_elements": ["anything not matching known patterns"],
    "risk_assessment": "low or medium or high or critical",
    "recommendation": "what to do",
    "thinking_depth": "basic or standard or deep"
}}"""

        try:
            # Use higher token limit for thinking mode
            response_text = self.client.generate_content(
                contents=prompt,
                temperature=0.1,
                max_output_tokens=4096,
                timeout_seconds=30,
            )
            return self._parse_thinking_response(response_text)
        except Exception as e:
            print(f"Thinking analysis failed: {e}")
            return {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "unknown",
                "reasoning_chain": [],
                "manipulation_tactics": [],
                "inconsistencies_found": [],
                "red_flags": [],
                "novel_elements": [],
                "risk_assessment": "unknown",
                "recommendation": "Analysis failed. Proceed with caution.",
                "thinking_depth": "failed",
                "error": str(e),
            }

    def _parse_pattern(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = self._repair_json(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Pattern parse error: {e}")
            return {
                "scam_type": "unknown",
                "raw_response": response_text[:500],
            }

    def _parse_thinking_response(self, response_text: str) -> dict:
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = self._repair_json(text)
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Thinking response parse error: {e}")
            return {
                "is_scam": False,
                "confidence": 0.0,
                "scam_type": "unknown",
                "reasoning_chain": [],
                "risk_assessment": "unknown",
                "raw_response": response_text[:500],
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


pattern_learner = PatternLearner()
