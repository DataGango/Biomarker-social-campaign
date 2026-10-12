import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from agent import ChildhoodCancerAgent


class ChildhoodCancerAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        (self.data_dir / "leukemia.txt").write_text(
            "Source: https://example.test/leukemia\n\n"
            "Childhood leukemia survival depends on subtype, age, and response to treatment.\n",
            encoding="utf-8",
        )
        (self.data_dir / "genetics.txt").write_text(
            "Source: https://example.test/genetics\n\n"
            "Inherited cancer predisposition can be associated with family history.\n",
            encoding="utf-8",
        )
        self.agent = ChildhoodCancerAgent(self.data_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_retrieval_ranks_relevant_source(self):
        matches = self.agent.retrieve("childhood leukemia survival")
        self.assertTrue(matches)
        self.assertEqual(matches[0].source, "https://example.test/leukemia")

    def test_unmatched_question_returns_grounded_no_match(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = self.agent.answer("What is the history of astronomy?")
        self.assertEqual(result["sources"], [])
        self.assertIn("could not find relevant information", result["answer"])

    def test_missing_api_key_has_actionable_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                self.agent.answer("What affects childhood leukemia survival?")

    def test_llm_request_contains_retrieved_source_and_returns_citation_source(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Outcomes vary by subtype [S1]."}}]
        }
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("agent.requests.post", return_value=response) as post:
                result = self.agent.answer("What affects childhood leukemia survival?")

        self.assertEqual(result["answer"], "Outcomes vary by subtype [S1].")
        self.assertEqual(result["sources"][0]["url"], "https://example.test/leukemia")
        request_body = post.call_args.kwargs["json"]
        self.assertIn("https://example.test/leukemia", request_body["messages"][1]["content"])
        self.assertIn("Cite factual statements", request_body["messages"][0]["content"])

    def test_blank_question_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Enter a question"):
            self.agent.answer("   ")


if __name__ == "__main__":
    unittest.main()
