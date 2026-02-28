"""
VeriCall Malaysia - API Routes

REST endpoints for the VeriCall mobile app.
"""
import os
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.services import (
    call_orchestrator,
    deepfake_detector,
    scam_analyzer,
    uncle_ah_hock,
    scam_intelligence,
    firebase_service,
    hybrid_detector,
    threat_orchestrator,
    scam_grounding,
    pattern_learner,
    scam_vaccine_trainer,
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/call/demo/start", methods=["POST"])
def start_demo_call():
    """Start single-device demo call and trigger victim phone ring."""
    data = request.get_json() or {}
    session_id = str(data.get("session_id", "")).strip()
    caller_label = str(data.get("caller_label", "Suspected Scammer")).strip()
    timestamp = str(data.get("timestamp", "")).strip() or datetime.now().isoformat()

    result = call_orchestrator.start_demo_call(
        session_id=session_id,
        caller_label=caller_label,
        timestamp=timestamp,
    )
    return jsonify(result)


@api_bp.route("/call/demo/answer", methods=["POST"])
def answer_demo_call():
    """Answer ringing demo call (first-answer wins)."""
    data = request.get_json() or {}
    session_id = str(data.get("session_id", "")).strip()
    device = str(data.get("device", "web")).strip().lower()
    client_id = str(data.get("client_id", "")).strip()
    answered_by_label = str(data.get("answered_by_label", "")).strip() or None

    result = call_orchestrator.answer_demo_call(
        session_id=session_id,
        device=device,
        client_id=client_id,
        answered_by_label=answered_by_label,
    )

    if result.get("accepted") is False and result.get("reason") == "already_answered":
        return jsonify(result), 409
    if result.get("accepted") is False and result.get("reason") in ("session_id_required", "client_id_required"):
        return jsonify(result), 400
    if result.get("accepted") is False and result.get("reason") == "session_not_found":
        return jsonify(result), 404
    if result.get("accepted") is False:
        return jsonify(result), 409
    return jsonify(result)


@api_bp.route("/call/demo/session/<session_id>", methods=["GET"])
def get_demo_call_session(session_id):
    """Get latest call session state for synchronization."""
    normalized = str(session_id or "").strip()
    if not normalized:
        return jsonify({"error": "session_id required"}), 400
    result = call_orchestrator.get_session(normalized)
    if not result:
        return jsonify({"error": "session_not_found"}), 404
    return jsonify(result)


@api_bp.route("/call/demo/end", methods=["POST"])
def end_demo_call():
    """End active demo call."""
    data = request.get_json() or {}
    session_id = str(data.get("session_id", "")).strip() or None
    ended_by = str(data.get("ended_by", "web_client")).strip()
    device = str(data.get("device", "")).strip().lower() or None
    client_id = str(data.get("client_id", "")).strip() or None
    reason_codes = data.get("reason_codes")
    if not isinstance(reason_codes, list):
        reason_codes = []
    result = call_orchestrator.end_demo_call(
        session_id=session_id,
        ended_by=ended_by,
        reason_codes=reason_codes,
        device=device,
        client_id=client_id,
    )
    if result.get("ok") is False and result.get("error") == "not_owner":
        return jsonify(result), 403
    return jsonify(result)


@api_bp.route("/threat/live", methods=["POST"])
def threat_live():
    """
    Threat engine v2 live assessment endpoint.
    """
    data = request.get_json() or {}
    session_id = str(data.get("session_id", "")).strip()
    timestamp = str(data.get("timestamp", "")).strip()

    if not session_id or not timestamp:
        return jsonify({"error": "session_id and timestamp are required"}), 400

    try:
        assessment = threat_orchestrator.assess_live(data)
        call_orchestrator.record_threat_snapshot(
            session_id=session_id,
            assessment=assessment,
        )
        call_orchestrator.record_call_action(
            session_id=session_id,
            call_action=str(assessment.get("call_action", "none")),
            risk_score=float(assessment.get("risk_score", 0.0)),
            reason_codes=assessment.get("call_action_reason_codes") or [],
        )
        return jsonify(assessment)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        print(f"Threat live error: {exc}")
        return jsonify({
            "error": "threat_assessment_failed",
            "mode": "degraded_local",
            "risk_level": "low",
            "risk_score": 0.2,
            "confidence": 0.25,
            "reason_codes": ["threat_engine_error"],
            "recommended_actions": ["verify_identity_with_official_channel"],
            "evidence_items": [],
            "retrieval_status": "error",
            "signals": [],
            "version": "threat-v2",
            "call_action": "none",
            "call_action_confidence": 0.0,
            "call_action_reason_codes": [],
            "hangup_after_ms": None,
        }), 200


@api_bp.route("/threat/session/<session_id>", methods=["GET"])
def get_threat_session(session_id):
    """Get latest threat session state and timeline."""
    result = threat_orchestrator.get_session(session_id)
    if not result:
        return jsonify({"error": "session_not_found"}), 404
    return jsonify(result)


@api_bp.route("/threat/session/<session_id>/finalize", methods=["POST"])
def finalize_threat_session(session_id):
    """Finalize threat session and materialize summary."""
    try:
        result = threat_orchestrator.finalize_session(session_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"finalize_failed: {exc}"}), 500


# ══════════════════════════════════════════════════════════════════
# CALL ANALYSIS ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/analyze", methods=["POST"])
def analyze_audio():
    """
    Analyze audio for deepfake detection and scam patterns.
    
    Request:
        - audio: Audio file (WAV, MP3)
        - transcript: Optional transcript if already available
        
    Response:
        - deepfake analysis results
        - scam analysis results
        - recommended action
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    transcript = request.form.get("transcript", "")
    
    # Save audio temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        audio_path = tmp.name
    
    try:
        # Layer 1: Deepfake Detection
        deepfake_result = deepfake_detector.analyze_audio(audio_path)
        
        # Layer 2: Scam Content Analysis (if transcript provided)
        scam_result = None
        if transcript:
            scam_result = scam_analyzer.analyze_content_sync(
                transcript,
                deepfake_result.deepfake_score,
                deepfake_result.artifacts_detected
            )
        
        # Determine if alert should be triggered
        should_alert = (
            deepfake_result.is_deepfake or
            (scam_result and scam_result.is_scam and scam_result.confidence > 0.8)
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "deepfake": {
                "score": deepfake_result.deepfake_score,
                "confidence": deepfake_result.confidence,
                "artifacts": deepfake_result.artifacts_detected,
                "explanation": deepfake_result.explanation
            },
            "should_alert": should_alert
        }
        
        if scam_result:
            response["scam"] = {
                "is_scam": scam_result.is_scam,
                "confidence": scam_result.confidence,
                "scam_type": scam_result.scam_type.value,
                "claimed_identity": scam_result.claimed_identity,
                "amount_requested": scam_result.amount_requested,
                "urgency": scam_result.urgency_level.value,
                "red_flags": scam_result.red_flags,
                "recommendation": scam_result.recommendation.value
            }
        
        return jsonify(response)
        
    finally:
        # Clean up temp file
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@api_bp.route("/analyze/audio", methods=["POST"])
def analyze_audio_stream():
    """
    Analyze audio stream for deepfake detection (real-time streaming).
    
    This endpoint accepts base64-encoded PCM audio data from the frontend
    and returns WavLM deepfake analysis results.
    
    Request (JSON):
        - audio: Base64-encoded PCM audio data (Float32Array)
        - sample_rate: Audio sample rate (default: 16000)
        
    Response:
        - deepfake_score: 0.0-1.0 probability of AI-generated voice
        - is_deepfake: Boolean if score > 0.7
        - artifacts_detected: List of detected audio artifacts
        - confidence: Analysis confidence
    """
    import base64
    import numpy as np
    
    data = request.get_json()
    if not data or "audio" not in data:
        return jsonify({"error": "No audio data provided"}), 400
    
    try:
        # Decode base64 audio
        audio_base64 = data["audio"]
        sample_rate = data.get("sample_rate", 16000)
        
        # Decode to bytes then to float32 array
        audio_bytes = base64.b64decode(audio_base64)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        
        # Analyze with deepfake detector
        result = deepfake_detector.analyze_audio_bytes(audio_array.tobytes())
        
        return jsonify({
            "deepfake_score": result.deepfake_score,
            "is_deepfake": result.is_deepfake,
            "artifacts_detected": result.artifacts_detected,
            "confidence": result.confidence,
            "explanation": result.explanation,
            "quality_score": (result.quality_info or {}).get("quality_score", 0.0),
            "active_speech_ratio": (result.quality_info or {}).get("active_speech_ratio", 0.0),
            "certainty": result.certainty,
            "decision_reason": (result.quality_info or {}).get("decision_reason", "")
        })
        
    except Exception as e:
        print(f"Audio analysis error: {e}")
        return jsonify({
            "error": str(e),
            "deepfake_score": 0.0,
            "is_deepfake": False,
            "artifacts_detected": [],
            "confidence": 0.0,
            "quality_score": 0.0,
            "active_speech_ratio": 0.0,
            "certainty": "very_low",
            "decision_reason": "analysis_error"
        }), 500

@api_bp.route("/analyze/simple", methods=["POST"])
def analyze_simple():
    """
    Complete analysis: Deepfake detection + Scam analysis.
    
    This is the main endpoint for real-time call analysis.
    
    Request:
        - audio: Audio file (WAV, MP3)
        - transcript: Optional transcript if already available
        
    Response:
        - deepfake_analysis: Deepfake detection results
        - scam_analysis: Scam pattern detection
        - overall_risk_score: Combined risk (0-1)
        - should_alert_user: Boolean
        - should_deploy_uncle: Boolean
        - alert_message: User-friendly message
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    transcript = request.form.get("transcript", "")
    
    # Save audio temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        audio_path = tmp.name
    
    try:
        # Step 1: Deepfake detection
        deepfake_result = deepfake_detector.analyze_audio(audio_path)
        
        print(f"🔬 Deepfake Analysis:")
        print(f"   Score: {deepfake_result.deepfake_score:.2%}")
        print(f"   Confidence: {deepfake_result.confidence:.2%}")
        print(f"   Is Deepfake: {deepfake_result.is_deepfake}")
        print(f"   Certainty: {deepfake_result.certainty}")
        
        # Step 2: Scam content analysis
        scam_result = None
        if transcript:
            scam_result = scam_analyzer.analyze_content_sync(
                transcript,
                deepfake_result.deepfake_score,
                deepfake_result.artifacts_detected
            )
        
        # Step 3: Calculate overall risk
        overall_risk = calculate_overall_risk(deepfake_result, scam_result)
        
        # Step 4: Determine actions
        should_alert = should_alert_user(deepfake_result, scam_result, overall_risk)
        should_deploy = should_deploy_uncle(deepfake_result, scam_result, overall_risk)
        
        # Step 5: Generate alert message
        alert_msg = generate_alert_message(deepfake_result, scam_result, overall_risk)
        
        response = {
            "deepfake_analysis": {
                "deepfake_score": deepfake_result.deepfake_score,
                "confidence": deepfake_result.confidence,
                "is_deepfake": deepfake_result.is_deepfake,
                "certainty": deepfake_result.certainty,
                "artifacts": deepfake_result.artifacts_detected,
                "explanation": deepfake_result.explanation,
            },
            "overall_risk_score": overall_risk,
            "should_alert_user": should_alert,
            "should_deploy_uncle": should_deploy,
            "alert_message": alert_msg
        }
        
        if scam_result:
            response["scam_analysis"] = {
                "is_scam": scam_result.is_scam,
                "confidence": scam_result.confidence,
                "scam_type": scam_result.scam_type.value,
                "urgency": scam_result.urgency_level.value,
                "red_flags": scam_result.red_flags,
                "recommendation": scam_result.recommendation.value
            }
        
        return jsonify(response)
        
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def calculate_overall_risk(deepfake_result, scam_result) -> float:
    """Calculate overall risk score (0-1) from both analyses."""
    risk = 0.0
    
    # Start with scam confidence if available
    if scam_result:
        risk = scam_result.confidence * 0.6
    
    # Add deepfake boost ONLY if high confidence
    if deepfake_result.deepfake_score > 0.85:
        risk += deepfake_result.deepfake_score * 0.4
    elif deepfake_result.is_deepfake and deepfake_result.certainty == "high":
        risk += 0.2
    
    # Penalize for low quality/certainty
    if deepfake_result.certainty == "very_low":
        risk *= 0.7
    
    return min(risk, 1.0)


def should_alert_user(deepfake_result, scam_result, overall_risk) -> bool:
    """Determine if user should be alerted."""
    if overall_risk > 0.75:
        return True
    if scam_result and scam_result.is_scam and scam_result.confidence > 0.8:
        return True
    if deepfake_result.is_deepfake and scam_result and scam_result.is_scam:
        return True
    return False


def should_deploy_uncle(deepfake_result, scam_result, overall_risk) -> bool:
    """Determine if Uncle Ah Hock should be deployed."""
    if overall_risk > 0.85:
        return True
    if deepfake_result.is_deepfake and scam_result and scam_result.is_scam:
        if scam_result.confidence > 0.75:
            return True
    return False


def generate_alert_message(deepfake_result, scam_result, overall_risk) -> str:
    """Generate user-friendly alert message."""
    if overall_risk > 0.9:
        severity = "🚨 CRITICAL SCAM ALERT"
    elif overall_risk > 0.75:
        severity = "⚠️ HIGH RISK SCAM"
    elif overall_risk > 0.5:
        severity = "⚠️ SUSPICIOUS CALL"
    else:
        severity = "ℹ️ NOTICE"
    
    msg = f"{severity}\n\n"
    
    if deepfake_result.is_deepfake:
        msg += f"🎭 AI Voice Detected ({deepfake_result.deepfake_score:.0%} confidence)\n"
    
    if scam_result and scam_result.is_scam:
        msg += f"📞 Scam Type: {scam_result.scam_type.value}\n"
        msg += f"⚠️ Red Flags: {', '.join(scam_result.red_flags[:3])}\n"
    
    return msg


@api_bp.route("/analyze/text", methods=["POST"])
def analyze_text():
    """
    Analyze transcript text only (no audio).
    
    Request:
        - transcript: Call transcript text
        
    Response:
        - scam analysis results
    """
    data = request.get_json()
    if not data or "transcript" not in data:
        return jsonify({"error": "No transcript provided"}), 400
    
    transcript = data["transcript"]
    deepfake_score = data.get("deepfake_score", 0.5)
    
    result = scam_analyzer.analyze_content_sync(
        transcript,
        deepfake_score,
        []
    )
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "is_scam": result.is_scam,
        "confidence": result.confidence,
        "scam_type": result.scam_type.value,
        "claimed_identity": result.claimed_identity,
        "amount_requested": result.amount_requested,
        "urgency": result.urgency_level.value,
        "red_flags": result.red_flags,
        "recommendation": result.recommendation.value
    })


@api_bp.route("/analyze/pipeline", methods=["POST"])
def analyze_pipeline():
    """
    🎯 FULL HYBRID PIPELINE ANALYSIS
    
    Three-stage detection:
    1. Stage 1: Quick WavLM screening (fast, catches obvious fakes)
    2. Stage 2: Deep Gemini audio analysis (if Stage 1 suspicious)
    3. Stage 3: Content/scam analysis with Gemini
    
    Request:
        - audio: Audio file (WAV, MP3)
        - transcript: Optional transcript for Stage 3
        
    Response:
        - Complete multi-stage analysis with verdict and recommendations
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files["audio"]
    transcript = request.form.get("transcript", "")
    
    # Save audio temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        audio_path = tmp.name
    
    try:
        # Run hybrid analysis (WavLM + Gemini)
        analysis, metadata = hybrid_detector.analyze_sync(audio_path)
        
        # Also run scam analysis if transcript provided
        scam_result = None
        if transcript:
            scam_result = scam_analyzer.analyze_content_sync(
                transcript, analysis.deepfake_score, analysis.artifacts_detected
            )
        
        # Build response
        result = {
            "stages": {
                "stage1": {
                    "name": "WavLM Deepfake Detection",
                    "deepfake_score": analysis.deepfake_score,
                    "confidence": analysis.confidence,
                    "artifacts_detected": analysis.artifacts_detected,
                    "explanation": analysis.explanation
                },
                "stage2": {
                    "name": "Gemini Audio Analysis",
                    "status": metadata.get("gemini_used", False),
                    "mode": metadata.get("mode", "unknown")
                }
            },
            "deepfake": {
                "score": analysis.deepfake_score,
                "is_fake": analysis.deepfake_score > 0.7,
                "confidence": analysis.confidence
            },
            "metadata": metadata
        }
        
        # Add scam analysis if available
        if scam_result:
            result["stages"]["stage3"] = {
                "name": "Scam Content Analysis",
                "is_scam": scam_result.is_scam,
                "scam_type": scam_result.scam_type.value,
                "confidence": scam_result.confidence,
                "red_flags": scam_result.red_flags
            }
            result["scam"] = {
                "is_scam": scam_result.is_scam,
                "scam_type": scam_result.scam_type.value,
                "confidence": scam_result.confidence,
                "red_flags": scam_result.red_flags,
                "recommendation": scam_result.recommendation.value
            }
        
        # Determine overall verdict
        is_dangerous = analysis.deepfake_score > 0.7 or (scam_result and scam_result.is_scam)
        result["verdict"] = "high" if is_dangerous else "safe" if analysis.deepfake_score < 0.3 else "medium"
        result["recommendation"] = "HANG UP - Possible scam detected!" if is_dangerous else "Call appears safe"
        result["confidence"] = analysis.confidence
        
        return jsonify(result)
        
    finally:
        # Clean up temp file
        if os.path.exists(audio_path):
            os.unlink(audio_path)


@api_bp.route("/analyze/complete", methods=["POST"])
def analyze_complete():
    """
    🛡️ COMPLETE 5-LAYER DEFENSE ANALYSIS
    
    Layers:
    1. Audio Deepfake Detection (WavLM + Gemini)
    2. Scam Content Analysis (Gemini Pro)
    3. Caller Verification (phone number check)
    4. Behavioral Analysis (manipulation detection)
    5. Voice Cloning Protection (if family claim)
    
    Request (JSON or multipart):
        - audio: Audio file (optional for demo)
        - transcript: Call transcript (required)
        - caller_number: Phone number displayed
        - claimed_identity: Who they claim to be
        - claimed_organization: LHDN, police, bank, etc.
        - call_duration: How long call has been active (seconds)
        
    Response:
        - Complete threat analysis with all 5 layers
        - Threat level: SAFE/LOW/MEDIUM/HIGH/CRITICAL
        - Recommendation and explanation
    """
    import asyncio
    from app.services.complete_vericall_implementation import (
        VeriCallDefenseSystem,
        BehaviorAnalyzer,
        CallerVerifier
    )
    
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    transcript = data.get("transcript", "")
    caller_number = data.get("caller_number", "+60123456789")
    claimed_identity = data.get("claimed_identity")
    claimed_organization = data.get("claimed_organization")
    call_duration = float(data.get("call_duration", 30))
    
    if not transcript:
        return jsonify({"error": "Transcript is required"}), 400
    
    audio_path = None
    
    # Handle audio file if provided
    if "audio" in request.files:
        audio_file = request.files["audio"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            audio_file.save(tmp.name)
            audio_path = tmp.name
    
    try:
        # Initialize defense system
        defense = VeriCallDefenseSystem()
        
        if audio_path:
            # Full analysis with audio (async wrapped in sync)
            result = asyncio.run(defense.analyze_call(
                audio_path=audio_path,
                transcript=transcript,
                caller_number=caller_number,
                claimed_identity=claimed_identity,
                claimed_organization=claimed_organization,
                call_duration=call_duration
            ))
        else:
            # Text-only analysis (demo mode)
            # Layer 2: Content Analysis
            scam_result = scam_analyzer.analyze_content_sync(
                transcript, 0.5, []
            )
            
            # Layer 3: Caller Verification (async wrapped)
            verifier = CallerVerifier()
            verification = asyncio.run(verifier.verify_caller(
                caller_number,
                claimed_identity or "Unknown",
                claimed_organization
            ))
            
            # Layer 4: Behavioral Analysis
            behavior_analyzer = BehaviorAnalyzer()
            behavior = behavior_analyzer.analyze_behavior(transcript, call_duration)
            
            # Calculate threat level (simplified for demo)
            threat_score = 0
            if scam_result.is_scam:
                threat_score += 3
            if not verification["number_verified"]:
                threat_score += 2
            if behavior["suspicious_behavior"]:
                threat_score += 2
            
            threat_levels = ["safe", "low", "medium", "high", "critical"]
            threat_level = threat_levels[min(threat_score // 2, 4)]
            
            result = {
                "layers": {
                    "layer1_audio": {
                        "status": "skipped",
                        "reason": "No audio provided (demo mode)"
                    },
                    "layer2_content": {
                        "is_scam": scam_result.is_scam,
                        "scam_type": scam_result.scam_type.value,
                        "confidence": scam_result.confidence,
                        "red_flags": scam_result.red_flags
                    },
                    "layer3_verification": {
                        "number_verified": verification["number_verified"],
                        "is_spoofed": verification.get("is_spoofed", False),
                        "official_numbers": verification.get("official_numbers", []),
                        "warnings": verification.get("warnings", [])
                    },
                    "layer4_behavior": {
                        "suspicious": behavior["suspicious_behavior"],
                        "red_flags": behavior["red_flags"],
                        "manipulation_tactics": behavior["manipulation_tactics"],
                        "voice_capture_attempt": "VOICE CAPTURE" in str(behavior["red_flags"])
                    },
                    "layer5_cloning": {
                        "status": "skipped",
                        "reason": "No audio for voice verification"
                    }
                },
                "threat_level": threat_level,
                "confidence": scam_result.confidence,
                "recommendation": _get_recommendation(threat_level),
                "explanation": _generate_explanation(
                    scam_result, verification, behavior
                )
            }
        
        return jsonify(result)
        
    finally:
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)


def _get_recommendation(threat_level: str) -> str:
    """Get action recommendation based on threat level"""
    recommendations = {
        "critical": "🚨 HANG UP IMMEDIATELY and report to 997",
        "high": "⚠️ DO NOT provide any information. Verify by calling official number.",
        "medium": "⚡ Be cautious. Ask verification questions before proceeding.",
        "low": "👀 Verify caller identity before sharing information.",
        "safe": "✅ Call appears safe, but stay vigilant."
    }
    return recommendations.get(threat_level, "Proceed with caution")


def _generate_explanation(scam_result, verification, behavior) -> str:
    """Generate human-readable explanation"""
    reasons = []
    if scam_result.is_scam:
        reasons.append(f"Scam pattern detected: {scam_result.scam_type.value}")
    if not verification["number_verified"]:
        reasons.append("Caller identity not verified")
    if verification.get("warnings"):
        reasons.append(verification["warnings"][0])
    if behavior["red_flags"]:
        reasons.append(f"Red flags: {', '.join(behavior['red_flags'][:2])}")
    
    return " • ".join(reasons) if reasons else "No immediate threats detected."


# ══════════════════════════════════════════════════════════════════
# REAL-TIME GROUNDING & INTELLIGENCE ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/analyze/ground", methods=["POST"])
def analyze_ground():
    """
    Real-time scam verification using Gemini Grounding with Google Search.

    Searches Google to fact-check the caller's specific claims as they speak.
    No hardcoded rules needed -- the system checks the actual web for matching
    scam reports.

    Request (JSON):
        - transcript: Transcript chunk to verify
        - claimed_org: Optional organization the caller claims to be from

    Response:
        - Grounding verification results with source URLs
    """
    data = request.get_json()
    if not data or "transcript" not in data:
        return jsonify({"error": "transcript required"}), 400

    transcript = data["transcript"]
    claimed_org = data.get("claimed_org")

    try:
        result = scam_grounding.verify_caller_claims(
            transcript_chunk=transcript,
            caller_claimed_org=claimed_org,
        )
        result["timestamp"] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": f"Grounding verification failed: {e}",
            "is_verified": False,
            "risk_assessment": "unknown",
        }), 500


@api_bp.route("/analyze/think", methods=["POST"])
def analyze_think():
    """
    Deep analysis using Gemini extended thinking for ambiguous cases.

    Uses extended reasoning for calls that don't clearly match known patterns.
    The model internally reasons through multiple hypotheses before classifying.

    Request (JSON):
        - transcript: Call transcript
        - deepfake_score: Optional deepfake score (0-1)
        - artifacts: Optional list of detected artifacts

    Response:
        - Deep analysis with reasoning chain and novel elements
    """
    data = request.get_json()
    if not data or "transcript" not in data:
        return jsonify({"error": "transcript required"}), 400

    transcript = data["transcript"]
    deepfake_score = float(data.get("deepfake_score", 0.0))
    artifacts = data.get("artifacts", [])

    try:
        result = pattern_learner.analyze_with_thinking(
            transcript=transcript,
            deepfake_score=deepfake_score,
            artifacts_detected=artifacts,
        )
        result["timestamp"] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": f"Thinking analysis failed: {e}",
            "is_scam": False,
            "thinking_depth": "error",
        }), 500


@api_bp.route("/analyze/extract-pattern", methods=["POST"])
def extract_pattern():
    """
    Extract structured scam pattern from a user report.
    Each report makes the system smarter without ML retraining.

    Request (JSON):
        - transcript: Call transcript
        - audio_analysis: Optional dict with deepfake_score, artifacts, etc.

    Response:
        - Structured scam pattern (type, language, tactics, etc.)
    """
    data = request.get_json()
    if not data or "transcript" not in data:
        return jsonify({"error": "transcript required"}), 400

    transcript = data["transcript"]
    audio_analysis = data.get("audio_analysis")

    try:
        pattern = pattern_learner.extract_pattern_from_report(
            transcript=transcript,
            audio_analysis=audio_analysis,
        )

        # Optionally save to Firebase for accumulation
        if firebase_service.is_available:
            try:
                firebase_service.track_scam_pattern(
                    pattern.get("scam_type", "unknown"),
                    pattern.get("key_phrases", []),
                )
            except Exception:
                pass

        pattern["timestamp"] = datetime.now().isoformat()
        return jsonify(pattern)
    except Exception as e:
        return jsonify({
            "error": f"Pattern extraction failed: {e}",
            "scam_type": "unknown",
        }), 500


@api_bp.route("/intelligence/daily", methods=["GET"])
def daily_intelligence():
    """
    Fetch latest scam intelligence from Google Search via Grounding.
    This powers the self-learning system -- no retraining needed.

    Query params:
        - region: Region to search (default: Malaysia)

    Response:
        - Latest scam patterns, government advisories, trending types
    """
    region = request.args.get("region", "Malaysia")

    try:
        result = scam_grounding.fetch_latest_scam_patterns(region=region)
        result["timestamp"] = datetime.now().isoformat()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "error": f"Daily intelligence fetch failed: {e}",
            "new_patterns": [],
        }), 500


# ══════════════════════════════════════════════════════════════════
# UNCLE AH HOCK DECOY ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/decoy/start", methods=["POST"])
def start_decoy():
    """
    Start a new Uncle Ah Hock decoy session.
    
    Response:
        - session_id: ID for the decoy session
        - greeting: Uncle's opening line
    """
    session_id = uncle_ah_hock.start_session()
    
    # Generate opening line
    greeting = uncle_ah_hock.generate_response(
        session_id,
        "[CALL CONNECTED]"
    )
    
    return jsonify({
        "session_id": session_id,
        "greeting": greeting,
        "message": "🎭 Uncle Ah Hock activated! Ready to waste scammer's time."
    })


@api_bp.route("/decoy/respond", methods=["POST"])
def decoy_respond():
    """
    Get Uncle Ah Hock's response to scammer.
    
    Request:
        - session_id: Active session ID
        - scammer_text: What the scammer just said
        
    Response:
        - response: Uncle's response
        - stats: Session statistics
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    session_id = data.get("session_id")
    scammer_text = data.get("scammer_text", "")
    
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400
    
    response = uncle_ah_hock.generate_response(session_id, scammer_text)
    stats = uncle_ah_hock.get_session_stats(session_id)
    
    return jsonify({
        "response": response,
        "stats": stats
    })


@api_bp.route("/decoy/end", methods=["POST"])
def end_decoy():
    """
    End a decoy session and get final stats.
    
    Request:
        - session_id: Session to end
        
    Response:
        - final statistics and conversation log
    """
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id:
        return jsonify({"error": "No session_id provided"}), 400
    
    session = uncle_ah_hock.end_session(session_id)
    
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    return jsonify({
        "session_id": session.session_id,
        "time_wasted_seconds": session.time_wasted_seconds,
        "time_wasted_formatted": f"{session.time_wasted_seconds // 60}m {session.time_wasted_seconds % 60}s",
        "exchanges": len(session.conversation_log),
        "victory": session.time_wasted_seconds >= 600,
        "conversation_log": session.conversation_log,
        "message": "🎉 Scammer defeated!" if session.time_wasted_seconds >= 600 else "Session ended"
    })


@api_bp.route("/decoy/sample", methods=["GET"])
def decoy_sample():
    """Get a sample conversation for demo purposes"""
    return jsonify({
        "sample": uncle_ah_hock.get_sample_conversation()
    })


# ══════════════════════════════════════════════════════════════════
# INTELLIGENCE ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/intelligence", methods=["GET"])
def get_intelligence():
    """
    Get latest scam intelligence for Malaysia.
    
    Query params:
        - type: Scam type filter (lhdn, police, bank, family, all)
        
    Response:
        - Latest scam reports and patterns
    """
    scam_type = request.args.get("type", "all")
    
    intel = scam_intelligence.search_recent_scams(scam_type)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "scam_type_filter": scam_type,
        "intelligence": intel
    })


@api_bp.route("/intelligence/verify", methods=["POST"])
def verify_organization():
    """
    Verify if an organization/phone number is legitimate.
    
    Request:
        - organization: Name claimed (e.g., "LHDN", "Maybank")
        - phone_number: Optional phone number to verify
        
    Response:
        - Verification result
    """
    data = request.get_json()
    if not data or "organization" not in data:
        return jsonify({"error": "No organization provided"}), 400
    
    result = scam_intelligence.verify_organization(
        data["organization"],
        data.get("phone_number")
    )
    
    return jsonify(result)


@api_bp.route("/intelligence/alerts", methods=["GET"])
def get_intelligence_alerts():
    """
    Get community scam alerts for an area.
    
    Query params:
        - location: Area filter (default: Malaysia)
    """
    location = request.args.get("location", "Malaysia")
    
    alerts = scam_intelligence.get_community_alerts(location)
    
    return jsonify({
        "location": location,
        "alerts": alerts,
        "count": len(alerts)
    })


# ══════════════════════════════════════════════════════════════════
# FAMILY PROTECTION ENDPOINTS (Firebase)
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/family/alert", methods=["POST"])
def send_family_alert():
    """
    Send alert to family members when scam detected.
    Uses Firebase Cloud Messaging (FCM).
    
    Request:
        - protected_user_id: ID of user receiving scam call
        - scam_type: Type of scam detected
        - risk_level: urgency level
        
    Response:
        - Confirmation of alerts sent
    """
    data = request.get_json()
    
    if not data or "protected_user_id" not in data:
        return jsonify({"error": "protected_user_id required"}), 400
    
    # Use Firebase to send real alerts
    result = firebase_service.send_family_alert(
        protected_user_id=data.get("protected_user_id"),
        scam_type=data.get("scam_type", "unknown"),
        risk_level=data.get("risk_level", "medium")
    )
    
    return jsonify({
        "status": "alerts_sent" if result.get("sent", 0) > 0 else "no_recipients",
        "message": f"Notified {result.get('sent', 0)} family members",
        "details": result,
        "timestamp": datetime.now().isoformat()
    })


@api_bp.route("/family/add", methods=["POST"])
def add_family_member():
    """
    Add a family member to protection network.
    
    Request:
        - user_id: User to protect
        - family_member_id: Family member who will receive alerts
    """
    data = request.get_json()
    
    if not data or "user_id" not in data or "family_member_id" not in data:
        return jsonify({"error": "user_id and family_member_id required"}), 400
    
    success = firebase_service.add_family_member(
        data["user_id"],
        data["family_member_id"]
    )
    
    return jsonify({
        "success": success,
        "message": "Family member added" if success else "Failed to add (Firebase may not be configured)"
    })


@api_bp.route("/family/link/code", methods=["POST"])
def generate_family_link_code():
    """
    Generate one-time family link code.

    Request:
        - victim_id: UID of protected user
        - victim_name: Optional display name
    """
    data = request.get_json()
    if not data or "victim_id" not in data:
        return jsonify({"error": "victim_id required"}), 400

    if not firebase_service.is_available:
        return jsonify({
            "error": "Family linking unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    result = firebase_service.generate_family_link_code(
        victim_id=data.get("victim_id"),
        victim_name=data.get("victim_name")
    )

    if not result:
        return jsonify({
            "error": "Failed to generate link code.",
            "action": "Check Firebase connectivity and permissions."
        }), 500

    return jsonify(result)


@api_bp.route("/family/link/consume", methods=["POST"])
def consume_family_link_code():
    """
    Consume one-time family link code.

    Request:
        - code: 6-char link code
        - guardian_id: UID of family guardian
        - guardian_name: Optional display name
    """
    data = request.get_json()
    if not data or "code" not in data or "guardian_id" not in data:
        return jsonify({"error": "code and guardian_id required"}), 400

    if not firebase_service.is_available:
        return jsonify({
            "error": "Family linking unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    result = firebase_service.consume_family_link_code(
        code=data.get("code"),
        guardian_id=data.get("guardian_id"),
        guardian_name=data.get("guardian_name")
    )

    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@api_bp.route("/family/<user_id>", methods=["GET"])
def get_family_members(user_id):
    """Get all family members for a user"""
    if not firebase_service.is_available:
        return jsonify({
            "error": "Family lookup unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    family = firebase_service.get_family_members(user_id)
    
    return jsonify({
        "user_id": user_id,
        "family_members": family,
        "count": len(family)
    })


@api_bp.route("/alerts", methods=["GET"])
def get_user_alerts():
    """
    Get alerts feed for a user.

    Query:
        - user_id: UID for protected user/guardian
        - limit: max results (default 20)
    """
    user_id = request.args.get("user_id")
    limit = request.args.get("limit", 20, type=int)

    if not user_id:
        return jsonify({"error": "user_id query parameter required"}), 400

    if not firebase_service.is_available:
        return jsonify({
            "error": "Alerts unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    try:
        alerts = firebase_service.get_alerts_for_user(user_id, limit)
    except Exception as e:
        return jsonify({
            "error": f"Failed to load alerts: {e}",
            "action": "Check Firestore indexes for alerts query and backend logs."
        }), 500

    return jsonify({
        "user_id": user_id,
        "alerts": alerts,
        "count": len(alerts)
    })


# ══════════════════════════════════════════════════════════════════
# USER MANAGEMENT ENDPOINTS (Firebase)
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/users", methods=["POST"])
def create_user():
    """
    Create or update user profile.
    
    Request:
        - user_id: Unique user ID
        - name: User's name
        - phone: Phone number
        - is_protected: If user is being protected (e.g., elderly)
        - fcm_token: Firebase Cloud Messaging token
    """
    data = request.get_json()
    
    if not data or "user_id" not in data:
        return jsonify({"error": "user_id required"}), 400
    
    user_id = data.pop("user_id")
    success = firebase_service.create_user_profile(user_id, data)
    
    return jsonify({
        "success": success,
        "user_id": user_id,
        "message": "User profile created" if success else "Failed (Firebase may not be configured)"
    })


@api_bp.route("/users/<user_id>", methods=["GET"])
def get_user(user_id):
    """Get user profile"""
    user = firebase_service.get_user_profile(user_id)
    
    if user:
        return jsonify(user)
    else:
        return jsonify({"error": "User not found or Firebase not configured"}), 404


@api_bp.route("/users/<user_id>/fcm", methods=["PUT"])
def update_fcm_token(user_id):
    """Update user's FCM token for push notifications"""
    data = request.get_json()
    
    if not data or "fcm_token" not in data:
        return jsonify({"error": "fcm_token required"}), 400
    
    success = firebase_service.update_fcm_token(user_id, data["fcm_token"])
    
    return jsonify({
        "success": success,
        "message": "FCM token updated" if success else "Failed"
    })


# ══════════════════════════════════════════════════════════════════
# SCAM REPORTS ENDPOINTS (Firebase)
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/reports", methods=["POST"])
def report_scam():
    """
    Report a scam call to community database.
    
    Request:
        - user_id: Reporter's ID
        - scam_type: lhdn, police, bank, family
        - phone_number: Scammer's phone number
        - transcript: Call transcript (optional)
        - deepfake_score: Detection score
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Report data required"}), 400

    if not firebase_service.is_available:
        return jsonify({
            "error": "Report submission unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503
    
    report_id = firebase_service.report_scam(data)
    if not report_id:
        return jsonify({
            "error": "Failed to report scam.",
            "action": "Check Firebase connectivity and permissions."
        }), 500

    return jsonify({
        "success": True,
        "report_id": report_id,
        "message": "Scam reported"
    })


@api_bp.route("/reports", methods=["GET"])
def get_scam_reports():
    """Get recent scam reports from community"""
    if not firebase_service.is_available:
        return jsonify({
            "error": "Report listing unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    scam_type = request.args.get("type")
    limit = request.args.get("limit", 20, type=int)
    
    reports = firebase_service.get_recent_scams(scam_type, limit)
    
    return jsonify({
        "reports": reports,
        "count": len(reports),
        "filter": scam_type or "all"
    })


@api_bp.route("/reports/stats", methods=["GET"])
def get_scam_stats():
    """Get aggregated scam statistics"""
    if not firebase_service.is_available:
        return jsonify({
            "error": "Scam stats unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503

    stats = firebase_service.get_scam_stats()
    
    return jsonify(stats)


# ══════════════════════════════════════════════════════════════════
# EVIDENCE STORAGE ENDPOINTS (Firebase)
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/evidence", methods=["POST"])
def save_evidence():
    """
    Save detailed evidence linked to a scam report.
    
    Request:
        - report_id: ID of the scam report
        - transcript: Full conversation transcript
        - audio_url: URL to stored audio (optional)
        - evidence_hash: SHA-256 hash for integrity
        - quality_score: 0-100 evidence completeness
        - keywords_detected: List of scam keywords found
        - verification_qa: List of verification Q&A attempts
    """
    data = request.get_json()
    
    if not data or "report_id" not in data:
        return jsonify({"error": "report_id required"}), 400

    if not firebase_service.is_available:
        return jsonify({
            "error": "Evidence storage unavailable: backend Firebase is not configured.",
            "action": "Set FIREBASE_CREDENTIALS_PATH and restart backend."
        }), 503
    
    success = firebase_service.save_evidence(
        data.pop("report_id"),
        data
    )
    if not success:
        return jsonify({
            "error": "Failed to save evidence.",
            "action": "Check Firebase connectivity and permissions."
        }), 500

    return jsonify({
        "success": True,
        "message": "Evidence saved"
    })


@api_bp.route("/evidence/<report_id>", methods=["GET"])
def get_evidence(report_id):
    """Get all evidence for a scam report"""
    evidence = firebase_service.get_evidence_by_report(report_id)
    
    return jsonify({
        "report_id": report_id,
        "evidence": evidence,
        "count": len(evidence)
    })


# ══════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS (Firebase)
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/analytics/pattern", methods=["POST"])
def track_pattern():
    """
    Track scam pattern for analytics.
    
    Request:
        - pattern_type: Type of scam (macau_scam, bank_scam, etc.)
        - keywords: Keywords detected in this instance
    """
    data = request.get_json()
    
    if not data or "pattern_type" not in data:
        return jsonify({"error": "pattern_type required"}), 400
    
    success = firebase_service.track_scam_pattern(
        data.get("pattern_type"),
        data.get("keywords", [])
    )
    
    return jsonify({
        "success": success,
        "message": "Pattern tracked" if success else "Failed to track pattern"
    })


@api_bp.route("/analytics/trending", methods=["GET"])
def get_trending():
    """Get trending scam patterns"""
    limit = request.args.get("limit", 10, type=int)
    
    patterns = firebase_service.get_trending_patterns(limit)
    
    return jsonify({
        "patterns": patterns,
        "count": len(patterns)
    })


# ══════════════════════════════════════════════════════════════════
# SCAM VACCINE TRAINING ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/vaccine/start", methods=["POST"])
def vaccine_start():
    """
    Start a Scam Vaccine training session.
    AI simulates a scammer so the user can practice identifying red flags.

    Request (JSON, optional):
        - scam_type: lhdn, police, bank, parcel (random if omitted)

    Response:
        - session_id, greeting, scam_type, scam_label
    """
    data = request.get_json() or {}
    scam_type = data.get("scam_type")

    try:
        result = scam_vaccine_trainer.start_session(scam_type=scam_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Failed to start vaccine session: {e}"}), 500


@api_bp.route("/vaccine/respond", methods=["POST"])
def vaccine_respond():
    """
    Send user response during Scam Vaccine training.

    Request (JSON):
        - session_id: Active training session ID
        - user_response: What the user said to the scammer

    Response:
        - response: Scammer's next line
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    session_id = data.get("session_id")
    user_response = data.get("user_response", "")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    try:
        result = scam_vaccine_trainer.generate_response(session_id, user_response)
        if result.get("error"):
            return jsonify(result), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Vaccine response failed: {e}"}), 500


@api_bp.route("/vaccine/end", methods=["POST"])
def vaccine_end():
    """
    End a Scam Vaccine training session and get results.

    Request (JSON):
        - session_id: Session to end

    Response:
        - Stats, red flags deployed by AI, conversation log
    """
    data = request.get_json()
    session_id = (data or {}).get("session_id")

    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    result = scam_vaccine_trainer.end_session(session_id)
    if not result:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(result)


# ══════════════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@api_bp.route("/status", methods=["GET"])
def api_status():
    """Get API status and loaded models"""
    return jsonify({
        "status": "operational",
        "version": "1.0.0",
        "services": {
            "deepfake_detector": "ready",
            "scam_analyzer": "ready",
            "scam_grounding": "ready",
            "pattern_learner": "ready",
            "uncle_ah_hock": "ready",
            "scam_intelligence": "ready",
            "threat_orchestrator": "ready",
            "firebase": "ready" if firebase_service.is_available else "not_configured"
        },
        "firebase_available": firebase_service.is_available,
        "timestamp": datetime.now().isoformat()
    })


@api_bp.route("/test/notification", methods=["POST"])
def test_notification():
    """Send a test push notification"""
    data = request.get_json()
    
    if not data or "fcm_token" not in data:
        return jsonify({"error": "fcm_token required"}), 400
    
    success = firebase_service.send_test_notification(data["fcm_token"])
    
    return jsonify({
        "success": success,
        "message": "Test notification sent" if success else "Failed"
    })

