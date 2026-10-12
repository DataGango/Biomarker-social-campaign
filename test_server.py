import unittest
from pathlib import Path
from unittest.mock import Mock
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
import json

from server import DashboardHandler, PROJECT_DIR


class DashboardStaticAccessTests(unittest.TestCase):
    def test_dashboard_is_served_from_project(self):
        path = Path(DashboardHandler.translate_path(None, "/dashboard.html"))
        self.assertEqual(path, PROJECT_DIR / "dashboard.html")

    def test_treatment_plan_page_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/treatment-plan.html"))
        self.assertEqual(path, PROJECT_DIR / "treatment-plan.html")

    def test_fundraising_episode_page_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/fundraising-episode.html"))
        self.assertEqual(path, PROJECT_DIR / "fundraising-episode.html")

    def test_global_health_radio_page_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/radio-channel.html"))
        self.assertEqual(path, PROJECT_DIR / "radio-channel.html")

    def test_radio_archive_source_pages_are_allowlisted(self):
        childhood = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/share/childhood-cancer.html"))
        nanorobots = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/share/nanorobots.html"))
        self.assertEqual(childhood, PROJECT_DIR / "childhood-cancer-site" / "share" / "childhood-cancer.html")
        self.assertEqual(nanorobots, PROJECT_DIR / "childhood-cancer-site" / "share" / "nanorobots.html")

    def test_fundraising_media_is_allowlisted_but_other_media_is_not(self):
        audio = Path(DashboardHandler.translate_path(None, "/media/fundraising-episode-01.m4a"))
        transcript = Path(DashboardHandler.translate_path(None, "/media/fundraising-episode-01.txt"))
        unknown = Path(DashboardHandler.translate_path(None, "/media/private.mp4"))
        self.assertEqual(audio, PROJECT_DIR / "media" / "fundraising-episode-01.m4a")
        self.assertEqual(transcript, PROJECT_DIR / "media" / "fundraising-episode-01.txt")
        self.assertEqual(unknown, PROJECT_DIR / "__not_found__")

    def test_care_locations_page_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/care-locations.html"))
        self.assertEqual(path, PROJECT_DIR / "care-locations.html")

    def test_poster_agent_route_resolves_to_generator_ui(self):
        path = Path(DashboardHandler.translate_path(None, "/poster-agent/"))
        self.assertEqual(path, PROJECT_DIR / "poster_agent" / "ui" / "index.html")

    def test_poster_agent_source_code_is_not_served(self):
        path = Path(DashboardHandler.translate_path(None, "/poster_agent/content/generator.py"))
        self.assertEqual(path, PROJECT_DIR / "__not_found__")

    def test_childhood_site_route_resolves_to_site_home(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "index.html")

    def test_childhood_paper_pdf_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/childhood_cancer_research.pdf"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "childhood_cancer_research.pdf")

    def test_downloaded_childhood_cancer_image_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/childhood-cancer-hope-progress.png"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "childhood-cancer-hope-progress.png")

    def test_dataset_report_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/dataset_analysis.md"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "dataset_analysis.md")

    def test_dataset_plot_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/data/trials_by_year.svg"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "data" / "trials_by_year.svg")

    def test_dataset_csv_is_allowlisted(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/data/diabetes_trials.csv"))
        self.assertEqual(path, PROJECT_DIR / "childhood-cancer-site" / "data" / "diabetes_trials.csv")

    def test_dataset_analyzer_code_is_not_served(self):
        path = Path(DashboardHandler.translate_path(None, "/childhood-cancer-site/analyze_dataset.py"))
        self.assertEqual(path, PROJECT_DIR / "__not_found__")

    def test_local_env_file_is_not_served(self):
        path = Path(DashboardHandler.translate_path(None, "/.env"))
        self.assertEqual(path, PROJECT_DIR / "__not_found__")

    def test_agent_source_code_is_not_served(self):
        path = Path(DashboardHandler.translate_path(None, "/agent.py"))
        self.assertEqual(path, PROJECT_DIR / "__not_found__")

    def test_ingested_source_artifact_is_available(self):
        path = Path(DashboardHandler.translate_path(None, "/data/cancer_genetics.txt"))
        self.assertEqual(path, PROJECT_DIR / "data" / "cancer_genetics.txt")


class DashboardAgentApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_orchestrator = DashboardHandler.orchestrator
        cls.orchestrator = Mock()
        cls.orchestrator.list_agents.return_value = [{"name": "Test Agent"}]
        cls.orchestrator.run.return_value = {"status": "completed", "result": {"ok": True}}
        cls.orchestrator.run_workflow.return_value = {"status": "completed", "workflow": "test"}
        DashboardHandler.orchestrator = cls.orchestrator
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = "http://127.0.0.1:{}".format(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        DashboardHandler.orchestrator = cls.previous_orchestrator

    def test_agent_registry_endpoint(self):
        with urlopen(self.base_url + "/api/agents") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["agents"][0]["name"], "Test Agent")

    def test_run_agent_endpoint_delegates_registered_task(self):
        request = Request(
            self.base_url + "/api/agents/run",
            data=json.dumps({"task_type": "research_question", "payload": {"question": "test"}}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request) as response:
            payload = json.loads(response.read())
        self.assertTrue(payload["result"]["ok"])
        self.orchestrator.run.assert_called_with("research_question", {"question": "test"})

    def test_agent_endpoint_rejects_malformed_contract(self):
        request = Request(
            self.base_url + "/api/agents/run",
            data=json.dumps({"task_type": "research_question", "payload": []}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(Exception) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
