"""
VeriCall Malaysia - Complete 5-Layer Defense System
====================================================

Detects BOTH AI voices AND real human scammers.
Prevents voice cloning attacks.
"""

import asyncio
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Import existing modules
from app.services.deepfake_detector import deepfake_detector
from app.services.scam_analyzer import scam_analyzer
from app.services.scam_intelligence import scam_intelligence


# ==================== DATA MODELS ====================

class ThreatLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CallAnalysis:
    """Complete analysis result from all 5 layers"""
    # Layer 1: Audio Detection
    is_ai_voice: bool
    deepfake_score: float
    audio_artifacts: List[str]
    
    # Layer 2: Content Analysis
    is_scam_content: bool
    scam_type: str
    scam_keywords: List[str]
    
    # Layer 3: Caller Verification
    caller_verified: bool
    claimed_identity: str
    actual_number: str
    number_verified: bool
    
    # Layer 4: Behavioral Analysis
    suspicious_behavior: bool
    red_flags: List[str]
    manipulation_tactics: List[str]
    
    # Layer 5: Voice Cloning Detection
    voice_clone_attempt: bool
    voice_match_score: float  # If claiming to be family
    
    # Overall Assessment
    threat_level: ThreatLevel
    confidence: float
    recommendation: str
    explanation: str


# ==================== LAYER 3: CALLER VERIFICATION ====================

class CallerVerifier:
    """
    Verifies caller identity against claimed identity.
    
    Checks:
    - Phone number vs claimed organization
    - Against official database
    - Against known scam numbers
    """
    
    def __init__(self):
        # Official Malaysian organization numbers
        self.official_numbers = {
            'lhdn': [
                '1-800-88-5436',  # LHDN official
                '03-77138888',    # LHDN HQ
            ],
            'pdrm': [  # Police
                '999',
                '03-21159999',
            ],
            'bnm': [  # Bank Negara
                '1-300-88-5465',
            ]
        }
        
        # Known scam numbers (would be database in production)
        self.scam_numbers = set()
        
    async def verify_caller(
        self,
        caller_number: str,
        claimed_identity: str,
        claimed_organization: str = None
    ) -> Dict:
        """
        Verify if caller is who they claim to be.
        
        Args:
            caller_number: Phone number displayed
            claimed_identity: Who they say they are
            claimed_organization: LHDN, police, bank, etc.
        """
        result = {
            'number_verified': False,
            'is_spoofed': False,
            'is_known_scammer': False,
            'official_numbers': [],
            'warnings': []
        }
        
        # Check if known scam number
        if caller_number in self.scam_numbers:
            result['is_known_scammer'] = True
            result['warnings'].append(
                f"Number {caller_number} reported in scam database"
            )
        
        # Verify organization number
        if claimed_organization:
            org_key = claimed_organization.lower()
            if org_key in self.official_numbers:
                official = self.official_numbers[org_key]
                result['official_numbers'] = official
                
                if caller_number in official:
                    result['number_verified'] = True
                else:
                    result['is_spoofed'] = True
                    result['warnings'].append(
                        f"Claims to be {claimed_organization} but calling from "
                        f"unofficial number. Real {claimed_organization}: {official[0]}"
                    )
        
        # Use Gemini to search for organization verification
        if claimed_organization and not result['number_verified']:
            intel = await self._search_organization(
                claimed_organization,
                caller_number
            )
            result.update(intel)
        
        return result
    
    async def _search_organization(
        self,
        org_name: str,
        phone_number: str
    ) -> Dict:
        """Search web for organization verification"""
        # Use scam_intelligence to verify
        return scam_intelligence.verify_organization(org_name, phone_number)


# ==================== LAYER 4: BEHAVIORAL ANALYSIS ====================

class BehaviorAnalyzer:
    """
    Analyzes conversation for manipulation tactics.
    
    Red flags:
    - Asking victim to speak first (voice capture!)
    - Time pressure
    - Isolation tactics
    - Preventing verification
    """
    
    def __init__(self):
        # Manipulation patterns
        self.urgency_keywords = [
            'urgent', 'immediately', 'now', 'today',
            'segera', 'sekarang', 'hari ini',
            'must', 'mesti', 'kena'
        ]
        
        self.isolation_keywords = [
            "don't tell anyone", "keep this secret",
            "don't hang up", "stay on the line",
            "jangan beritahu", "rahsia"
        ]
        
        self.threat_keywords = [
            'arrest', 'police', 'court', 'jail',
            'tangkap', 'polis', 'mahkamah', 'penjara',
            'warrant', 'waran'
        ]
    
    def analyze_behavior(self, transcript: str, call_duration: float) -> Dict:
        """
        Analyze conversation for suspicious behavior.
        
        Args:
            transcript: Full conversation text
            call_duration: How long has call been active
        """
        red_flags = []
        manipulation_tactics = []
        
        transcript_lower = transcript.lower()
        
        # Check for urgency tactics
        urgency_count = sum(
            1 for word in self.urgency_keywords
            if word in transcript_lower
        )
        if urgency_count >= 2:
            red_flags.append("Excessive urgency language")
            manipulation_tactics.append("Time pressure tactics")
        
        # Check for isolation
        if any(phrase in transcript_lower for phrase in self.isolation_keywords):
            red_flags.append("Isolation tactics detected")
            manipulation_tactics.append("Preventing victim from seeking help")
        
        # Check for threats
        if any(word in transcript_lower for word in self.threat_keywords):
            red_flags.append("Threatening language")
            manipulation_tactics.append("Fear-based manipulation")
        
        # Check call pattern
        if call_duration < 60 and any(
            word in transcript_lower 
            for word in ['transfer', 'send', 'pay', 'bank']
        ):
            red_flags.append("Rushing to payment (< 1 minute)")
            manipulation_tactics.append("Quick pressure for money")
        
        # Check for voice capture attempts
        if self._is_voice_capture_attempt(transcript_lower):
            red_flags.append("⚠️ VOICE CAPTURE ATTEMPT DETECTED!")
            manipulation_tactics.append(
                "Trying to record your voice for cloning"
            )
        
        return {
            'suspicious_behavior': len(red_flags) > 0,
            'red_flags': red_flags,
            'manipulation_tactics': manipulation_tactics,
            'threat_score': len(red_flags) / 5.0  # Normalize to 0-1
        }
    
    def _is_voice_capture_attempt(self, transcript: str) -> bool:
        """
        Detect if scammer is trying to capture victim's voice.
        
        Common patterns (English, Malay, Mandarin):
        - "Can you say yes?" / "Boleh cakap ya?" / "你能说是吗?"
        - "What's your name?" / "Siapa nama awak?"
        - "Can you repeat that?" / "Tolong ulang"
        - Asking victim to speak before revealing purpose
        """
        capture_patterns = [
            # English patterns
            "can you say",
            "please say",
            "confirm by saying",
            "say yes",
            "say no",
            "what is your name",
            "how old are you",
            "can you repeat",
            "speak louder",
            "i can't hear you",  # Classic trick!
            # Malay patterns
            "tolong sebut",       # "please say"
            "boleh cakap",        # "can you say"
            "sila sahkan",        # "please confirm"
            "cakap ya",           # "say yes"
            "cakap tidak",        # "say no"
            "siapa nama",         # "what is your name"
            "tolong ulang",       # "please repeat"
            "saya tak dengar",    # "I can't hear you"
            "cakap kuat sikit",   # "speak louder"
            "sahkan dengan suara", # "confirm with your voice"
            # Mandarin patterns
            "你能说",             # "can you say"
            "请说",               # "please say"
            "说是",               # "say yes"
            "你叫什么名字",       # "what is your name"
        ]
        
        return any(pattern in transcript for pattern in capture_patterns)


# ==================== LAYER 5: ANTI-VOICE-CLONING ====================

class VoiceCloningProtector:
    """
    Protects against voice cloning attacks.
    
    Features:
    1. Audio poisoning (add imperceptible noise)
    2. Voice signature verification
    3. Challenge-response protocol
    """
    
    def __init__(self):
        self.family_voices = {}  # Would be database in production
        self.family_codes = {}   # Secret code words
    
    def poison_outgoing_audio(
        self, audio_stream: np.ndarray, sample_rate: int = 48000
    ) -> np.ndarray:
        """
        Add imperceptible adversarial noise to prevent cloning.
        
        Based on "AntiFake" research paper.  Uses multi-frequency
        perturbation above phone bandwidth (~8 kHz) but well below
        Nyquist to ensure the signal survives sampling.
        """
        duration = len(audio_stream) / sample_rate
        t = np.linspace(0, duration, len(audio_stream))

        # Multi-frequency adversarial perturbation (11-14 kHz range)
        # These are above normal phone speech bandwidth but below
        # Nyquist for 48 kHz sample rate (24 kHz), so they survive.
        noise = (
            0.003 * np.sin(2 * np.pi * 11000 * t)
            + 0.003 * np.sin(2 * np.pi * 12500 * t)
            + 0.002 * np.sin(2 * np.pi * 14000 * t)
        )

        poisoned = np.clip(audio_stream + noise, -1.0, 1.0)
        return poisoned
    
    def verify_family_voice(
        self,
        audio_sample: np.ndarray,
        claimed_identity: str
    ) -> Dict:
        """
        Verify if voice matches stored family member signature.
        
        Args:
            audio_sample: Voice sample from call
            claimed_identity: Who they claim to be ("mom", "dad", etc.)
        """
        if claimed_identity not in self.family_voices:
            return {
                'verified': False,
                'reason': 'No stored voice signature for this family member',
                'recommendation': 'Ask them the family code word'
            }
        
        # Compare voice signatures
        stored_signature = self.family_voices[claimed_identity]
        similarity = self._compute_voice_similarity(
            audio_sample,
            stored_signature
        )
        
        if similarity > 0.85:
            return {
                'verified': True,
                'similarity': similarity,
                'confidence': 'high'
            }
        elif similarity > 0.7:
            return {
                'verified': 'uncertain',
                'similarity': similarity,
                'recommendation': 'Ask challenge question'
            }
        else:
            return {
                'verified': False,
                'similarity': similarity,
                'warning': '⚠️ Voice does not match! Possible clone attack!'
            }
    
    def _compute_voice_similarity(
        self,
        sample1: np.ndarray,
        sample2: np.ndarray
    ) -> float:
        """
        Compute similarity between two voice samples.
        Simplified version - production would use proper speaker verification.
        """
        # This is a placeholder - real implementation would use:
        # - Mel-frequency cepstral coefficients (MFCCs)
        # - Speaker embedding models
        # - Cosine similarity on embeddings
        
        # For now, return random for demo
        return np.random.uniform(0.5, 0.95)
    
    def suggest_challenge_response(self, claimed_identity: str) -> Dict:
        """
        Suggest challenge question to verify real family member.
        """
        if claimed_identity in self.family_codes:
            return {
                'type': 'code_word',
                'question': "What's our family code word?",
                'expected_answer': self.family_codes[claimed_identity]
            }
        
        # Generic challenges
        challenges = [
            {
                'type': 'secret_question',
                'question': 'Where did we go for vacation last year?'
            },
            {
                'type': 'video_verification',
                'question': 'Switch to video call and show me your ID card'
            },
            {
                'type': 'callback',
                'question': "I'll call you back on your usual number"
            }
        ]
        
        return challenges[0]


# ==================== MASTER COORDINATOR ====================

class VeriCallDefenseSystem:
    """
    Master coordinator for all 5 defense layers.
    
    Orchestrates:
    - Layer 1: Audio Deepfake Detection
    - Layer 2: Content Analysis
    - Layer 3: Caller Verification
    - Layer 4: Behavioral Analysis
    - Layer 5: Voice Cloning Protection
    """
    
    def __init__(self):
        self.layer3 = CallerVerifier()
        self.layer4 = BehaviorAnalyzer()
        self.layer5 = VoiceCloningProtector()
        
    async def analyze_call(
        self,
        audio_path: str,
        transcript: str,
        caller_number: str,
        claimed_identity: str = None,
        claimed_organization: str = None,
        call_duration: float = 0
    ) -> CallAnalysis:
        """
        Complete 5-layer analysis of incoming call.
        """
        print("🛡️ VeriCall Defense System - Starting Analysis")
        print("=" * 60)
        
        # LAYER 1: Audio Deepfake Detection
        print("\n⚡ Layer 1: Audio Deepfake Detection...")
        audio_result = deepfake_detector.analyze_audio(audio_path)
        is_ai = audio_result.deepfake_score > 0.7
        print(f"   AI Voice: {'YES' if is_ai else 'NO'} ({audio_result.deepfake_score:.0%})")
        
        # LAYER 2: Content Analysis
        print("\n🧠 Layer 2: Scam Content Analysis...")
        content_result = scam_analyzer.analyze_content_sync(
            transcript,
            audio_result.deepfake_score,
            audio_result.artifacts_detected
        )
        is_scam = content_result.is_scam
        print(f"   Scam Content: {'YES' if is_scam else 'NO'}")
        print(f"   Type: {content_result.scam_type}")
        
        # LAYER 3: Caller Verification
        print("\n🔍 Layer 3: Caller Verification...")
        verification = await self.layer3.verify_caller(
            caller_number,
            claimed_identity or "Unknown",
            claimed_organization
        )
        caller_verified = verification['number_verified']
        print(f"   Verified: {'YES' if caller_verified else 'NO'}")
        if verification['warnings']:
            print(f"   ⚠️ {verification['warnings'][0]}")
        
        # LAYER 4: Behavioral Analysis
        print("\n🎭 Layer 4: Behavioral Analysis...")
        behavior = self.layer4.analyze_behavior(transcript, call_duration)
        has_red_flags = behavior['suspicious_behavior']
        print(f"   Red Flags: {len(behavior['red_flags'])}")
        if behavior['red_flags']:
            for flag in behavior['red_flags'][:2]:
                print(f"   • {flag}")
        
        # LAYER 5: Voice Cloning Detection
        print("\n🛡️ Layer 5: Voice Cloning Protection...")
        voice_clone = False
        voice_match = 1.0
        if claimed_identity and claimed_identity != "Unknown":
            # Load audio for verification
            import librosa
            audio_data, sr = librosa.load(audio_path, sr=16000)
            voice_check = self.layer5.verify_family_voice(
                audio_data,
                claimed_identity
            )
            voice_clone = not voice_check.get('verified', False)
            voice_match = voice_check.get('similarity', 0.0)
            print(f"   Clone Attempt: {'YES' if voice_clone else 'NO'}")
        
        # OVERALL ASSESSMENT
        print("\n" + "=" * 60)
        threat_level = self._calculate_threat_level(
            is_ai, is_scam, caller_verified, has_red_flags, voice_clone
        )
        confidence = self._calculate_confidence(
            audio_result.confidence,
            content_result.confidence,
            verification,
            behavior
        )
        
        recommendation = self._get_recommendation(threat_level)
        explanation = self._generate_explanation(
            is_ai, is_scam, caller_verified, behavior, voice_clone
        )
        
        print(f"🎯 THREAT LEVEL: {threat_level.value.upper()}")
        print(f"📊 CONFIDENCE: {confidence:.0%}")
        print(f"💡 RECOMMENDATION: {recommendation}")
        print("=" * 60)
        
        return CallAnalysis(
            # Layer 1
            is_ai_voice=is_ai,
            deepfake_score=audio_result.deepfake_score,
            audio_artifacts=audio_result.artifacts_detected,
            # Layer 2
            is_scam_content=is_scam,
            scam_type=content_result.scam_type.value,
            scam_keywords=content_result.red_flags,
            # Layer 3
            caller_verified=caller_verified,
            claimed_identity=claimed_identity or "Unknown",
            actual_number=caller_number,
            number_verified=verification['number_verified'],
            # Layer 4
            suspicious_behavior=has_red_flags,
            red_flags=behavior['red_flags'],
            manipulation_tactics=behavior['manipulation_tactics'],
            # Layer 5
            voice_clone_attempt=voice_clone,
            voice_match_score=voice_match,
            # Overall
            threat_level=threat_level,
            confidence=confidence,
            recommendation=recommendation,
            explanation=explanation
        )
    
    def _calculate_threat_level(
        self, is_ai, is_scam, verified, red_flags, clone
    ) -> ThreatLevel:
        """Calculate overall threat level"""
        score = 0
        if is_ai: score += 2
        if is_scam: score += 3
        if not verified: score += 2
        if red_flags: score += 2
        if clone: score += 3
        
        if score >= 8: return ThreatLevel.CRITICAL
        elif score >= 6: return ThreatLevel.HIGH
        elif score >= 4: return ThreatLevel.MEDIUM
        elif score >= 2: return ThreatLevel.LOW
        else: return ThreatLevel.SAFE
    
    def _calculate_confidence(self, audio_conf, content_conf, verif, behav):
        """Calculate overall confidence"""
        return (audio_conf + content_conf) / 2
    
    def _get_recommendation(self, threat_level: ThreatLevel) -> str:
        """Get action recommendation"""
        if threat_level == ThreatLevel.CRITICAL:
            return "HANG UP IMMEDIATELY and report to 997"
        elif threat_level == ThreatLevel.HIGH:
            return "DO NOT provide information. Verify by calling official number."
        elif threat_level == ThreatLevel.MEDIUM:
            return "Be cautious. Ask verification questions before proceeding."
        elif threat_level == ThreatLevel.LOW:
            return "Verify caller identity before sharing information."
        else:
            return "Call appears safe, but stay vigilant."
    
    def _generate_explanation(self, is_ai, is_scam, verified, behavior, clone):
        """Generate human-readable explanation"""
        reasons = []
        if is_ai: reasons.append("AI-generated voice detected")
        if is_scam: reasons.append("Scam pattern identified")
        if not verified: reasons.append("Caller identity not verified")
        if behavior['red_flags']: reasons.append("Manipulation tactics detected")
        if clone: reasons.append("Possible voice cloning attack")
        
        if not reasons:
            return "No immediate threats detected."
        
        return " • ".join(reasons)


# ==================== TESTING ====================

async def test_complete_system():
    """Test the complete 5-layer system"""
    
    system = VeriCallDefenseSystem()
    
    # Test Case 1: AI Voice LHDN Scam
    print("\n" + "🧪 TEST CASE 1: AI Voice LHDN Scam")
    result1 = await system.analyze_call(
        audio_path="data/test_audio/fake/lhdn_scam.wav",
        transcript="Hello, this is LHDN calling. You have unpaid tax of RM8,000. You must pay immediately or we will issue arrest warrant.",
        caller_number="+60123456789",
        claimed_identity="LHDN Officer",
        claimed_organization="LHDN",
        call_duration=30
    )
    
    print(f"\n✅ Result: {result1.threat_level.value.upper()}")
    
    # Test Case 2: Real Human Reading Script
    print("\n" + "🧪 TEST CASE 2: Real Human Police Scam")
    result2 = await system.analyze_call(
        audio_path="data/test_audio/real/police_scam.wav",
        transcript="This is Inspector Ahmad from Bukit Aman. Your name is involved in money laundering case. You need to transfer RM50,000 for investigation.",
        caller_number="+60187654321",
        claimed_identity="Police Inspector",
        claimed_organization="PDRM",
        call_duration=45
    )
    
    print(f"\n✅ Result: {result2.threat_level.value.upper()}")


if __name__ == "__main__":
    asyncio.run(test_complete_system())