"""Run the standalone, localhost-only prompt-driven poster generator."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

from poster_agent.content.generator import PosterAgent


PROJECT_DIR = Path(__file__).resolve().parent.parent
UI_FILE = Path(__file__).resolve().parent / "ui" / "index.html"
load_dotenv(PROJECT_DIR / ".env", override=False)


class PosterHandler(BaseHTTPRequestHandler):
    poster_agent = PosterAgent()

    def do_GET(self):
        if self.path == "/api/poster/status":
            self._send_json(200, {"llm_configured": bool(os.getenv("OPENAI_API_KEY"))})
            return
        if self.path in {"/", "/index.html", "/poster-agent/"}:
            body = UI_FILE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(404, {"error": "Not found."})

    def do_POST(self):
        if self.path != "/api/poster/generate":
            self._send_json(404, {"error": "Endpoint not found."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > 8000:
                self._send_json(413, {"error": "Request is empty or too large."})
                return
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                self._send_json(400, {"error": "Request body must be a JSON object."})
                return
            prompt = payload.get("prompt", "")
            if not isinstance(prompt, str) or len(prompt) > 1500:
                self._send_json(400, {"error": "Poster prompt must be text under 1,500 characters."})
                return
            self._send_json(200, self.poster_agent.generate(prompt))
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except RuntimeError as error:
            self._send_json(503, {"error": str(error)})
        except requests.RequestException:
            self._send_json(502, {"error": "The poster model request failed. Check the API URL and credentials."})

    def _send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PosterHandler)
    print(f"Prompt-driven poster maker: http://127.0.0.1:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
