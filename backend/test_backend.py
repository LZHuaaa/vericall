"""
VeriCall Malaysia - Quick Test Script

Tests all backend components to verify they work.
Run this after installation to confirm everything is set up correctly.

Usage:
    cd backend
    python test_backend.py
"""
import asyncio
import sys
import os

# Make output robust on Windows terminals with cp1252 defaults.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_imports():
    """Test that all modules can be imported"""
    print("\n1️⃣ Testing imports...")
    
    try:
        from app.config import config
        print(f"   ✅ Config loaded (Gemini Model: {config.GEMINI_MODEL})")
        
        from app.models.schemas import ScamType, ScamAnalysis
        print("   ✅ Models loaded")
        
        from app.services.deepfake_detector import deepfake_detector
        print("   ✅ DeepfakeDetector loaded")
        
        from app.services.scam_analyzer import scam_analyzer
        print("   ✅ ScamAnalyzer loaded")
        
        from app.services.uncle_ah_hock import uncle_ah_hock
        print("   ✅ Uncle Ah Hock loaded")
        
        from app.services.scam_intelligence import scam_intelligence
        print("   ✅ ScamIntelligence loaded")
        
        return True
    except Exception as e:
        print(f"   ❌ Import error: {e}")
        return False


def test_flask_app():
    """Test Flask app can be created"""
    print("\n2️⃣ Testing Flask app...")
    
    try:
        from app.main import create_app
        app = create_app()
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            if response.status_code == 200:
                print("   ✅ Health endpoint working")
            else:
                print(f"   ❌ Health endpoint returned {response.status_code}")
                return False
            
            # Test API status
            response = client.get('/api/status')
            if response.status_code == 200:
                print("   ✅ API status endpoint working")
            else:
                print(f"   ❌ API status endpoint returned {response.status_code}")
        
        return True
    except Exception as e:
        print(f"   ❌ Flask error: {e}")
        return False


def test_uncle_ah_hock():
    """Test Uncle Ah Hock decoy (requires GEMINI_API_KEY)"""
    print("\n3️⃣ Testing Uncle Ah Hock...")
    
    from app.config import config
    
    if not config.GEMINI_API_KEY:
        print("   ⚠️ GEMINI_API_KEY not set - skipping")
        return True
    
    try:
        from app.services.uncle_ah_hock import uncle_ah_hock
        
        # Start session
        session_id = uncle_ah_hock.start_session()
        print(f"   ✅ Session started: {session_id[:8]}...")
        
        # Generate response
        response = uncle_ah_hock.generate_response(
            session_id,
            "This is LHDN! You owe RM8000 tax!"
        )
        print(f"   ✅ Uncle responded: \"{response[:60]}...\"")
        
        # Get stats
        stats = uncle_ah_hock.get_session_stats(session_id)
        print(f"   ✅ Session stats: {stats['exchanges']} exchanges")
        
        return True
    except Exception as e:
        print(f"   ❌ Uncle Ah Hock error: {e}")
        return False


def test_scam_analyzer():
    """Test Scam Analyzer (requires GEMINI_API_KEY)"""
    print("\n4️⃣ Testing Scam Analyzer...")
    
    from app.config import config
    
    if not config.GEMINI_API_KEY:
        print("   ⚠️ GEMINI_API_KEY not set - testing fallback only")
        
        from app.services.scam_analyzer import scam_analyzer
        result = scam_analyzer._fallback_analysis(
            "This is LHDN. You owe tax RM8000. Pay now or arrest!"
        )
        print(f"   ✅ Fallback analysis: is_scam={result.is_scam}, type={result.scam_type}")
        return True
    
    try:
        from app.services.scam_analyzer import scam_analyzer
        
        result = scam_analyzer.analyze_content_sync(
            transcript="This is LHDN! You owe RM8000 tax! Pay now or police arrest you!",
            deepfake_score=0.85,
            artifacts_detected=["No background noise"]
        )
        
        print(f"   ✅ Analysis result:")
        print(f"      - Is Scam: {result.is_scam}")
        print(f"      - Type: {result.scam_type.value}")
        print(f"      - Confidence: {result.confidence:.2f}")
        print(f"      - Recommendation: {result.recommendation.value}")
        
        return True
    except Exception as e:
        print(f"   ❌ Scam Analyzer error: {e}")
        return False


def test_deepfake_detector():
    """Test DeepfakeDetector (heuristic mode)"""
    print("\n5️⃣ Testing Deepfake Detector (heuristic mode)...")
    
    try:
        import numpy as np
        from app.services.deepfake_detector import deepfake_detector
        
        # Create fake audio waveform for testing
        sample_rate = 16000
        duration = 3  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration))
        # Generate a simple sine wave with some noise
        waveform = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(len(t))
        waveform = waveform.astype(np.float32)
        
        # Test heuristic detection
        score = deepfake_detector._heuristic_detection(waveform)
        print(f"   ✅ Heuristic score: {score:.2f}")
        
        if score >= 0 and score <= 1:
            print("   ✅ Score in valid range")
        else:
            print(f"   ❌ Score out of range: {score}")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ Deepfake Detector error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("🧪 VeriCall Malaysia - Backend Tests")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Flask App", test_flask_app()))
    results.append(("Deepfake Detector", test_deepfake_detector()))
    results.append(("Scam Analyzer", test_scam_analyzer()))
    results.append(("Uncle Ah Hock", test_uncle_ah_hock()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")
        if result:
            passed += 1
    
    print(f"\n   {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Backend is ready.")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
