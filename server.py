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
from multi_agent.orchestrator import AgentOrchestrator, build_default_orchestrator
from poster_agent.content.generator import PosterAgent
from research_refresh import ResearchRefreshService


PROJECT_DIR = Path(__file__).resolve().parent


class DashboardHandler(SimpleHTTPRequestHandler):
    agent: ChildhoodCancerAgent | None = None
    orchestrator: AgentOrchestrator | None = None
    poster_agent: PosterAgent | None = None
    refresh_service: ResearchRefreshService | None = None
    data_dir: Path = PROJECT_DIR / "data"

    def guess_type(self, path):
        if str(path).lower().endswith(".m4a"):
            return "audio/mp4"
        return super().guess_type(path)

    def do_GET(self):
        if self.path == "/api/agents":
            self._send_json(200, {"agents": self.orchestrator.list_agents() if self.orchestrator else []})
            return
        if self.path == "/api/health":
            healthy = bool(self.agent and self.agent.chunks)
            refresh_status = self.refresh_service.status() if self.refresh_service else {}
            self._send_json(
                200 if healthy else 503,
                {
                    "ok": healthy,
                    "status": "ok" if healthy else "unavailable",
                    "indexed_chunks": len(self.agent.chunks) if self.agent else 0,
                    "last_refresh_error": refresh_status.get("last_refresh_error"),
                },
            )
            return
        if self.path == "/api/status":
            refresh_status = self.refresh_service.status() if self.refresh_service else {}
            self._send_json(
                200,
                {
                    **refresh_status,
                    "indexed_chunks": len(self.agent.chunks) if self.agent else 0,
                    "indexed_source_count": len({chunk.source for chunk in self.agent.chunks}) if self.agent else 0,
                    "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
                },
            )
            return
        if self.path == "/api/poster/status":
            self._send_json(200, {"llm_configured": bool(os.getenv("OPENAI_API_KEY"))})
            return
        super().do_GET()

    def end_headers(self):
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "public, max-age=300, must-revalidate")
        super().end_headers()

    def do_POST(self):
        agent_paths = {"/api/agents/run", "/api/agents/workflow"}
        if self.path not in {"/api/ask", "/api/poster/generate", *agent_paths}:
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
            if self.path in agent_paths:
                if self.orchestrator is None:
                    self._send_json(503, {"error": "The agent orchestrator is not available."})
                    return
                if self.path == "/api/agents/run":
                    task_type = payload.get("task_type")
                    task_payload = payload.get("payload", {})
                    if not isinstance(task_type, str) or not isinstance(task_payload, dict):
                        self._send_json(400, {"error": "task_type must be text and payload must be an object."})
                        return
                    result = self.orchestrator.run(task_type, task_payload)
                else:
                    workflow = payload.get("workflow")
                    workflow_payload = payload.get("payload", {})
                    if not isinstance(workflow, str) or not isinstance(workflow_payload, dict):
                        self._send_json(400, {"error": "workflow must be text and payload must be an object."})
                        return
                    result = self.orchestrator.run_workflow(workflow, workflow_payload)
                self._send_json(200, result)
            elif self.path == "/api/poster/generate":
                prompt = payload.get("prompt", "")
                if not isinstance(prompt, str) or len(prompt) > 1500:
                    self._send_json(400, {"error": "Poster prompt must be text under 1,500 characters."})
                    return
                if self.poster_agent is None:
                    self._send_json(503, {"error": "The poster agent is not available."})
                    return
                preset = payload.get("preset")
                if preset == "childhood-cancer":
                    self._send_json(200, self.poster_agent.generate_childhood_cancer_preset())
                elif preset is not None:
                    self._send_json(400, {"error": "Unknown poster preset."})
                else:
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
        data_root = Path(getattr(self, "data_dir", PROJECT_DIR / "data")).resolve()
        if relative.startswith("data/"):
            candidate = (data_root / relative.removeprefix("data/")).resolve()
        else:
            candidate = (PROJECT_DIR / relative).resolve()
        allowed_root_files = {
            "dashboard.html",
            "treatment-plan.html",
            "care-locations.html",
            "death-estimates.html",
            "fundraising.html",
            "fundraising-episode.html",
            "radio-channel.html",
            "childhood_cancer_research.md",
        }
        allowed_root_file = candidate.parent == PROJECT_DIR and candidate.name in allowed_root_files
        allowed_poster_ui = candidate == (PROJECT_DIR / "poster_agent" / "ui" / "index.html").resolve()
        media_dir = (PROJECT_DIR / "media").resolve()
        allowed_fundraiser_media = candidate.parent == media_dir and candidate.name in {
            "fundraising-episode-01.m4a",
            "fundraising-episode-01.mp4",
            "fundraising-episode-01.txt",
        }
        allowed_data_file = candidate.parent == data_root and (
            candidate.suffix == ".txt" or candidate.name == "cancer_biomarkers.pdf"
        )
        site_dir = (PROJECT_DIR / "childhood-cancer-site").resolve()
        allowed_site_file = candidate.parent == site_dir and candidate.name in {
            "index.html",
            "childhood_cancer_research.pdf",
            "dataset_analysis.md",
            "childhood-cancer-hope-progress.png",
            "childhood-cancer-short.mp4",
            "nanorobot-short.mp4",
        }
        site_share_dir = (site_dir / "share").resolve()
        allowed_site_share = candidate.parent == site_share_dir and candidate.name in {
            "childhood-cancer.html",
            "nanorobots.html",
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
            or allowed_fundraiser_media
            or allowed_data_file
            or allowed_site_file
            or allowed_site_share
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
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    parser.add_argument("--data-dir", default=str(PROJECT_DIR / "data"))
    parser.add_argument("--refresh-interval-hours", type=float, default=3.0)
    parser.add_argument("--skip-initial-refresh", action="store_true")
    args = parser.parse_args()
    if args.refresh_interval_hours <= 0:
        parser.error("--refresh-interval-hours must be positive")

    DashboardHandler.agent = ChildhoodCancerAgent(args.data_dir)
    DashboardHandler.data_dir = Path(args.data_dir).resolve()
    DashboardHandler.poster_agent = PosterAgent()
    DashboardHandler.orchestrator = build_default_orchestrator(
        research_agent=DashboardHandler.agent,
        poster_agent=DashboardHandler.poster_agent,
        workspace_root=PROJECT_DIR,
    )
    refresh_service = ResearchRefreshService(
        args.data_dir,
        int(args.refresh_interval_hours * 60 * 60),
        lambda agent: setattr(DashboardHandler, "agent", agent),
    )
    DashboardHandler.refresh_service = refresh_service
    server = ThreadingHTTPServer(
        (args.host, args.port),
        partial(DashboardHandler, directory=str(PROJECT_DIR)),
    )
    print("Childhood cancer RAG dashboard: http://127.0.0.1:{}/dashboard.html".format(args.port))
    print("Prompt-driven poster maker: http://127.0.0.1:{}/poster-agent/".format(args.port))
    print("Indexed {} source chunks".format(len(DashboardHandler.agent.chunks)))
    print("Web research scrape refresh interval: {} hours".format(args.refresh_interval_hours))
    refresh_service.start(run_immediately=not args.skip_initial_refresh)
    try:
        server.serve_forever()
    finally:
        refresh_service.stop()
        server.server_close()


if __name__ == "__main__":
    main()
