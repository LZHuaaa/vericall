"""
VeriCall Malaysia - Comprehensive API Test

Tests all detection features:
1. Scam text analysis
2. Deepfake audio detection (if audio file provided)
3. Uncle Ah Hock decoy
4. Full pipeline

Run: python test_api.py
"""
import requests
import json
import sys
import os

BASE_URL = os.getenv("VERICALL_API_BASE_URL", "http://localhost:5000/api")

# Windows terminals may default to cp1252; avoid UnicodeEncodeError in test logs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health():
    """Test API health"""
    print_header("1. API Health Check")
    try:
        r = requests.get(f"{BASE_URL}/status")
        data = r.json()
        print(f"Status: {data.get('status')}")
        print(f"Services: {json.dumps(data.get('services'), indent=2)}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure backend is running: python -m app.main")
        return False


def test_scam_analysis():
    """Test scam content analysis"""
    print_header("2. Scam Content Analysis (Gemini 2.5 Pro)")
    
    test_cases = [
        {
            "name": "LHDN Scam",
            "transcript": "Hello, this is officer Ahmad from LHDN. Our records show you have outstanding tax of RM8000. If you don't pay within 2 hours, we will issue arrest warrant. Please transfer to this account immediately."
        },
        {
            "name": "Police Impersonation",
            "transcript": "This is Sergeant Lee from Bukit Aman. Your IC number is linked to money laundering case. You must cooperate or we will arrest you. Transfer RM5000 to clear your name."
        },
        {
            "name": "Bank Fraud",
            "transcript": "Your Maybank account has suspicious activity. Please give me your TAC number and PIN to verify your identity. This is urgent, your account will be frozen."
        },
        {
            "name": "Family Emergency Scam",
            "transcript": "Ah Ma! This is your grandson! I got into accident and need RM3000 urgently for hospital. Please don't tell mum and dad, just transfer to this account."
        },
        {
            "name": "Legitimate Call",
            "transcript": "Hi, this is TM calling to confirm your appointment for fiber installation tomorrow at 10am. Is that time still okay for you?"
        }
    ]
    
    for case in test_cases:
        print(f"\n📞 Testing: {case['name']}")
        print(f"   Transcript: {case['transcript'][:60]}...")
        
        try:
            r = requests.post(
                f"{BASE_URL}/analyze/text",
                json={"transcript": case["transcript"]}
            )
            data = r.json()
            
            is_scam = data.get("is_scam", False)
            confidence = data.get("confidence", 0)
            scam_type = data.get("scam_type", "unknown")
            recommendation = data.get("recommendation", "unknown")
            
            if is_scam:
                print(f"   🚨 SCAM DETECTED!")
                print(f"      Type: {scam_type}")
                print(f"      Confidence: {confidence:.0%}")
                print(f"      Recommendation: {recommendation}")
                if data.get("red_flags"):
                    print(f"      Red Flags: {data['red_flags'][:3]}")
            else:
                print(f"   ✅ Likely safe (confidence: {confidence:.0%})")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


def test_uncle_ah_hock():
    """Test Uncle Ah Hock decoy"""
    print_header("3. Uncle Ah Hock Decoy (Gemini 2.5 Flash)")
    
    try:
        # Start session
        print("\n🎭 Starting decoy session...")
        r = requests.post(f"{BASE_URL}/decoy/start")
        data = r.json()
        
        session_id = data.get("session_id")
        greeting = data.get("greeting")
        
        print(f"   Session ID: {session_id[:8]}...")
        print(f"   Uncle says: {greeting}")
        
        # Test conversation
        scammer_lines = [
            "Hello! I am calling from LHDN about your tax!",
            "Sir, you owe RM8000! Pay now or police arrest you!",
            "This is serious! Give me your bank account number!"
        ]
        
        for line in scammer_lines:
            print(f"\n   Scammer: {line}")
            
            r = requests.post(
                f"{BASE_URL}/decoy/respond",
                json={"session_id": session_id, "scammer_text": line}
            )
            data = r.json()
            
            response = data.get("response", "")
            print(f"   👴 Uncle: {response[:100]}...")
        
        # End session
        r = requests.post(
            f"{BASE_URL}/decoy/end",
            json={"session_id": session_id}
        )
        data = r.json()
        
        print(f"\n   ⏱️ Time wasted: {data.get('time_wasted_formatted')}")
        print(f"   💬 Exchanges: {data.get('exchanges')}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_audio_pipeline():
    """Test full audio pipeline (requires audio file)"""
    print_header("4. Full Audio Pipeline (WavLM + Gemini)")
    
    print("\n   ⚠️ Audio testing requires a WAV/MP3 file.")
    print("   To test, use curl with your audio file:")
    print()
    print('   curl -X POST http://localhost:5000/api/analyze/pipeline \\')
    print('     -F "audio=@test_call.wav" \\')
    print('     -F "transcript=Hello this is LHDN"')
    print()
    print("   The pipeline will:")
    print("   1. Stage 1: WavLM quick screening")
    print("   2. Stage 2: Gemini Native Audio analysis")
    print("   3. Stage 3: Gemini Pro scam analysis")
    print("   4. Return verdict: CRITICAL_THREAT / SUSPICIOUS_VOICE / SCAM_CONTENT / LIKELY_SAFE")


def test_intelligence():
    """Test scam intelligence"""
    print_header("5. Scam Intelligence (Gemini Grounding)")
    
    try:
        r = requests.get(f"{BASE_URL}/intelligence")
        data = r.json()
        
        print(f"   Latest scam intel retrieved")
        intel = data.get("intelligence", {})
        if intel.get("active_scams"):
            print(f"   Active scams: {len(intel.get('active_scams', []))}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")


def test_5_layer_defense():
    """Test complete 5-layer defense system"""
    print_header("6. 🛡️ COMPLETE 5-LAYER DEFENSE (No Audio Needed!)")
    
    test_cases = [
        {
            "name": "AI Voice LHDN Scam",
            "data": {
                "transcript": "Hello, this is LHDN calling. You have unpaid tax of RM8,000. You must pay immediately or we will issue arrest warrant. Don't tell anyone about this call.",
                "caller_number": "+60123456789",
                "claimed_identity": "LHDN Officer",
                "claimed_organization": "LHDN",
                "call_duration": 30
            }
        },
        {
            "name": "Police Impersonation with Voice Capture",
            "data": {
                "transcript": "This is Inspector Ahmad from Bukit Aman. Can you say yes to confirm your identity? Your name is linked to money laundering. You must transfer RM50,000 now.",
                "caller_number": "+60187654321",
                "claimed_identity": "Police Inspector",
                "claimed_organization": "PDRM",
                "call_duration": 45
            }
        },
        {
            "name": "Fake Family Emergency",
            "data": {
                "transcript": "Mom! Mom! This is your son! I got into accident and need RM10,000 urgently. Don't tell dad! Just transfer now!",
                "caller_number": "+60145678901",
                "claimed_identity": "Son",
                "call_duration": 20
            }
        },
        {
            "name": "Legitimate TM Call",
            "data": {
                "transcript": "Hi, this is Telekom Malaysia. We're calling to confirm your fiber installation appointment for tomorrow at 2pm. Is that time still good for you?",
                "caller_number": "1300-88-1234",
                "claimed_identity": "TM Support",
                "claimed_organization": "TM",
                "call_duration": 60
            }
        }
    ]
    
    for case in test_cases:
        print(f"\n🧪 Testing: {case['name']}")
        print(f"   Transcript: {case['data']['transcript'][:50]}...")
        
        try:
            r = requests.post(
                f"{BASE_URL}/analyze/complete",
                json=case["data"]
            )
            data = r.json()
            
            threat_level = data.get("threat_level", "unknown")
            confidence = data.get("confidence", 0)
            recommendation = data.get("recommendation", "")
            explanation = data.get("explanation", "")
            
            # Show threat level with emoji
            threat_emoji = {
                "critical": "🚨",
                "high": "⚠️",
                "medium": "⚡",
                "low": "👀",
                "safe": "✅"
            }
            emoji = threat_emoji.get(threat_level, "❓")
            
            print(f"\n   {emoji} THREAT LEVEL: {threat_level.upper()}")
            print(f"   📊 Confidence: {confidence:.0%}")
            print(f"   💡 Recommendation: {recommendation}")
            print(f"   📝 Explanation: {explanation[:100]}...")
            
            # Show layer details
            layers = data.get("layers", {})
            
            # Layer 2: Content
            l2 = layers.get("layer2_content", {})
            if l2.get("is_scam"):
                print(f"   Layer 2 - Scam: {l2.get('scam_type')}")
            
            # Layer 3: Verification
            l3 = layers.get("layer3_verification", {})
            if not l3.get("number_verified"):
                print(f"   Layer 3 - ⚠️ Number NOT verified!")
                if l3.get("warnings"):
                    print(f"            {l3['warnings'][0]}")
            
            # Layer 4: Behavior
            l4 = layers.get("layer4_behavior", {})
            if l4.get("voice_capture_attempt"):
                print(f"   Layer 4 - 🎤 VOICE CAPTURE ATTEMPT DETECTED!")
            if l4.get("red_flags"):
                print(f"   Layer 4 - Red flags: {', '.join(l4['red_flags'][:2])}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    print("\n" + "🛡️" * 20)
    print("     VERICALL MALAYSIA - API TEST SUITE")
    print("🛡️" * 20)
    
    # Test health first
    if not test_health():
        print("\n❌ Backend not running! Start it with:")
        print("   cd backend")
        print("   python -m app.main")
        return
    
    # Run all tests
    test_scam_analysis()
    test_uncle_ah_hock()
    test_audio_pipeline()
    test_intelligence()
    test_5_layer_defense()  # NEW!
    
    print("\n" + "=" * 60)
    print("  ✅ TEST COMPLETE")
    print("=" * 60)
    print("\n🎯 SUMMARY:")
    print("• Scam Analysis: Uses Gemini Pro for content detection")
    print("• Uncle Ah Hock: AI decoy that wastes scammer time")
    print("• 5-Layer Defense: Detects BOTH AI and human scammers!")
    print("\nNext steps:")
    print("1. Add audio files for full pipeline testing")
    print("2. Connect Firebase for family protection")
    print("3. Prepare demo for KitaHack 🏆")


if __name__ == "__main__":
    main()
