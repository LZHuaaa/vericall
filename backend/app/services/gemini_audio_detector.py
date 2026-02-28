"""
Gemini Native Audio Deepfake Detector
"""
import json
import os
from pathlib import Path
from typing import Optional

from app.models.schemas import DeepfakeAnalysis
from app.config import config
from app.services.gemini_adapter import GeminiAdapter


class GeminiAudioDetector:
    """
    Deepfake detection using Gemini native audio capabilities.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = GeminiAdapter(
            api_key=self.api_key,
            api_keys=config.GEMINI_API_KEYS,
            model="gemini-2.0-flash-exp",
        )
        print(f"Gemini Audio Detector initialized (sdk={self.client.sdk_name})")

    def _wait_file_ready(self, file_ref):
        import time

        state = getattr(getattr(file_ref, "state", None), "name", "ACTIVE")
        while state == "PROCESSING":
            time.sleep(2)
            file_ref = self.client.get_file(getattr(file_ref, "name"))
            state = getattr(getattr(file_ref, "state", None), "name", "ACTIVE")
        if state == "FAILED":
            raise ValueError("Audio processing failed")
        return file_ref

    def analyze_audio(self, audio_path: str) -> DeepfakeAnalysis:
        file_ref = self.client.upload_file(audio_path)
        file_ref = self._wait_file_ready(file_ref)
        try:
            response_text = self.client.generate_content(
                contents=[file_ref, self._get_analysis_prompt()],
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=45,
            )
            return self._parse_response(response_text)
        finally:
            try:
                self.client.delete_file(getattr(file_ref, "name"))
            except Exception:
                pass

    async def analyze_audio_async(self, audio_path: str) -> DeepfakeAnalysis:
        import asyncio

        file_ref = self.client.upload_file(audio_path)
        while getattr(getattr(file_ref, "state", None), "name", "ACTIVE") == "PROCESSING":
            await asyncio.sleep(2)
            file_ref = self.client.get_file(getattr(file_ref, "name"))
        try:
            response_text = await self.client.generate_content_async(
                contents=[file_ref, self._get_analysis_prompt()],
                temperature=0.1,
                max_output_tokens=2048,
                timeout_seconds=45,
            )
            return self._parse_response(response_text)
        finally:
            try:
                self.client.delete_file(getattr(file_ref, "name"))
            except Exception:
                pass

    def _get_analysis_prompt(self) -> str:
        return """You are an audio forensics analyst focused on deepfake detection.
Analyze the audio and return JSON:
{
  "deepfake_probability": 0-100,
  "confidence": "low|medium|high",
  "artifacts_detected": ["artifact"],
  "overall_assessment": "real|likely_real|uncertain|likely_fake|definitely_fake",
  "explanation": "2-3 sentence explanation"
}"""

    def _parse_response(self, response_text: str) -> DeepfakeAnalysis:
        try:
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)
            deepfake_prob = float(data.get("deepfake_probability", 50)) / 100.0
            confidence_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
            confidence = confidence_map.get(data.get("confidence", "medium"), 0.5)
            artifacts = data.get("artifacts_detected", [])[:5]
            explanation = data.get("explanation", "") or "Audio analyzed by Gemini"
            return DeepfakeAnalysis(
                deepfake_score=deepfake_prob,
                confidence=confidence,
                artifacts_detected=artifacts,
                explanation=explanation,
            )
        except Exception as e:
            print(f"Error parsing Gemini audio response: {e}")
            score = 0.5
            lower = response_text.lower()
            if "definitely_fake" in lower:
                score = 0.95
            elif "likely_fake" in lower:
                score = 0.75
            elif "likely_real" in lower:
                score = 0.25
            return DeepfakeAnalysis(
                deepfake_score=score,
                confidence=0.5,
                artifacts_detected=["Gemini analysis completed"],
                explanation="Audio analyzed by Gemini AI",
            )


def test_gemini_detector():
    detector = GeminiAudioDetector()
    test_file = input("Enter path to audio file: ")
    if not Path(test_file).exists():
        print(f"File not found: {test_file}")
        return
    result = detector.analyze_audio(test_file)
    print(f"Deepfake Score: {result.deepfake_score:.2%}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Artifacts: {result.artifacts_detected}")
    print(f"Explanation: {result.explanation}")


if __name__ == "__main__":
    test_gemini_detector()
