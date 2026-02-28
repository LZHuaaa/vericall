"""
VeriCall Malaysia - Flask Application
"""
import sys

# Windows terminals often default to cp1252 and crash on emoji logs.
for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from flask import Flask
from flask_cors import CORS
from app.config import config
from app.api.routes import api_bp
from app.services.call_audio_bridge import call_audio_bridge


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for mobile app
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Health check endpoint
    @app.route("/health")
    def health():
        return {"status": "healthy", "service": "VeriCall Malaysia"}
    
    @app.route("/")
    def index():
        return {
            "name": "VeriCall Malaysia API",
            "version": "1.0.0",
            "description": "AI-powered voice scam detection and active defense",
            "endpoints": {
                "health": "/health",
                "analyze_audio": "/api/analyze",
                "threat_live": "/api/threat/live",
                "threat_session": "/api/threat/session/<session_id>",
                "call_start": "/api/call/demo/start",
                "call_end": "/api/call/demo/end",
                "deploy_decoy": "/api/decoy",
                "scam_intel": "/api/intelligence",
                "family_alert": "/api/family/alert"
            }
        }

    # Start optional audio relay bridge once app is initialized.
    call_audio_bridge.start()
    
    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    print("🛡️ VeriCall Malaysia API Starting...")
    print(f"   Debug Mode: {config.DEBUG}")
    print(f"   Port: {config.PORT}")
    print(f"   Gemini Model: {config.GEMINI_MODEL}")
    # use_reloader=False fixes Python 3.13 + watchdog threading issue
    app.run(host='0.0.0.0', debug=config.DEBUG, port=config.PORT, use_reloader=False)
