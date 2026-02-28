"""
Hybrid Deepfake Detector - VeriCall Malaysia
=============================================

Combines WavLM (fast, accurate) + Gemini (intelligent, context-aware)
for best-in-class deepfake detection.

ARCHITECTURE:
Stage 1: WavLM Quick Screening (0.5 seconds)
  ↓ If suspicious (>70%)
Stage 2: Gemini Deep Analysis (5-10 seconds)
  ↓
Final Decision with confidence scores
"""

import asyncio
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

from app.services.deepfake_detector import deepfake_detector as wavlm_detector
from app.services.gemini_audio_detector import GeminiAudioDetector
from app.models.schemas import DeepfakeAnalysis


class DetectionMode(Enum):
    """Detection mode selection"""
    FAST = "fast"  # WavLM only (0.5s)
    ACCURATE = "accurate"  # WavLM + Gemini (10s)
    GEMINI_ONLY = "gemini_only"  # 100% Google (10s)
    WAVLM_ONLY = "wavlm_only"  # Fastest (0.5s)


class HybridDetector:
    """
    Intelligent hybrid deepfake detector.
    
    Uses two-stage approach:
    1. WavLM for fast screening
    2. Gemini for deep analysis when needed
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None):
        self.wavlm = wavlm_detector
        self.gemini = None
        self.gemini_api_key = gemini_api_key
        
        # Thresholds
        self.wavlm_threshold = 0.7  # Trigger Gemini if WavLM > 70%
        self.high_confidence_threshold = 0.85  # Skip Gemini if very confident
        
        print("🔄 Hybrid Detector initialized")
    
    def _init_gemini(self):
        """Lazy load Gemini (only when needed)"""
        if self.gemini is None:
            print("📡 Loading Gemini for deep analysis...")
            self.gemini = GeminiAudioDetector(self.gemini_api_key)
    
    async def analyze(
        self,
        audio_path: str,
        mode: DetectionMode = DetectionMode.ACCURATE
    ) -> Tuple[DeepfakeAnalysis, dict]:
        """
        Analyze audio with selected mode.
        
        Args:
            audio_path: Path to audio file
            mode: Detection mode (fast/accurate/gemini_only/wavlm_only)
            
        Returns:
            Tuple of (analysis, metadata)
        """
        metadata = {
            "mode": mode.value,
            "stages_used": [],
            "processing_time_seconds": 0
        }
        
        import time
        start_time = time.time()
        
        # MODE: GEMINI ONLY (100% Google)
        if mode == DetectionMode.GEMINI_ONLY:
            self._init_gemini()
            result = await self.gemini.analyze_audio_async(audio_path)
            metadata["stages_used"] = ["gemini"]
            metadata["processing_time_seconds"] = time.time() - start_time
            return result, metadata
        
        # STAGE 1: WavLM Quick Screening
        print("⚡ Stage 1: WavLM screening...")
        wavlm_result = self.wavlm.analyze_audio(audio_path)
        metadata["stages_used"].append("wavlm")
        metadata["wavlm_score"] = wavlm_result.deepfake_score
        
        # MODE: WAVLM ONLY
        if mode == DetectionMode.WAVLM_ONLY:
            metadata["processing_time_seconds"] = time.time() - start_time
            return wavlm_result, metadata
        
        # MODE: FAST - return WavLM result
        if mode == DetectionMode.FAST:
            metadata["processing_time_seconds"] = time.time() - start_time
            return wavlm_result, metadata
        
        # MODE: ACCURATE - decide if Gemini needed
        needs_gemini = (
            wavlm_result.deepfake_score >= self.wavlm_threshold and
            wavlm_result.deepfake_score < self.high_confidence_threshold
        )
        
        if not needs_gemini:
            # WavLM is confident enough
            print(f"✅ WavLM confident ({wavlm_result.deepfake_score:.0%}) - skipping Gemini")
            metadata["processing_time_seconds"] = time.time() - start_time
            metadata["gemini_skipped"] = "wavlm_confident"
            return wavlm_result, metadata
        
        # STAGE 2: Gemini Deep Analysis
        print("🧠 Stage 2: Gemini deep analysis...")
        self._init_gemini()
        gemini_result = await self.gemini.analyze_audio_async(audio_path)
        metadata["stages_used"].append("gemini")
        metadata["gemini_score"] = gemini_result.deepfake_score
        
        # Combine results
        final_result = self._combine_results(wavlm_result, gemini_result)
        metadata["processing_time_seconds"] = time.time() - start_time
        
        return final_result, metadata
    
    def analyze_sync(
        self,
        audio_path: str,
        mode: DetectionMode = DetectionMode.ACCURATE
    ) -> Tuple[DeepfakeAnalysis, dict]:
        """Synchronous version"""
        return asyncio.run(self.analyze(audio_path, mode))
    
    def _combine_results(
        self,
        wavlm_result: DeepfakeAnalysis,
        gemini_result: DeepfakeAnalysis
    ) -> DeepfakeAnalysis:
        """
        Intelligently combine WavLM + Gemini results.
        
        Strategy:
        - If both agree (>0.7 or <0.3): High confidence
        - If they disagree: Average with explanation
        - Merge artifacts from both
        """
        wavlm_score = wavlm_result.deepfake_score
        gemini_score = gemini_result.deepfake_score
        
        # Check agreement
        both_say_fake = wavlm_score > 0.7 and gemini_score > 0.7
        both_say_real = wavlm_score < 0.3 and gemini_score < 0.3
        
        if both_say_fake:
            # Both agree it's fake
            final_score = max(wavlm_score, gemini_score)
            confidence = 0.95
            explanation = f"Both WavLM and Gemini detect synthetic voice (WavLM: {wavlm_score:.0%}, Gemini: {gemini_score:.0%})"
        
        elif both_say_real:
            # Both agree it's real
            final_score = min(wavlm_score, gemini_score)
            confidence = 0.90
            explanation = f"Both systems indicate genuine voice (WavLM: {wavlm_score:.0%}, Gemini: {gemini_score:.0%})"
        
        else:
            # Disagreement - weighted average (WavLM 60%, Gemini 40%)
            final_score = wavlm_score * 0.6 + gemini_score * 0.4
            confidence = 0.6
            explanation = (
                f"Mixed signals: WavLM {wavlm_score:.0%}, Gemini {gemini_score:.0%}. "
                f"Combined score: {final_score:.0%}. Recommend manual verification."
            )
        
        # Merge artifacts
        all_artifacts = list(set(
            wavlm_result.artifacts_detected + 
            gemini_result.artifacts_detected
        ))
        
        return DeepfakeAnalysis(
            deepfake_score=final_score,
            confidence=confidence,
            artifacts_detected=all_artifacts,
            explanation=explanation
        )


# ==================== TESTING SUITE ====================

class DetectorTester:
    """Comprehensive testing suite"""
    
    def __init__(self, detector: HybridDetector):
        self.detector = detector
    
    async def test_single_file(self, audio_path: str):
        """Test single audio file with all modes"""
        print(f"\n{'='*70}")
        print(f"Testing: {audio_path}")
        print('='*70)
        
        if not Path(audio_path).exists():
            print(f"❌ File not found!")
            return
        
        modes = [
            (DetectionMode.FAST, "⚡ FAST MODE (WavLM only)"),
            (DetectionMode.WAVLM_ONLY, "🎯 WavLM ONLY"),
            (DetectionMode.GEMINI_ONLY, "🧠 GEMINI ONLY (100% Google)"),
            (DetectionMode.ACCURATE, "🔬 ACCURATE MODE (Hybrid)"),
        ]
        
        results = {}
        
        for mode, label in modes:
            print(f"\n{label}")
            print("-" * 70)
            
            result, metadata = await self.detector.analyze(audio_path, mode)
            results[mode.value] = (result, metadata)
            
            print(f"Deepfake Score: {result.deepfake_score:.2%}")
            print(f"Confidence: {result.confidence:.2%}")
            print(f"Processing Time: {metadata['processing_time_seconds']:.2f}s")
            print(f"Stages Used: {', '.join(metadata['stages_used'])}")
            
            if result.artifacts_detected:
                print(f"Artifacts:")
                for artifact in result.artifacts_detected[:3]:
                    print(f"  • {artifact}")
            
            print(f"Assessment: {result.explanation[:100]}...")
        
        # Comparison
        print(f"\n{'='*70}")
        print("📊 MODE COMPARISON")
        print('='*70)
        print(f"{'Mode':<20} {'Score':>10} {'Time':>10} {'Verdict':<20}")
        print("-" * 70)
        
        for mode, label in modes:
            result, metadata = results[mode.value]
            verdict = "🤖 FAKE" if result.deepfake_score > 0.6 else "🎤 REAL"
            print(
                f"{mode.value:<20} "
                f"{result.deepfake_score:>9.0%} "
                f"{metadata['processing_time_seconds']:>9.2f}s "
                f"{verdict:<20}"
            )
        
        print('='*70)
    
    async def test_batch(self, audio_dir: str):
        """Test all audio files in directory"""
        audio_path = Path(audio_dir)
        audio_files = list(audio_path.glob("*.wav")) + list(audio_path.glob("*.mp3"))
        
        if not audio_files:
            print(f"❌ No audio files found in {audio_dir}")
            return
        
        print(f"\n🧪 Testing {len(audio_files)} files in ACCURATE mode...")
        
        results = []
        for audio_file in audio_files:
            result, metadata = await self.detector.analyze(
                str(audio_file),
                DetectionMode.ACCURATE
            )
            results.append((audio_file.name, result, metadata))
            print(f"✓ {audio_file.name}: {result.deepfake_score:.0%}")
        
        # Summary
        print(f"\n{'='*70}")
        print("📈 BATCH SUMMARY")
        print('='*70)
        
        fake_count = sum(1 for _, r, _ in results if r.deepfake_score > 0.6)
        real_count = len(results) - fake_count
        avg_time = sum(m['processing_time_seconds'] for _, _, m in results) / len(results)
        
        print(f"Total Files: {len(results)}")
        print(f"Detected Fake: {fake_count}")
        print(f"Detected Real: {real_count}")
        print(f"Avg Processing Time: {avg_time:.2f}s")
        print('='*70)


# ==================== MAIN ====================

async def main():
    """Interactive testing"""
    print("\n" + "="*70)
    print("  VeriCall Malaysia - Hybrid Detector Test Suite")
    print("="*70)
    
    # Initialize detector
    detector = HybridDetector()
    tester = DetectorTester(detector)
    
    print("\nOptions:")
    print("1. Test single file (all modes)")
    print("2. Test directory (batch)")
    print("3. Quick test (WavLM only)")
    
    choice = input("\nEnter choice (1-3): ")
    
    if choice == "1":
        audio_file = input("Enter audio file path: ")
        await tester.test_single_file(audio_file)
    
    elif choice == "2":
        audio_dir = input("Enter directory path: ")
        await tester.test_batch(audio_dir)
    
    elif choice == "3":
        audio_file = input("Enter audio file path: ")
        if Path(audio_file).exists():
            result, metadata = await detector.analyze(
                audio_file,
                DetectionMode.FAST
            )
            print(f"\n⚡ Quick Result:")
            print(f"Score: {result.deepfake_score:.0%}")
            print(f"Time: {metadata['processing_time_seconds']:.2f}s")
            print(f"Verdict: {'🤖 FAKE' if result.deepfake_score > 0.6 else '🎤 REAL'}")
    
    else:
        print("Invalid choice")


# Singleton instance for imports
hybrid_detector = HybridDetector()


if __name__ == "__main__":
    asyncio.run(main())