"""
VeriCall Malaysia - Data Schemas
"""
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ScamType(Enum):
    """Types of scams detected in Malaysia"""
    LHDN = "lhdn"           # Tax department impersonation
    POLICE = "police"        # Police/court threats
    BANK = "bank"            # Bank fraud
    FAMILY = "family"        # Family emergency scams
    VOICE_HARVESTING = "voice_harvesting"  # Silent call / voice cloning
    INVESTMENT = "investment"  # Crypto/forex/Macau scams
    COURIER = "courier"      # PosLaju/J&T parcel scams
    LOVE = "love"            # Romance/love scams
    UNKNOWN = "unknown"


class UrgencyLevel(Enum):
    """Urgency levels for scam detection"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedAction(Enum):
    """Recommended actions after detection"""
    HANG_UP = "hang_up"
    VERIFY = "verify"
    DEPLOY_DECOY = "deploy_decoy"
    REPORT_997 = "report_997"


@dataclass
class DeepfakeAnalysis:
    """Enhanced result from audio deepfake detection with quality metrics"""
    deepfake_score: float           # 0-1 (higher = more likely synthetic)
    confidence: float               # 0-1 (confidence in the score)
    artifacts_detected: List[str]   # List of detected artifacts
    explanation: str                # Human-readable explanation
    
    # Enhanced fields
    is_deepfake: bool = False       # Whether the audio is determined to be a deepfake
    certainty: str = "medium"       # Certainty level: high, medium, low, very_low
    quality_info: Optional[dict] = None    # Audio quality metrics
    method_scores: Optional[dict] = None   # Individual scores from each detection method


@dataclass
class ScamAnalysis:
    """Result from scam content analysis"""
    is_scam: bool
    confidence: float
    scam_type: ScamType
    claimed_identity: Optional[str]
    amount_requested: Optional[str]
    urgency_level: UrgencyLevel
    red_flags: List[str]
    recommendation: RecommendedAction


@dataclass
class CallAnalysisResult:
    """Combined result from full call analysis"""
    deepfake: DeepfakeAnalysis
    scam: ScamAnalysis
    transcript: str
    timestamp: str
    should_alert: bool
    alert_message: Optional[str]


@dataclass
class CombinedAnalysis:
    """Combined deepfake + scam analysis with action flags"""
    deepfake_analysis: DeepfakeAnalysis
    scam_analysis: ScamAnalysis
    overall_risk_score: float       # 0-1 combined risk score
    should_alert_user: bool         # Should show alert to user
    should_deploy_uncle: bool       # Should deploy Uncle Ah Hock
    alert_message: str              # User-friendly alert message


@dataclass
class DecoySession:
    """Active decoy session info"""
    session_id: str
    start_time: str
    time_wasted_seconds: int
    conversation_log: List[dict]
    is_active: bool
    scammer_hung_up: bool


@dataclass
class FamilyAlert:
    """Alert sent to family members"""
    alert_id: str
    protected_user_id: str
    protected_user_name: str
    scam_type: ScamType
    risk_level: UrgencyLevel
    timestamp: str
    location: Optional[str]
    actions_available: List[str]
