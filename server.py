"""Serve the local research dashboard and its RAG question endpoint."""

from __future__ import annotations

import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

from agent import ChildhoodCancerAgent
from poster_agent.content.generator import PosterAgent


PROJECT_DIR = Path(__file__).resolve().parent


class DashboardHandler(SimpleHTTPRequestHandler):
    agent: ChildhoodCancerAgent | None = None
    poster_agent: PosterAgent | None = None

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json(
                200,
                {
                    "indexed_chunks": len(self.agent.chunks) if self.agent else 0,
                    "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
                },
            )
            return
        if self.path == "/api/poster/status":
            self._send_json(200, {"llm_configured": bool(os.getenv("OPENAI_API_KEY"))})
            return
        super().do_GET()

    def do_POST(self):
        if self.path not in {"/api/ask", "/api/poster/generate"}:
            self._send_json(404, {"error": "Endpoint not found."})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            maximum_length = 8000 if self.path == "/api/poster/generate" else 12000
            if content_length < 1 or content_length > maximum_length:
                self._send_json(413, {"error": "Request is empty or too large."})
                return
            payload = json.loads(self.rfile.read(content_length))
            if not isinstance(payload, dict):
                self._send_json(400, {"error": "Request body must be a JSON object."})
                return
            if self.path == "/api/poster/generate":
                prompt = payload.get("prompt", "")
                if not isinstance(prompt, str) or len(prompt) > 1500:
                    self._send_json(400, {"error": "Poster prompt must be text under 1,500 characters."})
                    return
                if self.poster_agent is None:
                    self._send_json(503, {"error": "The poster agent is not available."})
                    return
                self._send_json(200, self.poster_agent.generate(prompt))
            else:
                question = payload.get("question", "")
                if not isinstance(question, str) or len(question) > 1000:
                    self._send_json(400, {"error": "Question must be text under 1,000 characters."})
                    return
                if self.agent is None:
                    self._send_json(503, {"error": "The source index is not available."})
                    return
                self._send_json(200, self.agent.answer(question))
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
        except RuntimeError as error:
            self._send_json(503, {"error": str(error)})
        except requests.RequestException:
            self._send_json(502, {"error": "The LLM request failed. Check the configured endpoint and API credentials."})

    def translate_path(self, path):
        relative = unquote(urlsplit(path).path).lstrip("/")
        if relative in {"", "index.html"}:
            relative = "dashboard.html"
        if relative in {"childhood-cancer-site", "childhood-cancer-site/"}:
            relative = "childhood-cancer-site/index.html"
        if relative in {"poster-agent", "poster-agent/"}:
            relative = "poster_agent/ui/index.html"
        candidate = (PROJECT_DIR / relative).resolve()
        allowed_root_files = {"dashboard.html", "childhood_cancer_research.md"}
        allowed_root_file = candidate.parent == PROJECT_DIR and candidate.name in allowed_root_files
        allowed_poster_ui = candidate == (PROJECT_DIR / "poster_agent" / "ui" / "index.html").resolve()
        allowed_data_file = candidate.parent == (PROJECT_DIR / "data").resolve() and (
            candidate.suffix == ".txt" or candidate.name == "cancer_biomarkers.pdf"
        )
        site_dir = (PROJECT_DIR / "childhood-cancer-site").resolve()
        allowed_site_file = candidate.parent == site_dir and candidate.name in {
            "index.html",
            "childhood_cancer_research.pdf",
            "dataset_analysis.md",
            "childhood-cancer-hope-progress.png",
        }
        site_data_dir = (site_dir / "data").resolve()
        allowed_site_data = candidate.parent == site_data_dir and candidate.name in {
            "diabetes_trials.csv",
            "trials_by_year.svg",
            "trial_status.svg",
            "trial_period_comparison.svg",
        }
        if not (
            allowed_root_file
            or allowed_poster_ui
            or allowed_data_file
            or allowed_site_file
            or allowed_site_data
        ):
            candidate = PROJECT_DIR / "__not_found__"
        return str(candidate)

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=str(PROJECT_DIR / "data"))
    args = parser.parse_args()

    DashboardHandler.agent = ChildhoodCancerAgent(args.data_dir)
    DashboardHandler.poster_agent = PosterAgent()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        partial(DashboardHandler, directory=str(PROJECT_DIR)),
    )
    print("Childhood cancer RAG dashboard: http://127.0.0.1:{}/dashboard.html".format(args.port))
    print("Prompt-driven poster maker: http://127.0.0.1:{}/poster-agent/".format(args.port))
    print("Indexed {} source chunks".format(len(DashboardHandler.agent.chunks)))
    server.serve_forever()


if __name__ == "__main__":
    main()
