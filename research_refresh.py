"""Background refresh of scraped research sources and the RAG index."""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from agent import ChildhoodCancerAgent
from ingest import refresh_sources


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _source_inventory(data_dir: Path) -> dict[str, dict[str, object]]:
    paths = list(data_dir.glob("*.txt"))
    pdf_path = data_dir / "cancer_biomarkers.pdf"
    if pdf_path.is_file():
        paths.append(pdf_path)

    inventory = {}
    for path in sorted(paths):
        try:
            content = path.read_bytes()
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            continue
        inventory[path.name] = {
            "name": path.name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "modified_at": modified.isoformat(timespec="seconds"),
        }
    return inventory


class ResearchRefreshService:
    """Periodically scrape configured web sources and rebuild the RAG index."""

    def __init__(
        self,
        data_dir: str | Path,
        interval_seconds: int,
        replace_agent: Callable[[ChildhoodCancerAgent], None],
        scraper: Callable[[], list[dict[str, object]]] = refresh_sources,
        agent_factory: Callable[[str | Path], ChildhoodCancerAgent] = ChildhoodCancerAgent,
    ):
        if interval_seconds <= 0:
            raise ValueError("Refresh interval must be positive.")
        self.data_dir = Path(data_dir)
        self.interval_seconds = interval_seconds
        self.replace_agent = replace_agent
        self.scraper = scraper
        self.agent_factory = agent_factory
        self._refresh_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status_lock = threading.Lock()
        cached = _source_inventory(self.data_dir)
        self._status: dict[str, object] = {
            "refresh_interval_seconds": interval_seconds,
            "refresh_in_progress": False,
            "last_refresh_at": None,
            "last_success_at": None,
            "next_refresh_at": None,
            "last_refresh_error": None,
            "source_count": len(cached),
            "indexed_source_count": 0,
            "cached_sources": list(cached.values()),
            "changed_sources": [],
            "last_refresh_results": [],
        }

    def start(self, run_immediately: bool = True) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(run_immediately,),
            name="research-refresh",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def status(self) -> dict[str, object]:
        with self._status_lock:
            return {
                **self._status,
                "cached_sources": list(self._status["cached_sources"]),
                "changed_sources": list(self._status["changed_sources"]),
                "last_refresh_results": list(self._status["last_refresh_results"]),
            }

    def refresh_once(self) -> dict[str, object]:
        if not self._refresh_lock.acquire(blocking=False):
            return self.status()

        started_at = _now()
        with self._status_lock:
            self._status["refresh_in_progress"] = True
            self._status["next_refresh_at"] = (
                started_at + timedelta(seconds=self.interval_seconds)
            ).isoformat(timespec="seconds")

        before = _source_inventory(self.data_dir)
        results: list[dict[str, object]] = []
        changed = []
        refresh_error = None
        reindexed_source_count = int(self._status["indexed_source_count"])
        try:
            results = self.scraper()
            successful = [result for result in results if result.get("ok")]
            errors = [result for result in results if not result.get("ok")]
            after = _source_inventory(self.data_dir)
            changed = [
                {key: value for key, value in after[name].items() if key != "sha256"}
                for name in sorted(after)
                if before.get(name, {}).get("sha256") != after[name]["sha256"]
            ]

            if successful:
                new_agent = self.agent_factory(self.data_dir)
                if not new_agent.chunks:
                    raise RuntimeError("The refreshed research index contains no source passages.")
                self.replace_agent(new_agent)
                reindexed_source_count = len({chunk.source for chunk in new_agent.chunks})
            elif errors:
                refresh_error = "; ".join(
                    f"{result.get('title', 'Source')}: {result.get('error', 'scrape failed')}"
                    for result in errors
                )
            else:
                refresh_error = "The web scraper returned no source results."

            if successful and errors:
                refresh_error = "; ".join(
                    f"{result.get('title', 'Source')}: {result.get('error', 'scrape failed')}"
                    for result in errors
                )
            with self._status_lock:
                self._status["source_count"] = len(after)
                self._status["cached_sources"] = list(after.values())
                self._status["changed_sources"] = changed
                self._status["last_refresh_results"] = results
                self._status["indexed_source_count"] = reindexed_source_count
                self._status["last_refresh_error"] = refresh_error
                if successful:
                    self._status["last_success_at"] = _now().isoformat(timespec="seconds")
        except Exception as error:
            refresh_error = str(error)
            current = _source_inventory(self.data_dir)
            with self._status_lock:
                self._status["source_count"] = len(current)
                self._status["cached_sources"] = list(current.values())
                self._status["changed_sources"] = changed
                self._status["last_refresh_results"] = results
                self._status["last_refresh_error"] = refresh_error
        finally:
            completed_at = _now()
            with self._status_lock:
                self._status["refresh_in_progress"] = False
                self._status["last_refresh_at"] = completed_at.isoformat(timespec="seconds")
                self._status["next_refresh_at"] = (
                    completed_at + timedelta(seconds=self.interval_seconds)
                ).isoformat(timespec="seconds")
            self._refresh_lock.release()

        return self.status()

    def _run(self, run_immediately: bool) -> None:
        if not run_immediately and self._stop_event.wait(self.interval_seconds):
            return
        while not self._stop_event.is_set():
            self.refresh_once()
            if self._stop_event.wait(self.interval_seconds):
                return
