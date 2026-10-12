import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from research_refresh import ResearchRefreshService


class ResearchRefreshTests(unittest.TestCase):
    def test_successful_scrape_rebuilds_index_and_reports_cache_changes(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            source = data_dir / "childhood_cancer_nci.txt"
            source.write_text("old research", encoding="utf-8")
            replacements = []

            def scrape_web_sources():
                source.write_text("updated research", encoding="utf-8")
                return [{"title": "NCI fact sheet", "ok": True, "error": None}]

            def build_agent(_data_dir):
                return SimpleNamespace(chunks=[SimpleNamespace(source="https://nci.example/research")])

            service = ResearchRefreshService(
                data_dir,
                10_800,
                replacements.append,
                scraper=scrape_web_sources,
                agent_factory=build_agent,
            )

            status = service.refresh_once()

            self.assertEqual(source.read_text(encoding="utf-8"), "updated research")
            self.assertEqual(len(replacements), 1)
            self.assertEqual(status["source_count"], 1)
            self.assertEqual(status["indexed_source_count"], 1)
            self.assertEqual(status["changed_sources"][0]["name"], source.name)
            self.assertIsNotNone(status["last_success_at"])
            self.assertEqual(status["refresh_interval_seconds"], 10_800)

    def test_failed_web_scrape_keeps_existing_index_and_cache(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_dir = Path(temporary_dir)
            source = data_dir / "childhood_cancer_nci.txt"
            source.write_text("last good research", encoding="utf-8")
            replacements = []

            def failed_scrape():
                return [{"title": "NCI fact sheet", "ok": False, "error": "offline"}]

            service = ResearchRefreshService(
                data_dir,
                10_800,
                replacements.append,
                scraper=failed_scrape,
                agent_factory=lambda _data_dir: self.fail("Must not replace the index after a failed scrape"),
            )

            status = service.refresh_once()

            self.assertEqual(source.read_text(encoding="utf-8"), "last good research")
            self.assertEqual(replacements, [])
            self.assertEqual(status["last_refresh_error"], "NCI fact sheet: offline")
            self.assertIsNone(status["last_success_at"])

    def test_refresh_interval_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            ResearchRefreshService(Path("."), 0, lambda _agent: None)


if __name__ == "__main__":
    unittest.main()
