"""
VeriCall Malaysia - Enhanced Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

_CONFIG_FILE = Path(__file__).resolve()
_BACKEND_DIR = _CONFIG_FILE.parent.parent
load_dotenv(_BACKEND_DIR / ".env")


def _parse_gemini_keys() -> list[str]:
    """Load Gemini keys from single-key and multi-key env vars."""
    keys: list[str] = []
    raw_single = (os.getenv("GEMINI_API_KEY", "") or "").strip()
    raw_multi = os.getenv("GEMINI_API_KEYS", "") or ""

    if raw_single:
        keys.append(raw_single)
    for item in raw_multi.split(","):
        key = item.strip()
        if key and key not in keys:
            keys.append(key)
    return keys


class Config:
    """Enhanced configuration for MyGuard.ai / VeriCall Malaysia"""
    
    # Base directory
    BASE_DIR = Path(__file__).parent.parent
    
    # Gemini AI - Multiple models for different tasks
    GEMINI_API_KEYS = _parse_gemini_keys()
    GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
    
    # Model Selection (choose best model for each task)
    GEMINI_MODEL_PRO = "gemini-2.5-pro"           # Best reasoning for scam detection
    GEMINI_MODEL_FLASH = "gemini-2.5-flash"       # Fast responses for real-time analysis
    GEMINI_MODEL_AUDIO = "gemini-2.5-flash-native-audio-latest"  # Native audio analysis!
    GEMINI_MODEL_TTS = "gemini-2.5-flash-preview-tts"   # Text-to-speech for Uncle voice
    
    # Default model (fallback)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Firebase
    FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    
    # Twilio VOIP
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # App Settings
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))
    THREAT_ENGINE_VERSION = os.getenv("THREAT_ENGINE_VERSION", "threat-v2")
    THREAT_ENGINE_V2_SHADOW = os.getenv("THREAT_ENGINE_V2_SHADOW", "true").lower() == "true"
    THREAT_ENGINE_V2_PRIMARY = os.getenv("THREAT_ENGINE_V2_PRIMARY", "false").lower() == "true"
    AUTO_HANGUP_ENABLED = os.getenv("AUTO_HANGUP_ENABLED", "true").lower() == "true"
    CALL_AUDIO_RELAY_ENABLED = os.getenv("CALL_AUDIO_RELAY_ENABLED", "false").lower() == "true"
    FCM_INCOMING_CALL_ENABLED = os.getenv("FCM_INCOMING_CALL_ENABLED", "false").lower() == "true"
    DEMO_VICTIM_USER_ID = os.getenv("DEMO_VICTIM_USER_ID", "demo_victim")
    CALL_AUDIO_WS_HOST = os.getenv("CALL_AUDIO_WS_HOST", "0.0.0.0")
    CALL_AUDIO_WS_PORT = int(os.getenv("CALL_AUDIO_WS_PORT", "8765"))
    RETRIEVAL_TIMEOUT_SECONDS = float(os.getenv("RETRIEVAL_TIMEOUT_SECONDS", "1.8"))
    THREAT_ENGINE_ALLOW_TIER2 = os.getenv("THREAT_ENGINE_ALLOW_TIER2", "true").lower() == "true"
    THREAT_LLM_MIN_INTERVAL_SECONDS = float(os.getenv("THREAT_LLM_MIN_INTERVAL_SECONDS", "12"))
    THREAT_RETRIEVAL_MIN_INTERVAL_SECONDS = float(os.getenv("THREAT_RETRIEVAL_MIN_INTERVAL_SECONDS", "30"))
    
    # Model Settings
    WAVLM_MODEL = "microsoft/wavlm-base-plus"
    CLASSIFIER_PATH = BASE_DIR / "models" / "classifier.pth"
    AUDIO_SAMPLE_RATE = 16000
    MAX_AUDIO_LENGTH = 30  # seconds
    # Optional: Comma-separated list of pretrained deepfake models (Hugging Face)
    DEEPFAKE_MODELS = [m.strip() for m in os.getenv(
        "DEEPFAKE_MODELS",
        "motheecreator/Deepfake-audio-detection"
    ).split(",") if m.strip()]
    
    # Detection Thresholds (IMPROVED - More conservative)
    DEEPFAKE_HIGH_THRESHOLD = 0.85  # 85%+ = definitely fake
    DEEPFAKE_LOW_THRESHOLD = 0.15   # 15%- = definitely real
    DEEPFAKE_THRESHOLD = 0.7        # Legacy: Above this = likely synthetic
    SCAM_THRESHOLD = 0.75           # 75%+ scam confidence to alert
    SCAM_CONFIDENCE_THRESHOLD = 0.8 # Legacy: Above this = trigger alert
    
    # Only boost scam score if VERY confident about deepfake
    DEEPFAKE_SCAM_BOOST_THRESHOLD = 0.85
    DEEPFAKE_CONFIDENCE_GATE = 0.75
    DEEPFAKE_MIN_ACTIVE_SPEECH_FOR_ALERT = 0.25
    
    # Audio quality thresholds
    MIN_AUDIO_LENGTH = 5.0          # Minimum seconds for analysis
    IDEAL_AUDIO_LENGTH = 10.0       # Ideal length for best accuracy
    MAX_SILENCE_RATIO = 0.4         # Max 40% silence
    CLIPPING_THRESHOLD = 0.95       # Audio clipping detection
    MIN_ACTIVE_SPEECH_RATIO = 0.2   # Minimum ratio of active speech frames
    
    # Malaysian Scam Patterns (Enhanced)
    SCAM_KEYWORDS = {
        "lhdn": ["LHDN", "cukai", "tax", "refund", "bayaran", "hasil", "Lembaga Hasil"],
        "police": ["Mahkamah", "polis", "court", "arrest", "tangkap", "warrant", "tribunal"],
        "bank": ["bank account", "akaun bank", "PIN", "TAC", "transfer", "maybank", "cimb"],
        "family": ["accident", "kemalangan", "hospital", "urgent", "emergency", "kecemasan", "tolong"],
        "investment": ["pelaburan", "investment", "profit", "untung", "saham", "crypto", "forex"],
        "voice_harvesting": ["can you say yes", "say your name", "boleh cakap", "tolong sebut", "can you hear me"],
        "courier": ["PosLaju", "J&T", "parcel", "bungkusan", "customs", "kastam", "delivery"],
        "love": ["sayang", "darling", "send money", "kirim wang", "lonely", "love you", "gift"],
    }
    
    # Ensemble weights (for multi-method detection)
    ENSEMBLE_WEIGHTS = {
        'pretrained': 0.5,   # Pretrained model weight
        'heuristic': 0.3,    # Spectral analysis weight
        'statistical': 0.2   # Statistical features weight
    }


config = Config()
