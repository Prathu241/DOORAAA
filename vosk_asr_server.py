"""
Vosk ASR Server for DORA
Listens on HTTP port 2700
Accepts POST /recognize with raw PCM16 audio bytes
Returns JSON transcript

Run: python vosk_asr_server.py
"""

import json
import struct
import wave
import io
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from vosk import Model, KaldiRecognizer

MODEL_PATH = os.path.join(os.path.dirname(__file__), "vosk-model-small-en-us-0.15")
SAMPLE_RATE = 16000
PORT = 2700

print("=" * 50)
print("  DORA Vosk ASR Server")
print("=" * 50)
print(f"  Model : {MODEL_PATH}")
print(f"  Port  : {PORT}")
print()

if not os.path.exists(MODEL_PATH):
    print(f"ERROR: Model not found at {MODEL_PATH}")
    print("Download: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
    sys.exit(1)

print("Loading Vosk model (may take a few seconds)...")
model = Model(MODEL_PATH)
print("✅ Model loaded — ready for recognition\n")


class ASRHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress default HTTP server logs, use our own
        pass

    def do_POST(self):
        if self.path == "/recognize":
            content_length = int(self.headers.get("Content-Length", 0))
            audio_bytes = self.rfile.read(content_length)

            if not audio_bytes:
                self._respond(400, {"error": "No audio data"})
                return

            try:
                transcript = self._recognize(audio_bytes)
                response = {
                    "transcript": transcript,
                    "success": True,
                    "bytes_received": len(audio_bytes),
                    "duration_ms": int(len(audio_bytes) / 2 / SAMPLE_RATE * 1000)
                }
                print(f"  ✅ Recognized: \"{transcript}\" ({len(audio_bytes)} bytes)")
                self._respond(200, response)

            except Exception as e:
                print(f"  ❌ Recognition error: {e}")
                self._respond(500, {"error": str(e), "transcript": ""})

        elif self.path == "/health":
            self._respond(200, {"status": "ready", "model": "vosk-small-en-us", "port": PORT})

        else:
            self._respond(404, {"error": "Not found"})

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ready", "model": "vosk-small-en-us"})
        else:
            self._respond(404, {"error": "Not found"})

    def _recognize(self, audio_bytes):
        """Run Vosk recognition on raw PCM16 bytes at 16kHz mono."""
        rec = KaldiRecognizer(model, SAMPLE_RATE)
        rec.SetWords(True)

        # Feed audio in chunks
        chunk_size = 4000
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            rec.AcceptWaveform(chunk)

        # Get final result
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), ASRHandler)
    print(f"🎙️  Vosk ASR Server running on http://localhost:{PORT}")
    print(f"    POST /recognize  — send raw PCM16 bytes, get transcript")
    print(f"    GET  /health     — check server status")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 ASR server stopped")
