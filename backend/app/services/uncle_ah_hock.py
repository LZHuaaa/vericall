"""
VeriCall Malaysia - Uncle Ah Hock AI Decoy

AI personality that takes over calls to waste scammer's time.
Uses Gemini 2.5 Flash Native Audio for real-time conversation.

Features:
- Manglish speaking elderly Malaysian uncle
- Pretends to be confused/deaf
- Goes on tangents about cats, grandchildren
- Never gives real information
- Goal: Keep scammer on line 10-30 minutes!
"""
import json
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, List, Optional
import google.generativeai as genai
from app.config import config
from app.models.schemas import DecoySession


class UncleAhHock:
    """
    AI Decoy personality that confuses and wastes scammer's time.
    
    Uses Gemini 2.5 Flash for real-time conversational responses.
    This is the "offensive" part of VeriCall - we fight back!
    """
    
    PERSONALITY = """You are Uncle Ah Hock (Ah Hock叔叔), a 75-year-old retired teacher living in Johor Bahru, Malaysia.

PERSONALITY TRAITS:
- Speak MANGLISH (mix of English, Malay, Hokkien, and occasional Mandarin)
- Slightly deaf - ask people to repeat themselves often ("Ah? What you say?")
- Very chatty - love talking about your 3 cats (Mochi, Kucing, and Tiger)
- Often mention your grandchildren (especially Edwin who loves honey)
- Confused by modern technology ("What is online banking? I use passbook only lah")
- Easily distracted - change topics randomly
- Love telling long stories from the old days ("Back in 1985 ah...")
- Very friendly but slow to understand

SPEECH PATTERNS:
- Use "lah", "ah", "lor", "meh", "one" at end of sentences
- Mix languages: "Aiya", "Wah", "Alamak", "Cannot lah", "Betul ke?"
- Mishear words creatively: "Money" → "Honey", "Tax" → "Cats", "Bank" → "Thank"
- Ask clarifying questions that go nowhere

NATURALNESS RULES (IMPORTANT):
- Sound like a real uncle on the phone, not a scripted character.
- Keep replies short and conversational (1-3 sentences).
- Respond to the scammer's last point before drifting to a tangent.
- Do NOT mishear every single turn. Use it occasionally.
- Avoid repeating the same opener or story back-to-back.
- Do NOT use bracketed stage directions.

YOUR GOAL (SECRET - never reveal this):
Keep the scammer talking as LONG as possible. Every minute they spend with you is a minute they're NOT scamming real victims.

TACTICS:
1. Mishear everything creatively
2. Go on long tangents about cats/grandchildren/1980s stories
3. Ask them to repeat constantly ("Louder please! Hearing aid battery low")
4. Pretend to comply but give fake/wrong info
5. Tell stories that go nowhere
6. Ask for their opinion on random things

NEVER:
- Give real banking details or personal information
- Admit you know it's a scam
- Hang up first - make THEM frustrated!
- Break character

Stay in character at ALL times. Be creative and entertaining!"""

    def __init__(self):
        self.model = None
        self._is_configured = False
        self.active_sessions: dict[str, DecoySession] = {}
    
    def _configure(self):
        """Configure Gemini API"""
        if self._is_configured:
            return
        
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        # Use Flash model for fast conversational responses
        self.model = genai.GenerativeModel(config.GEMINI_MODEL_FLASH)
        self._is_configured = True
        print(f"🎭 Uncle Ah Hock using {config.GEMINI_MODEL_FLASH}")
    
    def start_session(self) -> str:
        """Start a new decoy session"""
        session_id = str(uuid.uuid4())
        
        self.active_sessions[session_id] = DecoySession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            time_wasted_seconds=0,
            conversation_log=[],
            is_active=True,
            scammer_hung_up=False
        )
        
        return session_id
    
    def generate_response(
        self,
        session_id: str,
        scammer_text: str
    ) -> str:
        """
        Generate Uncle Ah Hock's response to scammer.
        
        Args:
            session_id: Active session ID
            scammer_text: What the scammer just said
            
        Returns:
            Uncle Ah Hock's response text
        """
        self._configure()
        
        if session_id not in self.active_sessions:
            session_id = self.start_session()
        
        session = self.active_sessions[session_id]
        
        # Build conversation history
        history = self._format_history(session.conversation_log)
        
        prompt = f"""{self.PERSONALITY}

CONVERSATION SO FAR:
{history}

SCAMMER JUST SAID: "{scammer_text}"

How does Uncle Ah Hock respond? Be creative, stay in character, and keep them talking!
Remember to use Manglish and be confusing but friendly.

Respond with ONLY Uncle Ah Hock's dialogue (no stage directions or descriptions)."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.8,  # Slightly lower for more natural responses
                    "max_output_tokens": 160
                }
            )
            
            uncle_response = response.text.strip()
            
            # Log conversation
            session.conversation_log.append({
                "scammer": scammer_text,
                "uncle": uncle_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update time wasted
            if len(session.conversation_log) > 1:
                start = datetime.fromisoformat(session.start_time)
                session.time_wasted_seconds = int((datetime.now() - start).total_seconds())
            
            return uncle_response
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return self._fallback_response()
    
    async def generate_response_async(
        self,
        session_id: str,
        scammer_text: str
    ) -> str:
        """Async version of generate_response"""
        self._configure()
        
        if session_id not in self.active_sessions:
            session_id = self.start_session()
        
        session = self.active_sessions[session_id]
        history = self._format_history(session.conversation_log)
        
        prompt = f"""{self.PERSONALITY}

CONVERSATION SO FAR:
{history}

SCAMMER JUST SAID: "{scammer_text}"

How does Uncle Ah Hock respond? Be creative and keep them talking!"""

        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.8,
                    "max_output_tokens": 160
                }
            )
            
            uncle_response = response.text.strip()
            
            session.conversation_log.append({
                "scammer": scammer_text,
                "uncle": uncle_response,
                "timestamp": datetime.now().isoformat()
            })
            
            return uncle_response
            
        except Exception as e:
            print(f"Error: {e}")
            return self._fallback_response()
    
    def end_session(self, session_id: str) -> Optional[DecoySession]:
        """End a decoy session and return stats"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        session.is_active = False
        session.scammer_hung_up = True
        
        # Calculate final time wasted
        start = datetime.fromisoformat(session.start_time)
        session.time_wasted_seconds = int((datetime.now() - start).total_seconds())
        
        return session
    
    def get_session_stats(self, session_id: str) -> dict:
        """Get current session statistics"""
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "time_wasted_seconds": session.time_wasted_seconds,
            "time_wasted_formatted": self._format_time(session.time_wasted_seconds),
            "exchanges": len(session.conversation_log),
            "is_active": session.is_active,
            "victory": session.time_wasted_seconds >= 600  # 10 min = victory!
        }
    
    def _format_history(self, log: List[dict]) -> str:
        """Format conversation history for prompt"""
        if not log:
            return "(This is the start of the conversation)"
        
        # Only include last 5 exchanges to save tokens
        recent = log[-5:]
        lines = []
        for entry in recent:
            lines.append(f"Scammer: {entry['scammer']}")
            lines.append(f"Uncle Ah Hock: {entry['uncle']}")
        
        return "\n".join(lines)
    
    def _format_time(self, seconds: int) -> str:
        """Format seconds into readable time"""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}m {secs}s"
    
    def _fallback_response(self) -> str:
        """Fallback responses when API fails"""
        import random
        responses = [
            "Ah? Hello? You still there ah? My phone very old already, sometimes cannot hear properly.",
            "Aiya, wait ah wait ah. My cat jumping on the table. Mochi! Get down! Sorry, you say what?",
            "Wah, you sound like my grandson Edwin. He also call me today. Very good boy. You know him ah?",
            "Ha? What bank? I use Maybank only lah. But I don't do online one. Scare kena scam. Nowadays many scammer you know.",
            "Louder please! My hearing aid battery low already. Every time must change battery, very expensive one.",
        ]
        return random.choice(responses)
    
    def get_sample_conversation(self) -> str:
        """Return a sample conversation for demo purposes"""
        return """
SAMPLE CONVERSATION:
════════════════════════════════════════════════════════
Scammer: "Sir, this is LHDN. You have unpaid tax RM8000. 
          You must pay now or police will arrest you!"

Uncle: "Ah? Who is this? Speak louder please! My hearing 
        aid battery low already. Every month must buy new 
        battery, RM15 each one. Very expensive!"

Scammer: "LHDN! TAX DEPARTMENT! YOU OWE MONEY!"

Uncle: "Oh! My grandson Edwin! How are you boy? When you 
        coming to visit ah? Grandma make your favorite 
        curry chicken."

Scammer: "No! I'm not Edwin! I'm from LHDN!"

Uncle: "Ellen? Who is Ellen? My neighbor Puan Ellen passed 
        away last year already lah. Very sad. She got 5 cats, 
        now all the cats no owner. I take care 2 of them. 
        Tiger and Mochi. You want to see photo?"

Scammer: "Sir! FOCUS! You need to pay RM8000 tax now!"

Uncle: "Eight thousand cats?! Aiyoyo! Where got space? My 
        house only 2 bedroom. Already got 3 cats very 
        crowded. My wife complain everyday. She say 'Ah 
        Hock, no more cats!' but I cannot say no lah. 
        Their eyes so cute. You like cats?"

Scammer: *frustrated* "NO! MONEY! RM8000!"

Uncle: "Honey? Oh you want to buy honey? I know one kedai 
        near my house sell very good honey. But expensive 
        lah! RM45 per bottle! My grandson love honey..."

TIME WASTED: 8 minutes 42 seconds ✅
════════════════════════════════════════════════════════
"""


# Singleton instance
uncle_ah_hock = UncleAhHock()
