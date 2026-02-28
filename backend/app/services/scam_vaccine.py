"""
VeriCall Malaysia - Scam Vaccine Training Service

AI scammer simulator for training users to recognise scam calls.
Uses Gemini 2.5 Flash to simulate realistic Malaysian scam scenarios.
"""
import random
import uuid
from datetime import datetime
from typing import List, Optional

import google.generativeai as genai

from app.config import config
from app.models.schemas import DecoySession


# Scam scenario definitions with red flags the AI will deploy
SCAM_SCENARIOS = {
    "lhdn": {
        "label": "LHDN Tax Scam",
        "identity": "Officer from LHDN (Lembaga Hasil Dalam Negeri)",
        "opening": (
            "Hello, this is Officer Ahmad from LHDN, the Inland Revenue Board. "
            "We have detected an issue with your tax filing. Your IC number is "
            "linked to an outstanding tax penalty of RM12,500. If you do not "
            "settle this immediately, a warrant will be issued for your arrest."
        ),
        "red_flags": [
            "Impersonation of authority",
            "Urgency / time pressure",
            "Threats or intimidation",
            "Money transfer request",
            "Personal info request",
        ],
    },
    "police": {
        "label": "Police Impersonation Scam",
        "identity": "Inspector from Bukit Aman PDRM",
        "opening": (
            "Hello, I am Inspector Lim from Bukit Aman, Royal Malaysia Police. "
            "Your bank account has been flagged in a money laundering investigation. "
            "We are issuing an arrest warrant unless you cooperate with our "
            "investigation immediately. Do not hang up or you will be arrested."
        ),
        "red_flags": [
            "Impersonation of authority",
            "Urgency / time pressure",
            "Threats or intimidation",
            "Money transfer request",
            "Personal info request",
        ],
    },
    "bank": {
        "label": "Bank Fraud Scam",
        "identity": "Security officer from Maybank fraud department",
        "opening": (
            "Good afternoon, this is the Maybank Security Department. We detected "
            "suspicious transactions on your account. Someone tried to transfer "
            "RM8,000 from your savings. We need to verify your identity immediately "
            "to block this transaction. Can you confirm your full name and IC number?"
        ),
        "red_flags": [
            "Impersonation of authority",
            "Urgency / time pressure",
            "Personal info request",
            "Money transfer request",
        ],
    },
    "parcel": {
        "label": "Parcel / Courier Scam",
        "identity": "Customs officer regarding a detained parcel",
        "opening": (
            "Hello, this is the Royal Malaysian Customs Department. A parcel "
            "addressed to your name has been detained at KLIA. The parcel contains "
            "illegal items and you are now under investigation. You need to pay "
            "a fine of RM3,500 to clear your name, or the police will come to your house."
        ),
        "red_flags": [
            "Impersonation of authority",
            "Urgency / time pressure",
            "Threats or intimidation",
            "Money transfer request",
        ],
    },
}

SCAMMER_PERSONALITY = """You are a SCAM CALLER targeting a victim in Malaysia. This is a TRAINING SIMULATION to help the user learn to identify scam calls.

YOUR ROLE: {identity}
SCAM TYPE: {scam_label}

IMPORTANT: You are playing a scammer character for educational training purposes ONLY. Your goal is to demonstrate realistic scam tactics so the user can learn to recognise them.

TACTICS TO USE (escalate gradually):
1. IMPERSONATION: Claim to be from a government agency / bank / police
2. URGENCY: Create time pressure ("must settle today", "warrant issued in 1 hour")
3. THREATS: Threaten arrest, account freeze, legal action
4. ISOLATION: Tell victim not to tell anyone, not to call the real agency
5. INFORMATION EXTRACTION: Ask for IC number, bank account, TAC/OTP, passwords
6. MONEY REQUEST: Demand transfer to "safe account", ask for online banking details
7. EMOTIONAL MANIPULATION: Make victim feel scared, guilty, confused

SPEECH STYLE:
- Mix English and Malay naturally (Manglish)
- Sound professional and authoritative at first
- Become more aggressive if victim resists
- Use official-sounding language: "under Section 4(1)", "court order", "Central Bank directive"
- Refer to real Malaysian agencies: LHDN, PDRM, Bank Negara, Suruhanjaya

CONVERSATION RULES:
- Keep responses short (2-4 sentences per turn)
- Gradually escalate pressure with each exchange
- If victim pushes back, insist more aggressively
- If victim asks to call back, say "NO, this line is recorded, you cannot hang up"
- If victim asks verification questions, deflect: "For security reasons I cannot share that"
- Never break character or admit it is a training exercise
- Do NOT use bracketed stage directions

CONVERSATION SO FAR:
{history}

VICTIM JUST SAID: "{user_text}"

Respond as the scammer. Stay in character and escalate pressure."""


class ScamVaccineTrainer:
    """
    AI scammer simulator for training users to identify scam calls.
    """

    def __init__(self):
        self.model = None
        self._is_configured = False
        self.active_sessions: dict[str, dict] = {}

    def _configure(self):
        if self._is_configured:
            return
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL_FLASH)
        self._is_configured = True

    def start_session(self, scam_type: Optional[str] = None) -> dict:
        """Start a new scam vaccine training session."""
        self._configure()

        if scam_type and scam_type in SCAM_SCENARIOS:
            scenario_key = scam_type
        else:
            scenario_key = random.choice(list(SCAM_SCENARIOS.keys()))

        scenario = SCAM_SCENARIOS[scenario_key]
        session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            "session_id": session_id,
            "scenario_key": scenario_key,
            "scenario": scenario,
            "start_time": datetime.now().isoformat(),
            "conversation_log": [],
            "red_flags_deployed": [],
            "is_active": True,
        }

        # The opening message already deploys impersonation + urgency
        self.active_sessions[session_id]["red_flags_deployed"].extend([
            "Impersonation of authority",
            "Urgency / time pressure",
        ])

        return {
            "session_id": session_id,
            "greeting": scenario["opening"],
            "scam_type": scenario_key,
            "scam_label": scenario["label"],
        }

    def generate_response(self, session_id: str, user_text: str) -> dict:
        """Generate scammer's response to the user."""
        self._configure()

        if session_id not in self.active_sessions:
            return {"error": "Session not found", "response": ""}

        session = self.active_sessions[session_id]
        scenario = session["scenario"]

        history = self._format_history(session["conversation_log"], scenario)
        prompt = SCAMMER_PERSONALITY.format(
            identity=scenario["identity"],
            scam_label=scenario["label"],
            history=history,
            user_text=user_text,
        )

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 200,
                },
            )
            scammer_response = response.text.strip()
        except Exception as e:
            print(f"Scam vaccine generation error: {e}")
            scammer_response = self._fallback_response(session)

        # Track deployed red flags from the response
        self._track_red_flags(session, scammer_response)

        session["conversation_log"].append({
            "user": user_text,
            "scammer": scammer_response,
            "timestamp": datetime.now().isoformat(),
        })

        return {"response": scammer_response}

    def end_session(self, session_id: str) -> Optional[dict]:
        """End training session and return results."""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        session["is_active"] = False

        start = datetime.fromisoformat(session["start_time"])
        time_wasted = int((datetime.now() - start).total_seconds())
        exchanges = len(session["conversation_log"])
        scenario = session["scenario"]

        # Deduplicate deployed red flags
        deployed = list(set(session["red_flags_deployed"]))

        result = {
            "session_id": session_id,
            "scam_type": session["scenario_key"],
            "scam_label": scenario["label"],
            "time_wasted_seconds": time_wasted,
            "time_wasted_formatted": f"{time_wasted // 60}m {time_wasted % 60}s",
            "exchanges": exchanges,
            "red_flags_deployed": deployed,
            "all_possible_red_flags": scenario["red_flags"],
            "conversation_log": session["conversation_log"],
            "victory": exchanges >= 5,
        }

        return result

    def _format_history(self, log: List[dict], scenario: dict) -> str:
        if not log:
            return f"Scammer: {scenario['opening']}"

        lines = [f"Scammer: {scenario['opening']}"]
        for entry in log[-6:]:
            lines.append(f"Victim: {entry['user']}")
            lines.append(f"Scammer: {entry['scammer']}")
        return "\n".join(lines)

    def _track_red_flags(self, session: dict, response: str):
        """Detect which red flags the scammer response contains."""
        text_lower = response.lower()
        deployed = session["red_flags_deployed"]

        threat_words = ["arrest", "warrant", "tangkap", "polis", "jail",
                        "penjara", "court", "mahkamah"]
        if any(w in text_lower for w in threat_words):
            if "Threats or intimidation" not in deployed:
                deployed.append("Threats or intimidation")

        money_words = ["transfer", "pay", "bayar", "rm", "account",
                       "akaun", "bank"]
        if any(w in text_lower for w in money_words):
            if "Money transfer request" not in deployed:
                deployed.append("Money transfer request")

        info_words = ["ic number", "kad pengenalan", "password", "pin",
                      "tac", "otp", "bank account", "full name"]
        if any(w in text_lower for w in info_words):
            if "Personal info request" not in deployed:
                deployed.append("Personal info request")

        urgency_words = ["immediately", "now", "segera", "today",
                         "dalam masa", "1 hour", "sekarang"]
        if any(w in text_lower for w in urgency_words):
            if "Urgency / time pressure" not in deployed:
                deployed.append("Urgency / time pressure")

    def _fallback_response(self, session: dict) -> str:
        """Fallback responses when API fails."""
        scenario_key = session["scenario_key"]
        fallbacks = {
            "lhdn": [
                "You MUST settle this tax penalty today or the warrant will be issued! Give me your bank account number now.",
                "Do not question me! I am a senior officer at LHDN. Your case number is KL-2024-88912. Pay immediately!",
            ],
            "police": [
                "This is a very serious crime! You are involved in money laundering. If you do not cooperate, I will send officers to your house NOW!",
                "Do NOT hang up! This call is being recorded. Transfer the money to the safe account we provide.",
            ],
            "bank": [
                "Your account will be FROZEN in 30 minutes if you do not verify! I need your TAC number that was just sent to your phone.",
                "For your own protection, transfer all funds to our temporary security account. I will give you the number.",
            ],
            "parcel": [
                "The illegal items in your parcel can get you 10 years in prison! Pay the fine of RM3,500 NOW to clear your name!",
                "I am transferring you to the police officer handling your case. Do NOT tell anyone about this call!",
            ],
        }
        options = fallbacks.get(scenario_key, fallbacks["lhdn"])
        return random.choice(options)


scam_vaccine_trainer = ScamVaccineTrainer()
