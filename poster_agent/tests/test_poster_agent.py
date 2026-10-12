import json
import unittest
from unittest.mock import Mock, patch

from poster_agent.content.generator import PosterAgent
from poster_agent.rendering.html_renderer import render_poster


SAMPLE_POSTER = {
    "title": "Community Science Day",
    "subtitle": "Explore, learn, and make something new.",
    "poster_type": "Community event",
    "audience": "For all ages",
    "visual_metaphor": "A bright constellation of connected ideas",
    "theme": "playful",
    "sections": [
        {"heading": "Discover", "body": "Try hands-on activities.", "bullets": ["Build a small circuit"]},
        {"heading": "Join us", "body": "", "bullets": ["Bring your curiosity"]},
    ],
    "call_to_action": "Come learn with us!",
    "sources": [],
}


class PosterAgentTests(unittest.TestCase):
    def test_empty_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "poster prompt"):
            PosterAgent().generate(" ")

    def test_missing_api_key_has_actionable_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                PosterAgent().generate("Make a poster")

    def test_generation_returns_validated_poster_and_html(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(SAMPLE_POSTER)}}]
        }
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("poster_agent.content.generator.requests.post", return_value=response) as post:
                result = PosterAgent().generate("Make a community event poster")
        self.assertEqual(result["poster"]["title"], "Community Science Day")
        self.assertIn("<title>Community Science Day</title>", result["html"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-key")

    def test_unknown_theme_falls_back_to_safe_theme(self):
        invalid_theme = dict(SAMPLE_POSTER, theme="body{background:red}")
        validated = PosterAgent._validate_content(invalid_theme)
        self.assertEqual(validated["theme"], "editorial")

    def test_renderer_escapes_model_text(self):
        unsafe = dict(SAMPLE_POSTER, title="<script>alert(1)</script>")
        rendered = render_poster(unsafe)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_invalid_model_layout_is_reported(self):
        invalid = dict(SAMPLE_POSTER, sections=[])
        with self.assertRaisesRegex(RuntimeError, "section layout"):
            PosterAgent._validate_content(invalid)


if __name__ == "__main__":
    unittest.main()
