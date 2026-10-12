import unittest
from pathlib import Path

from server import DashboardHandler, PROJECT_DIR


class DashboardStaticAccessTests(unittest.TestCase):
    def test_dashboard_is_served_from_project(self):
        path = Path(DashboardHandler.translate_path(None, "/dashboard.html"))
        self.assertEqual(path, PROJECT_DIR / "dashboard.html")

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


if __name__ == "__main__":
    unittest.main()
