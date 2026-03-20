import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# ── Create Flask app ──────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# ── Enable CORS so the React frontend can talk to the backend ─
CORS(app, resources={
    r"/*": {
       "origins": [
    "http://localhost:3000",        # React dev server
    "http://localhost:3001",        # React dev server (alternate port)
    "http://localhost:5173",        # Vite dev server
    "https://your-app.vercel.app"   # Replace with your Vercel URL later
        ]
    }
})

# ── Register route blueprints ─────────────────────────────────
from routes.ask import ask_bp
from routes.admin import admin_bp

app.register_blueprint(ask_bp)
app.register_blueprint(admin_bp)


# ── Health check endpoint ─────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "running",
        "message": "ACity Student Assistant API is live.",
        "version": "1.0.0"
    }), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# ── Run the app ───────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    print(f"Starting ACity Student Assistant on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=debug)