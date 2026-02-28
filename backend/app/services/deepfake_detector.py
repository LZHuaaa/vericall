"""
VeriCall Malaysia - Improved Audio Deepfake Detector

Enhanced version with:
- Ensemble scoring (multiple methods)
- Audio quality checks
- Confidence thresholds
- Better handling of short/compressed audio
- Reduced false positives
"""
import os
import torch
import torch.nn as nn
import numpy as np
import librosa
from pathlib import Path
from typing import Tuple, List, Dict
from transformers import AutoModel, AutoFeatureExtractor, AutoModelForAudioClassification, Wav2Vec2FeatureExtractor
from app.config import config
from app.models.schemas import DeepfakeAnalysis


class SimpleClassifier(nn.Module):
    """Tiny classifier - only part you need to train!"""
    def __init__(self, input_dim=1024, output_dim=1):
        super().__init__()
        self.fc = nn.Linear(input_dim, output_dim)
    
    def forward(self, x):
        return torch.sigmoid(self.fc(x))


# Pretrained deepfake detection models to try (configurable via env)
PRETRAINED_MODELS = config.DEEPFAKE_MODELS or [
    "motheecreator/Deepfake-audio-detection",
]


class DeepfakeDetector:
    """
    Enhanced deepfake detector with ensemble scoring and quality checks.
    
    Features:
    - Ensemble of multiple detection methods
    - Audio quality validation
    - Confidence-based thresholds
    - Reduced false positives
    """
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.processor = None
        self.classifier = None
        self._is_loaded = False
        self._classifier_trained = False
        self._use_pretrained = False
        self._pretrained_model = None
        self._pretrained_processor = None
        
        # Quality check thresholds
        self.MIN_AUDIO_LENGTH = config.MIN_AUDIO_LENGTH
        self.IDEAL_AUDIO_LENGTH = config.IDEAL_AUDIO_LENGTH
        self.MAX_SILENCE_RATIO = config.MAX_SILENCE_RATIO
        self.CLIPPING_THRESHOLD = config.CLIPPING_THRESHOLD
        self.MIN_ACTIVE_SPEECH_RATIO = config.MIN_ACTIVE_SPEECH_RATIO
        
        # Detection thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = config.DEEPFAKE_HIGH_THRESHOLD
        self.LOW_CONFIDENCE_THRESHOLD = config.DEEPFAKE_LOW_THRESHOLD
        
        # Ensemble weights
        self.PRETRAINED_WEIGHT = config.ENSEMBLE_WEIGHTS.get('pretrained', 0.5)
        self.HEURISTIC_WEIGHT = config.ENSEMBLE_WEIGHTS.get('heuristic', 0.3)
        self.STATISTICAL_WEIGHT = config.ENSEMBLE_WEIGHTS.get('statistical', 0.2)
    
    def load_model(self):
        """Load pretrained model (lazy loading)"""
        if self._is_loaded:
            return
        
        # Try pretrained deepfake detection models first
        for model_name in PRETRAINED_MODELS:
            try:
                print(f"🔄 Trying pretrained model: {model_name}")
                self._pretrained_model = AutoModelForAudioClassification.from_pretrained(
                    model_name,
                    low_cpu_mem_usage=False
                )
                self._pretrained_processor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
                self._pretrained_model = self._pretrained_model.to(self.device)
                self._pretrained_model.eval()
                self._use_pretrained = True
                self._classifier_trained = True
                self._is_loaded = True
                id2label = getattr(self._pretrained_model.config, "id2label", None)
                print(f"✅ Loaded pretrained deepfake detector: {model_name}")
                print(f"   Model labels: {id2label}")
                return
            except Exception as e:
                print(f"⚠️ Could not load {model_name}: {e}")
                continue
        
        # Fallback to WavLM + simple classifier
        print(f"🔄 Falling back to WavLM model: {config.WAVLM_MODEL}")
        
        try:
            self.model = AutoModel.from_pretrained(
                config.WAVLM_MODEL,
                low_cpu_mem_usage=False,
                torch_dtype=torch.float32
            )
            self.processor = AutoFeatureExtractor.from_pretrained(config.WAVLM_MODEL)
            
            self.model = self.model.to(self.device)
            self.model.eval()
            
            self.classifier = SimpleClassifier().to(self.device)
            
            classifier_path = Path(config.CLASSIFIER_PATH) if hasattr(config, 'CLASSIFIER_PATH') else None
            if classifier_path and classifier_path.exists():
                self.classifier.load_state_dict(
                    torch.load(classifier_path, map_location=self.device)
                )
                self._classifier_trained = True
                print("✅ Loaded trained classifier")
            else:
                print("⚠️ No trained classifier found - using ensemble heuristics")
                self._classifier_trained = False
            
            self.classifier.eval()
            self._is_loaded = True
            print("✅ WavLM model loaded successfully")
        except Exception as e:
            print(f"⚠️ WavLM model load failed: {e}")
            print("📊 Using heuristic-only mode")
            self._is_loaded = True
            self._classifier_trained = False
            self.model = None
    
    def analyze_audio(self, audio_path: str) -> DeepfakeAnalysis:
        """
        Analyze audio file for deepfake detection.
        
        Returns enhanced analysis with quality metrics and certainty levels.
        """
        self.load_model()
        
        # Load audio at 16kHz
        waveform, sr = librosa.load(audio_path, sr=config.AUDIO_SAMPLE_RATE)
        
        # Perform quality checks
        quality_info = self._check_audio_quality(waveform)
        
        # Get deepfake score using ensemble method
        score, method_scores = self._get_deepfake_score_ensemble(waveform, quality_info)
        
        # Detect spectral artifacts
        artifacts = self._detect_spectral_artifacts(waveform, sr)
        
        # Determine certainty level
        certainty = self._calculate_certainty(score, quality_info, artifacts)
        
        # Calculate confidence (how sure we are about the score)
        confidence = self._calculate_confidence(score, quality_info, method_scores)
        
        # Determine if it's a deepfake (with confidence/quality gating)
        is_deepfake, decision_reason = self._determine_deepfake_status(
            score, certainty, confidence, artifacts, quality_info
        )
        quality_info["decision_reason"] = decision_reason
        
        # Generate explanation
        explanation = self._generate_explanation(
            score, artifacts, certainty, quality_info, method_scores
        )
        
        return DeepfakeAnalysis(
            deepfake_score=score,
            confidence=confidence,
            artifacts_detected=artifacts,
            explanation=explanation,
            is_deepfake=is_deepfake,
            quality_info=quality_info,
            certainty=certainty,
            method_scores=method_scores
        )
    
    def analyze_audio_bytes(self, audio_bytes: bytes) -> DeepfakeAnalysis:
        """Analyze audio from bytes (for real-time streaming)"""
        self.load_model()
        
        # Convert bytes to numpy array
        waveform = np.frombuffer(audio_bytes, dtype=np.float32)
        
        # Quality checks
        quality_info = self._check_audio_quality(waveform)
        
        # Ensemble scoring
        score, method_scores = self._get_deepfake_score_ensemble(waveform, quality_info)
        
        # Artifacts
        artifacts = self._detect_spectral_artifacts(waveform, config.AUDIO_SAMPLE_RATE)
        
        # Certainty
        certainty = self._calculate_certainty(score, quality_info, artifacts)
        
        # Confidence
        confidence = self._calculate_confidence(score, quality_info, method_scores)
        
        # Deepfake status
        is_deepfake, decision_reason = self._determine_deepfake_status(
            score, certainty, confidence, artifacts, quality_info
        )
        quality_info["decision_reason"] = decision_reason
        
        # Explanation
        explanation = self._generate_explanation(
            score, artifacts, certainty, quality_info, method_scores
        )
        
        return DeepfakeAnalysis(
            deepfake_score=score,
            confidence=confidence,
            artifacts_detected=artifacts,
            explanation=explanation,
            is_deepfake=is_deepfake,
            quality_info=quality_info,
            certainty=certainty,
            method_scores=method_scores
        )
    
    def _check_audio_quality(self, waveform: np.ndarray) -> Dict:
        """
        Check audio quality and return metrics.
        
        Returns quality info dict with flags for various issues.
        """
        if len(waveform.shape) > 1:
            waveform = waveform.flatten()
        
        duration = len(waveform) / config.AUDIO_SAMPLE_RATE
        
        # Check for clipping
        max_amplitude = np.max(np.abs(waveform))
        is_clipped = max_amplitude > self.CLIPPING_THRESHOLD
        
        # Check for excessive silence
        silence_threshold = 0.01
        silence_frames = np.sum(np.abs(waveform) < silence_threshold)
        silence_ratio = silence_frames / len(waveform)
        has_excessive_silence = silence_ratio > self.MAX_SILENCE_RATIO
        
        # Active speech ratio (to avoid analyzing near-silent audio)
        active_threshold = 0.02
        active_frames = np.sum(np.abs(waveform) >= active_threshold)
        active_speech_ratio = active_frames / len(waveform)
        has_low_speech = active_speech_ratio < self.MIN_ACTIVE_SPEECH_RATIO
        
        # Check for compression artifacts (sudden level changes)
        energy = librosa.feature.rms(y=waveform)[0]
        energy_jumps = np.sum(np.abs(np.diff(energy)) > 0.1)
        has_compression = energy_jumps > len(energy) * 0.2
        
        # Overall quality score
        quality_score = 1.0
        if duration < self.MIN_AUDIO_LENGTH:
            quality_score -= 0.3
        if is_clipped:
            quality_score -= 0.2
        if has_excessive_silence:
            quality_score -= 0.2
        if has_low_speech:
            quality_score -= 0.3
        if has_compression:
            quality_score -= 0.1
        quality_score = max(0.0, quality_score)
        
        return {
            'duration': duration,
            'is_too_short': duration < self.MIN_AUDIO_LENGTH,
            'is_clipped': is_clipped,
            'has_excessive_silence': has_excessive_silence,
            'silence_ratio': silence_ratio,
            'active_speech_ratio': active_speech_ratio,
            'has_low_speech': has_low_speech,
            'has_compression_artifacts': has_compression,
            'quality_score': quality_score,
            'max_amplitude': max_amplitude
        }
    
    def _get_deepfake_score_ensemble(
        self, 
        waveform: np.ndarray, 
        quality_info: Dict
    ) -> Tuple[float, Dict]:
        """
        Use ensemble of multiple methods for robust detection.
        
        Returns:
            Tuple of (final_score, individual_method_scores)
        """
        scores = []
        weights = []
        method_scores = {}
        
        # Ensure 1D waveform
        if len(waveform.shape) > 1:
            waveform = waveform.flatten()
        
        # Method 1: Pretrained model (if available)
        if self._use_pretrained and self._pretrained_model is not None:
            try:
                pretrained_score = self._pretrained_inference(waveform)
                
                # Adjust score based on quality
                if quality_info['has_compression_artifacts']:
                    # Reduce extreme scores for compressed audio
                    pretrained_score = pretrained_score * 0.7 + 0.15
                    print(f"🔬 Pretrained (quality-adjusted): {pretrained_score:.2%}")
                else:
                    print(f"🔬 Pretrained: {pretrained_score:.2%}")
                
                scores.append(pretrained_score)
                weights.append(self.PRETRAINED_WEIGHT)
                method_scores['pretrained'] = pretrained_score
            except Exception as e:
                print(f"⚠️ Pretrained inference failed: {e}")
        
        # Method 2: Heuristic analysis (spectral features)
        heuristic_score = self._heuristic_detection(waveform)
        scores.append(heuristic_score)
        weights.append(self.HEURISTIC_WEIGHT)
        method_scores['heuristic'] = heuristic_score
        print(f"🔬 Heuristic: {heuristic_score:.2%}")
        
        # Method 3: Statistical analysis
        stats_score = self._statistical_analysis(waveform)
        scores.append(stats_score)
        weights.append(self.STATISTICAL_WEIGHT)
        method_scores['statistical'] = stats_score
        print(f"🔬 Statistical: {stats_score:.2%}")
        
        # Calculate weighted average
        if not scores:
            return 0.5, {}
        
        final_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        
        # Boost if multiple methods agree (only when already suspicious)
        high_scores = sum(1 for s in scores if s > 0.4)
        if high_scores >= 2 and final_score > 0.6:
            final_score = min(final_score * 1.05, 1.0)  # 5% boost
            print(f"✨ Multiple methods agree - boosting score")
        
        # Apply quality penalty for very short/low-quality audio
        if quality_info['is_too_short']:
            # Push towards uncertain (0.5) for short audio
            final_score = final_score * 0.6 + 0.2
            print(f"⚠️ Short audio penalty applied")
        if quality_info.get('has_low_speech'):
            # Heavier penalty for near-silence
            final_score = final_score * 0.4 + 0.3
            print(f"⚠️ Low speech activity penalty applied")
        
        print(f"🎯 Final ensemble score: {final_score:.2%}")
        method_scores['final'] = final_score
        
        return final_score, method_scores
    
    def _pretrained_inference(self, waveform: np.ndarray) -> float:
        """Run pretrained model inference"""
        try:
            inputs = self._pretrained_processor(
                waveform,
                sampling_rate=config.AUDIO_SAMPLE_RATE,
                return_tensors="pt",
                padding=True
            )
            
            input_values = inputs.input_values.to(self.device)
            
            with torch.no_grad():
                outputs = self._pretrained_model(input_values)
                logits = outputs.logits
                
                probs = torch.softmax(logits, dim=-1)
                # Try to find "fake/spoof" or "real/bonafide" label
                fake_index = None
                real_index = None
                id2label = getattr(self._pretrained_model.config, "id2label", None)
                if id2label:
                    for idx, label in id2label.items():
                        label_lower = label.lower() if isinstance(label, str) else ""
                        if label_lower in ("fake", "spoof", "deepfake", "synthetic"):
                            fake_index = int(idx)
                            break
                        if label_lower in ("real", "bonafide", "genuine", "human"):
                            real_index = int(idx)

                if fake_index is not None:
                    return probs[0, fake_index].item()
                elif real_index is not None:
                    # Invert: fake probability = 1 - real probability
                    return 1.0 - probs[0, real_index].item()
                else:
                    # Unknown labels -- assume binary [real=0, fake=1]
                    fake_index = 1 if probs.shape[-1] > 1 else 0
                    return probs[0, fake_index].item()
                
        except Exception as e:
            print(f"⚠️ Pretrained model error: {e}")
            return 0.5
    
    def _heuristic_detection(self, waveform: np.ndarray) -> float:
        """
        Improved heuristic detection with multiple features.
        """
        try:
            # Spectral flatness (AI voices are too uniform)
            spectral_flatness = librosa.feature.spectral_flatness(y=waveform)
            avg_flatness = np.mean(spectral_flatness)
            
            # Zero crossing rate variance (natural speech varies)
            zcr = librosa.feature.zero_crossing_rate(waveform)
            zcr_std = np.std(zcr)
            zcr_mean = np.mean(zcr)
            
            # Spectral rolloff variance
            rolloff = librosa.feature.spectral_rolloff(
                y=waveform, 
                sr=config.AUDIO_SAMPLE_RATE
            )
            rolloff_std = np.std(rolloff)
            
            # Spectral contrast (voice quality variation)
            contrast = librosa.feature.spectral_contrast(
                y=waveform,
                sr=config.AUDIO_SAMPLE_RATE
            )
            contrast_var = np.var(contrast)
            
            # Score accumulation (0 = natural, 1 = synthetic)
            score = 0.0
            
            # Check 1: Spectral flatness (ADJUSTED for ElevenLabs)
            if avg_flatness > 0.30:  # Was 0.35, now 0.30 - Too flat
                score += 0.30  # Was 0.25, now 0.30
            elif avg_flatness < 0.12:  # Was 0.15 - Too peaked
                score += 0.20  # Was 0.15
            
            # Check 2: ZCR consistency (ADJUSTED)
            if zcr_std < 0.012:  # Was 0.008, now 0.012 - Too consistent
                score += 0.30  # Was 0.25
            
            # Check 3: Rolloff variance (ADJUSTED)
            if rolloff_std < 600:  # Was 400, now 600 - Too consistent
                score += 0.25  # Was 0.20
            
            # Check 4: Spectral contrast (ADJUSTED)
            if contrast_var < 15:  # Was 10, now 15 - Low variation
                score += 0.20  # Was 0.15
            
            # Check 5: Unnaturally high ZCR (ADJUSTED)
            if zcr_mean > 0.12:  # Was 0.15, now 0.12 - some AI voices
                score += 0.20  # Was 0.15
            
            return min(score, 1.0)
            
        except Exception as e:
            print(f"⚠️ Heuristic error: {e}")
            return 0.5
    
    def _statistical_analysis(self, waveform: np.ndarray) -> float:
        """
        Statistical feature analysis for deepfake detection.
        """
        try:
            # Energy variation (real speech has natural dynamics)
            energy = librosa.feature.rms(y=waveform)[0]
            energy_std = np.std(energy)
            energy_range = np.ptp(energy)  # Peak-to-peak
            
            # Spectral centroid (voice brightness variation)
            spectral_centroid = librosa.feature.spectral_centroid(y=waveform)[0]
            centroid_std = np.std(spectral_centroid)
            
            # Pitch analysis
            pitches, magnitudes = librosa.piptrack(
                y=waveform, 
                sr=config.AUDIO_SAMPLE_RATE
            )
            pitch_values = pitches[magnitudes > np.median(magnitudes)]
            
            score = 0.0
            
            # Check energy variation
            if energy_std < 0.008:  # Too consistent
                score += 0.3
            if energy_range < 0.05:  # Too narrow range
                score += 0.2
            
            # Check spectral centroid
            if centroid_std < 80:  # Too consistent
                score += 0.3
            
            # Check pitch if available
            if len(pitch_values) > 10:
                pitch_std = np.std(pitch_values)
                if pitch_std < 8:  # Unnaturally consistent pitch
                    score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            print(f"⚠️ Statistical analysis error: {e}")
            return 0.5
    
    def _detect_spectral_artifacts(self, waveform: np.ndarray, sr: int) -> List[str]:
        """Enhanced spectral artifact detection"""
        artifacts = []
        
        try:
            # Compute spectrogram
            S = librosa.stft(waveform)
            S_db = librosa.amplitude_to_db(np.abs(S), ref=np.max)
            
            # 1. Unnatural harmonics
            harmonics = librosa.effects.harmonic(waveform)
            harmonic_energy = np.mean(np.abs(harmonics))
            if harmonic_energy > 0.35:
                artifacts.append("Unnatural harmonic structure")
            
            # 2. Noise floor (AI voices too clean)
            noise_floor = np.percentile(S_db, 5)
            if noise_floor > -45:  # Adjusted threshold
                artifacts.append("Missing ambient noise")
            
            # 3. Frequency gaps
            freq_bins = np.mean(S_db, axis=1)
            gaps = np.where(freq_bins < np.mean(freq_bins) - 25)[0]
            if len(gaps) > 15:
                artifacts.append("Unnatural frequency gaps")
            
            # 4. Phase consistency
            phase = np.angle(S)
            phase_diff = np.diff(phase, axis=1)
            phase_variance = np.var(phase_diff)
            if phase_variance < 0.3:  # Too consistent
                artifacts.append("Suspicious phase patterns")
            
            # 5. Pitch unnaturalness
            pitches, magnitudes = librosa.piptrack(y=waveform, sr=sr)
            pitch_values = pitches[magnitudes > np.median(magnitudes)]
            if len(pitch_values) > 0:
                pitch_std = np.std(pitch_values)
                if pitch_std < 6:
                    artifacts.append("Unnatural pitch consistency")
            
            # 6. Spectral rolloff consistency
            rolloff = librosa.feature.spectral_rolloff(y=waveform, sr=sr)
            rolloff_std = np.std(rolloff)
            if rolloff_std < 300:
                artifacts.append("Unnaturally consistent timbre")
        
        except Exception as e:
            print(f"⚠️ Spectral analysis error: {e}")
        
        return artifacts
    
    def _calculate_certainty(
        self, 
        score: float, 
        quality_info: Dict, 
        artifacts: List[str]
    ) -> str:
        """
        Determine certainty level of the detection.
        
        Returns: "high", "medium", "low", or "very_low"
        """
        # Start with quality-based certainty
        if quality_info['quality_score'] > 0.8:
            base_certainty = "high"
        elif quality_info['quality_score'] > 0.6:
            base_certainty = "medium"
        elif quality_info['quality_score'] > 0.4:
            base_certainty = "low"
        else:
            base_certainty = "very_low"
        
        # Adjust based on score extremity
        if score > self.HIGH_CONFIDENCE_THRESHOLD or score < self.LOW_CONFIDENCE_THRESHOLD:
            # Extreme scores increase certainty
            if base_certainty == "medium":
                base_certainty = "high"
            elif base_certainty == "low":
                base_certainty = "medium"
        
        # Artifacts support the decision
        if score > 0.6 and len(artifacts) >= 3:
            # Multiple artifacts support deepfake claim
            if base_certainty == "low":
                base_certainty = "medium"
        
        return base_certainty
    
    def _calculate_confidence(
        self, 
        score: float, 
        quality_info: Dict,
        method_scores: Dict
    ) -> float:
        """
        Calculate confidence (0-1) in the detection result.
        
        High confidence when:
        - Good audio quality
        - Methods agree
        - Extreme scores
        """
        confidence = quality_info['quality_score']
        
        # Check method agreement
        if len(method_scores) > 1:
            scores_list = [v for k, v in method_scores.items() if k != 'final']
            if scores_list:
                score_variance = np.var(scores_list)
                # Low variance = high agreement = high confidence
                if score_variance < 0.05:
                    confidence += 0.1
                elif score_variance > 0.15:
                    confidence -= 0.2
        
        # Extreme scores increase confidence
        distance_from_middle = abs(score - 0.5)
        confidence += distance_from_middle * 0.3
        
        return min(max(confidence, 0.0), 1.0)
    
    def _determine_deepfake_status(
        self,
        score: float,
        certainty: str,
        confidence: float,
        artifacts: List[str],
        quality_info: Dict
    ) -> Tuple[bool, str]:
        """
        Determine if audio is a deepfake.
        
        Conservative final escalation:
        - Confidence must be >= 0.75
        - Active speech ratio must be >= 0.25
        - Certainty must not be very_low
        - Score threshold must be reached
        """
        confidence_gate = getattr(config, "DEEPFAKE_CONFIDENCE_GATE", 0.75)
        if confidence < confidence_gate:
            return False, f"confidence_too_low ({confidence:.2f} < {confidence_gate:.2f})"

        active_speech_ratio = quality_info.get("active_speech_ratio", 0.0)
        min_active_speech = getattr(config, "DEEPFAKE_MIN_ACTIVE_SPEECH_FOR_ALERT", 0.25)
        if active_speech_ratio < min_active_speech:
            return False, f"low_active_speech ({active_speech_ratio:.2f} < {min_active_speech:.2f})"

        if certainty == "very_low":
            return False, "certainty_very_low"

        score_threshold_hit = (
            score >= self.HIGH_CONFIDENCE_THRESHOLD
            or score >= config.DEEPFAKE_THRESHOLD
            or (score >= 0.65 and len(artifacts) >= 3)
        )
        if not score_threshold_hit:
            return False, f"score_below_threshold ({score:.2f})"

        return True, "all_gates_passed"
    
    def _generate_explanation(
        self, 
        score: float, 
        artifacts: List[str],
        certainty: str,
        quality_info: Dict,
        method_scores: Dict
    ) -> str:
        """Generate detailed human-readable explanation"""
        
        # Determine risk level
        if score > 0.85:
            risk = "HIGH"
            reason = "Very likely AI-generated voice"
        elif score > 0.65:
            risk = "MEDIUM-HIGH"
            reason = "Possibly synthetic voice"
        elif score > 0.35:
            risk = "UNCERTAIN"
            reason = "Cannot confidently determine authenticity"
        elif score > 0.15:
            risk = "LOW"
            reason = "Likely genuine human voice"
        else:
            risk = "SAFE"
            reason = "Very likely genuine human voice"
        
        explanation = f"[{risk}] {reason} (Score: {score:.0%}, Certainty: {certainty})"
        
        # Add quality warnings
        if quality_info['is_too_short']:
            explanation += f" ⚠️ Short audio ({quality_info['duration']:.1f}s)"
        if quality_info['has_compression_artifacts']:
            explanation += " ⚠️ Compression detected"
        
        # Add artifacts if found
        if artifacts and score > 0.5:
            explanation += f". Detected: {', '.join(artifacts[:2])}"
        
        # Add method agreement info
        if 'pretrained' in method_scores and 'heuristic' in method_scores:
            agreement = abs(method_scores['pretrained'] - method_scores['heuristic'])
            if agreement < 0.1:
                explanation += " ✓ Methods agree"
            elif agreement > 0.3:
                explanation += " ⚠️ Methods disagree"
        
        return explanation


# Singleton instance
deepfake_detector = DeepfakeDetector()
