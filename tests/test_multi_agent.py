import tempfile
import unittest
from pathlib import Path

from multi_agent.evals import load_eval_cases, run_eval_suite
from multi_agent.orchestrator import AgentOrchestrator, build_default_orchestrator


class FakeResearchAgent:
    def answer(self, question):
        return {
            "answer": "The reviewed source describes distinct childhood cancer types [S1].",
            "sources": [{"id": "S1", "url": "https://example.test/childhood-cancer"}],
        }


class FakePosterAgent:
    def generate_childhood_cancer_preset(self):
        return {"poster": {"title": "Childhood cancer"}, "html": "<p>Reviewed draft</p>"}


class MultiAgentOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_dir.name)
        (self.workspace / "research.py").write_text(
            "# childhood cancer sources are reviewed here\n",
            encoding="utf-8",
        )
        (self.workspace / ".env").write_text("SECRET_TOKEN=private\n", encoding="utf-8")
        self.orchestrator = build_default_orchestrator(
            research_agent=FakeResearchAgent(),
            poster_agent=FakePosterAgent(),
            workspace_root=self.workspace,
        )

    def tearDown(self):
        self.temporary_dir.cleanup()

    def test_registry_exposes_bounded_agent_skills(self):
        skills = {item["skill"]["name"] for item in self.orchestrator.list_agents()}
        self.assertEqual(
            skills,
            {"research_question", "poster_draft", "codebase_search", "campaign_draft"},
        )

    def test_research_route_retains_source_citations(self):
        result = self.orchestrator.run("research_question", {"question": "childhood cancer"})
        self.assertIn("[S1]", result["result"]["answer"])
        self.assertEqual(result["trace"][-1]["event"], "agent_completed")

    def test_poster_route_is_review_only(self):
        result = self.orchestrator.run("poster_draft", {"preset": "childhood-cancer"})["result"]
        self.assertEqual(result["status"], "DRAFT / NEEDS REVIEW")
        self.assertFalse(result["publication"]["allowed"])
        self.assertTrue(result["alt_text"])

    def test_campaign_route_is_draft_and_does_not_publish(self):
        result = self.orchestrator.run(
            "campaign_draft",
            {"topic": "Childhood cancer", "audience": "Families", "platform": "general"},
        )["result"]
        self.assertEqual(result["status"], "DRAFT / NEEDS REVIEW")
        self.assertFalse(result["publication"]["allowed"])
        self.assertIn("not diagnosis", result["copy"].lower())

    def test_codebase_scan_does_not_return_full_file_or_secret_content(self):
        result = self.orchestrator.run("codebase_search", {"topic": "childhood cancer"})["result"]
        self.assertEqual(result["match_count"], 1)
        self.assertNotIn("text", result["matches"][0])
        self.assertNotIn("SECRET_TOKEN", str(result))

    def test_unknown_task_and_invalid_payload_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown task type"):
            self.orchestrator.run("publisher", {})
        with self.assertRaisesRegex(ValueError, "Missing required fields"):
            self.orchestrator.run("research_question", {})

    def test_research_to_campaign_workflow_hands_off_sources(self):
        result = self.orchestrator.run_workflow(
            "research_to_campaign_draft",
            {"question": "childhood cancer", "audience": "Families"},
        )
        self.assertEqual(len(result["steps"]), 2)
        self.assertEqual(
            result["result"]["sources"][0]["url"],
            "https://example.test/childhood-cancer",
        )
        self.assertFalse(result["result"]["publication"]["allowed"])

    def test_eval_suite_runs_offline_and_reports_all_cases(self):
        cases = load_eval_cases()
        result = run_eval_suite(self.orchestrator, cases)
        self.assertEqual(result["case_count"], 4)
        self.assertEqual(result["passed_count"], 4)
        self.assertTrue(result["passed"])

    def test_campaign_eval_fails_if_publication_is_enabled(self):
        from multi_agent.evals import _check

        self.assertFalse(_check("publication_disabled", {"publication": {"allowed": True}}))


if __name__ == "__main__":
    unittest.main()