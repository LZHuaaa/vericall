"""
VeriCall Malaysia - KitaHack Demo Script
=========================================

Interactive demo showcasing all 5 defense layers.
Works WITHOUT audio files - perfect for live presentation!

Run: python demo.py
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000/api"

# ANSI colors for terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║  {Colors.BOLD}🛡️  VeriCall Malaysia - Voice Scam Defense System  🛡️{Colors.END}{Colors.CYAN}           ║
║                                                                  ║
║  Protecting Malaysians from AI voice scams                       ║
║  5-Layer Defense | Gemini AI Powered | KitaHack 2026             ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═' * 60}{Colors.END}\n")


def demo_problem_statement():
    """Act 1: Explain the problem"""
    print_section("📊 THE PROBLEM: Voice Scams in Malaysia")
    
    print(f"""
{Colors.RED}Statistics (2024-2026):{Colors.END}
  • RM 2.72 million lost to voice scams
  • 47+ cases reported weekly
  • Most vulnerable: Elderly Malaysians 60+

{Colors.YELLOW}Two Types of Attacks:{Colors.END}
  
  {Colors.BOLD}Type 1: AI Voice Cloning (30% of scams){Colors.END}
  Scammers use AI to clone voices of:
  • Government officials (LHDN, Police)
  • Bank employees
  • Family members
  
  {Colors.BOLD}Type 2: Real Human Scammers (70% of scams){Colors.END}
  Real people reading scam scripts:
  • "You have unpaid tax of RM8,000"
  • "Your IC is linked to money laundering"
  • "Your grandson is in hospital!"

{Colors.RED}⚠️  Most solutions ONLY detect AI voices - missing 70% of scams!{Colors.END}

{Colors.GREEN}✅ VeriCall detects BOTH using 5-Layer Defense!{Colors.END}
""")
    input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")


def demo_architecture():
    """Act 2: Explain the solution"""
    print_section("🏗️ THE SOLUTION: 5-Layer Defense System")
    
    print(f"""
{Colors.CYAN}
┌──────────────────────────────────────────────────────────────┐
│ INCOMING CALL                                                │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
{Colors.MAGENTA}┌──────────────────────────────────────────────────────────────┐
│ LAYER 1: Audio Deepfake Detection (WavLM + Gemini)           │
│ Catches: AI-generated voices                                 │
└────────────────────────┬─────────────────────────────────────┘{Colors.END}
                         │
                         ▼
{Colors.BLUE}┌──────────────────────────────────────────────────────────────┐
│ LAYER 2: Content Analysis (Gemini Pro)                       │
│ Catches: Scam scripts (BOTH AI and human!)                   │
└────────────────────────┬─────────────────────────────────────┘{Colors.END}
                         │
                         ▼
{Colors.YELLOW}┌──────────────────────────────────────────────────────────────┐
│ LAYER 3: Caller Verification                                 │
│ Catches: Fake caller IDs, spoofed numbers                    │
└────────────────────────┬─────────────────────────────────────┘{Colors.END}
                         │
                         ▼
{Colors.RED}┌──────────────────────────────────────────────────────────────┐
│ LAYER 4: Behavioral Analysis                                 │
│ Catches: Manipulation tactics, VOICE CAPTURE ATTEMPTS!       │
└────────────────────────┬─────────────────────────────────────┘{Colors.END}
                         │
                         ▼
{Colors.GREEN}┌──────────────────────────────────────────────────────────────┐
│ LAYER 5: Anti-Voice-Cloning Protection                       │
│ Prevents: Voice cloning, validates family members            │
└──────────────────────────────────────────────────────────────┘{Colors.END}
""")
    input(f"\n{Colors.CYAN}Press Enter to see live demo...{Colors.END}")


def demo_live_detection():
    """Act 3: Live detection demo"""
    print_section("🔴 LIVE DEMO: 5-Layer Defense in Action")
    
    scenarios = [
        {
            "name": "Scenario 1: LHDN Tax Scam (AI Voice)",
            "icon": "🚨",
            "data": {
                "transcript": "Hello, this is officer from LHDN. Your tax record shows outstanding amount of RM8,000. You must pay immediately within 2 hours or we will issue arrest warrant and send police to your house.",
                "caller_number": "+60123456789",
                "claimed_identity": "LHDN Officer Ahmad",
                "claimed_organization": "LHDN",
                "call_duration": 45
            }
        },
        {
            "name": "Scenario 2: Police Scam with Voice Capture Attempt",
            "icon": "🎤",
            "data": {
                "transcript": "This is Inspector Lee from Bukit Aman. Can you say yes to confirm your identity? Please say your full name clearly. Your IC is linked to money laundering case. Transfer RM50,000 now or we arrest you today.",
                "caller_number": "+60187654321",
                "claimed_identity": "Police Inspector",
                "claimed_organization": "PDRM",
                "call_duration": 30
            }
        },
        {
            "name": "Scenario 3: Fake Family Emergency",
            "icon": "👨‍👩‍👦",
            "data": {
                "transcript": "Ah Ma! Ah Ma! This is your grandson! I got into accident and hospital need RM15,000 deposit. Please don't tell mom and dad, just transfer to this account urgently!",
                "caller_number": "+60145678901",
                "claimed_identity": "Grandson",
                "call_duration": 25
            }
        },
        {
            "name": "Scenario 4: Legitimate Call (TM Technician)",
            "icon": "✅",
            "data": {
                "transcript": "Hi, this is Ahmad from Telekom Malaysia. I'm calling to confirm your appointment for fiber installation tomorrow at 2pm. Will you be home? We can reschedule if needed.",
                "caller_number": "1300-88-1234",
                "claimed_identity": "TM Support",
                "claimed_organization": "TM",
                "call_duration": 60
            }
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{Colors.BOLD}{scenario['icon']} {scenario['name']}{Colors.END}")
        print(f"{Colors.WHITE}Transcript: \"{scenario['data']['transcript'][:70]}...\"{Colors.END}")
        print(f"{Colors.WHITE}Caller: {scenario['data']['caller_number']}{Colors.END}")
        
        # Simulate analysis
        print(f"\n{Colors.YELLOW}Analyzing with 5-Layer Defense...{Colors.END}")
        
        for layer in range(1, 6):
            time.sleep(0.3)
            layer_names = ["Audio Detection", "Content Analysis", "Caller Verification", 
                          "Behavioral Analysis", "Voice Cloning Check"]
            print(f"  ⚡ Layer {layer}: {layer_names[layer-1]}...")
        
        # Call actual API
        try:
            r = requests.post(f"{BASE_URL}/analyze/complete", json=scenario["data"])
            result = r.json()
            
            threat_level = result.get("threat_level", "unknown")
            recommendation = result.get("recommendation", "")
            explanation = result.get("explanation", "")
            
            # Color based on threat level
            if threat_level in ["critical", "high"]:
                color = Colors.RED
                emoji = "🚨"
            elif threat_level == "medium":
                color = Colors.YELLOW
                emoji = "⚠️"
            else:
                color = Colors.GREEN
                emoji = "✅"
            
            print(f"\n  {color}{Colors.BOLD}{emoji} RESULT: {threat_level.upper()}{Colors.END}")
            print(f"  {color}💡 {recommendation}{Colors.END}")
            
            # Show layer details
            layers = result.get("layers", {})
            l2 = layers.get("layer2_content", {})
            l3 = layers.get("layer3_verification", {})
            l4 = layers.get("layer4_behavior", {})
            
            if l2.get("is_scam"):
                print(f"  {Colors.RED}• Scam Pattern: {l2.get('scam_type')}{Colors.END}")
            if not l3.get("number_verified"):
                print(f"  {Colors.YELLOW}• Caller NOT verified{Colors.END}")
            if l4.get("voice_capture_attempt"):
                print(f"  {Colors.RED}• 🎤 VOICE CAPTURE ATTEMPT DETECTED!{Colors.END}")
            if l4.get("red_flags"):
                print(f"  {Colors.YELLOW}• Red flags: {', '.join(l4['red_flags'][:2])}{Colors.END}")
                
        except Exception as e:
            print(f"  {Colors.RED}API Error: {e}{Colors.END}")
            print(f"  {Colors.YELLOW}(Make sure backend is running: python -m app.main){Colors.END}")
        
        if i < len(scenarios):
            input(f"\n{Colors.CYAN}Press Enter for next scenario...{Colors.END}")


def demo_uncle_ah_hock():
    """Act 4: Uncle Ah Hock demo"""
    print_section("🎭 BONUS: Uncle Ah Hock - The AI Decoy")
    
    print(f"""
{Colors.MAGENTA}When VeriCall detects a scammer, users can deploy "Uncle Ah Hock" -
an AI personality that takes over the call to waste the scammer's time!{Colors.END}

{Colors.BOLD}Features:{Colors.END}
  • Speaks Manglish (mixed English, Malay, Hokkien)
  • Pretends to be confused/deaf
  • Goes on tangents about cats and grandchildren
  • Goal: Keep scammer busy for 10-30 minutes!

{Colors.CYAN}Every minute scammer spends with Uncle = 1 minute NOT scamming real victims!{Colors.END}
""")
    
    try_uncle = input(f"\n{Colors.CYAN}Demo Uncle Ah Hock? (y/n): {Colors.END}")
    
    if try_uncle.lower() == 'y':
        try:
            # Start session
            r = requests.post(f"{BASE_URL}/decoy/start")
            data = r.json()
            session_id = data.get("session_id")
            
            print(f"\n{Colors.GREEN}🎭 Uncle Ah Hock session started!{Colors.END}")
            print(f"{Colors.WHITE}(Session: {session_id[:8]}...){Colors.END}")
            
            scammer_lines = [
                "Hello, this is LHDN. You owe RM8000 tax!",
                "Sir! You must pay now or we arrest you!",
                "Give me your bank account number immediately!"
            ]
            
            for line in scammer_lines:
                print(f"\n{Colors.RED}Scammer: {line}{Colors.END}")
                
                r = requests.post(f"{BASE_URL}/decoy/respond", 
                    json={"session_id": session_id, "scammer_text": line})
                response = r.json().get("response", "")
                
                print(f"{Colors.GREEN}👴 Uncle: {response}{Colors.END}")
                time.sleep(1)
            
            # End session
            r = requests.post(f"{BASE_URL}/decoy/end", json={"session_id": session_id})
            stats = r.json()
            
            print(f"\n{Colors.CYAN}⏱️  Time wasted: {stats.get('time_wasted_formatted')}")
            print(f"💬 Exchanges: {stats.get('exchanges')}{Colors.END}")
            
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.END}")


def demo_conclusion():
    """Act 5: Conclusion"""
    print_section("🏆 WHY VERICALL WINS")
    
    print(f"""
{Colors.GREEN}{Colors.BOLD}What Makes VeriCall Complete:{Colors.END}

  ✅ Detects AI-generated voices (30% of scams)
  ✅ Detects REAL HUMAN scammers (70% of scams!)
  ✅ Prevents voice cloning attacks
  ✅ Verifies caller identity
  ✅ Fights back with Uncle Ah Hock!

{Colors.CYAN}{Colors.BOLD}Google Technologies Used:{Colors.END}

  🧠 Gemini 2.5 Pro - Scam content analysis
  🎵 Gemini Native Audio - Voice deepfake detection  
  🌐 Gemini Grounding - Real-time scam intelligence
  📱 Flutter - Mobile app
  🔥 Firebase - User/family data, notifications

{Colors.YELLOW}{Colors.BOLD}Perfect Timing:{Colors.END}

  📅 January 12, 2026: Malaysia banned Grok AI over deepfake abuse
  📅 January 17, 2026: We present VeriCall - the solution!

{Colors.BOLD}
"VeriCall doesn't just detect scams - we prevent them and fight back!"
{Colors.END}
""")
    print(f"{Colors.CYAN}Thank you! 🙏🇲🇾{Colors.END}\n")


def main():
    print_banner()
    
    print("Select demo mode:")
    print("1. Full presentation (all acts)")
    print("2. Quick demo (live detection only)")
    print("3. Uncle Ah Hock only")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ")
    
    if choice == "1":
        demo_problem_statement()
        demo_architecture()
        demo_live_detection()
        demo_uncle_ah_hock()
        demo_conclusion()
    elif choice == "2":
        demo_live_detection()
    elif choice == "3":
        demo_uncle_ah_hock()
    elif choice == "4":
        print("Goodbye!")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
