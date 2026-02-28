"""
VeriCall Malaysia - Gemini Audio Analyzer

Uses Gemini 2.0 Flash to analyze audio for deepfake detection.
This provides deep AI analysis as Stage 2 of the hybrid pipeline.

Benefits:
- 100% Google AI technology
- Multi-modal analysis (audio + context)
- Linguistic pattern detection
- Cultural context understanding (Malaysian)
"""
import os
import tempfile
from typing import Dict, Optional
from datetime import datetime
import google.generativeai as genai
from app.config import config


class GeminiAudioAnalyzer:
    """
    Uses Gemini Native Audio for deep audio analysis.
    
    Uses gemini-2.5-flash-native-audio-latest for best audio processing.
    This is Stage 2 of the hybrid detection pipeline.
    """
    
    def __init__(self):
        self.model = None
        self._is_configured = False
    
    def _configure(self):
        """Configure Gemini API"""
        if self._is_configured:
            return
        
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use Native Audio model for best audio deepfake detection
        self.model = genai.GenerativeModel(config.GEMINI_MODEL_AUDIO)
        self._is_configured = True
        print(f"✅ Audio Analyzer using {config.GEMINI_MODEL_AUDIO}")
    
    def analyze_voice(self, audio_path: str) -> Dict:
        """
        Perform deep audio analysis using Gemini's multi-modal capabilities.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Analysis result with synthetic score and detailed findings
        """
        self._configure()
        
        prompt = """Analyze this audio recording for signs of AI-generated or synthetic voice.

CHECK FOR THESE INDICATORS:

1. ACOUSTIC ARTIFACTS:
   - Unnatural pitch consistency (real voices vary naturally)
   - Missing micro-pauses between words
   - Perfect pronunciation without natural hesitations
   - Robotic or mechanical undertones
   - Unnatural breathing patterns or complete absence of breath sounds

2. AUDIO QUALITY CLUES:
   - Too clean/sterile (no background noise in supposedly live call)
   - Unusual frequency patterns
   - Clipping or artifacts at word boundaries
   - Inconsistent volume levels

3. SPEECH PATTERNS:
   - Unnatural rhythm or cadence
   - Missing emotional variation
   - Robotic intonation patterns
   - Too perfect grammar for casual speech

4. MALAYSIAN CONTEXT:
   - Check if accent matches claimed identity
   - Natural code-switching (Manglish) patterns
   - Regional dialect consistency

Provide your analysis in this JSON format:
{
    "synthetic_probability": 0.0 to 1.0,
    "confidence": 0.0 to 1.0,
    "voice_characteristics": {
        "pitch_consistency": "natural|unnatural|suspicious",
        "breathing_patterns": "present|absent|artificial",
        "background_noise": "natural|too_clean|artificial",
        "emotional_variation": "natural|flat|exaggerated"
    },
    "acoustic_artifacts": ["list of detected artifacts"],
    "speech_analysis": {
        "rhythm": "natural|robotic|suspicious",
        "accent_match": "consistent|inconsistent|unknown",
        "language_patterns": "natural|unnatural"
    },
    "assessment": "likely_human|possibly_synthetic|likely_synthetic|definitely_synthetic",
    "reasoning": "brief explanation of your conclusion"
}"""

        try:
            # Upload audio file to Gemini
            audio_file = genai.upload_file(audio_path)
            
            # Analyze with Gemini
            response = self.model.generate_content([
                audio_file,
                prompt
            ])
            
            # Parse response
            return self._parse_response(response.text)
            
        except Exception as e:
            print(f"❌ Gemini audio analysis error: {e}")
            return self._fallback_result(str(e))
    
    async def analyze_voice_async(self, audio_path: str) -> Dict:
        """Async version of analyze_voice"""
        self._configure()
        
        prompt = """Analyze this audio for synthetic/AI-generated voice indicators.
Return JSON with: synthetic_probability, confidence, voice_characteristics, assessment, reasoning."""

        try:
            audio_file = genai.upload_file(audio_path)
            
            response = await self.model.generate_content_async([
                audio_file,
                prompt
            ])
            
            return self._parse_response(response.text)
            
        except Exception as e:
            print(f"❌ Gemini audio analysis error: {e}")
            return self._fallback_result(str(e))
    
    def analyze_audio_bytes(self, audio_bytes: bytes) -> Dict:
        """
        Analyze audio from bytes by saving to temp file first.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        try:
            return self.analyze_voice(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured format"""
        import json
        
        try:
            # Clean response
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            return json.loads(text)
            
        except json.JSONDecodeError:
            # Try to extract key information from text response
            return {
                "synthetic_probability": 0.5,
                "confidence": 0.3,
                "assessment": "unable_to_parse",
                "raw_response": response_text,
                "reasoning": "Could not parse structured response"
            }
    
    def _fallback_result(self, error: str) -> Dict:
        """Fallback result when analysis fails"""
        return {
            "synthetic_probability": 0.5,
            "confidence": 0.0,
            "assessment": "analysis_failed",
            "error": error,
            "reasoning": "Analysis failed - defaulting to uncertain"
        }


# Singleton instance
gemini_audio_analyzer = GeminiAudioAnalyzer()
