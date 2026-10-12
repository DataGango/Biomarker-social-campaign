"""Generate validated poster content with an OpenAI-compatible chat API."""

from __future__ import annotations

import json
import os

import requests

from poster_agent.design.themes import THEMES
from poster_agent.prompt.templates import SYSTEM_PROMPT, build_user_prompt
from poster_agent.rendering.html_renderer import render_poster


DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
ALLOWED_THEMES = frozenset(THEMES)


class PosterAgent:
    def generate_childhood_cancer_preset(self) -> dict[str, object]:
        """Render a reviewed educational poster without requiring an LLM key."""
        poster = self._validate_content(
            {
                "title": "Childhood cancer is not one disease.",
                "subtitle": "Every diagnosis is different. Families deserve clear information and expert support.",
                "poster_type": "RESEARCH FIELD GUIDE",
                "audience": "For families and communities",
                "visual_metaphor": "A connected care path: learn, ask, decide together, and follow up.",
                "theme": "clinical",
                "sections": [
                    {
                        "heading": "Many diagnoses",
                        "body": "Childhood cancer includes distinct diseases. Age, cancer type, biology, risk group, and treatment response all matter.",
                        "bullets": ["One statistic cannot describe one child's outlook."],
                    },
                    {
                        "heading": "Use statistics with context",
                        "body": "NCI's U.S. estimates include 14,910 diagnoses among people ages 0–19 in 2024. This is a population estimate, not a personal prediction.",
                        "bullets": ["Survival figures describe groups diagnosed in earlier years."],
                    },
                    {
                        "heading": "Care is a conversation",
                        "body": "A pediatric oncology team can explain the diagnosis, testing, treatment options, clinical trials, and follow-up that apply to the child.",
                        "bullets": ["Ask what each result can and cannot tell you."],
                    },
                ],
                "call_to_action": "Bring your questions to your child's pediatric oncology team.",
                "sources": [
                    "NCI, Cancer in Children and Adolescents: cancer.gov/types/childhood-cancers/child-adolescent-cancers-fact-sheet",
                    "ACS, Childhood Leukemia Survival Rates: cancer.org/cancer/types/leukemia-in-children/detection-diagnosis-staging/survival-rates.html",
                    "Educational information only; not diagnosis, treatment advice, or an individual prognosis.",
                ],
            }
        )
        return {"poster": poster, "html": render_poster(poster), "generation_mode": "reviewed-template"}

    def generate(self, prompt: str) -> dict[str, object]:
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Enter a poster prompt first.")
        if len(prompt) > 1500:
            raise ValueError("Poster prompt must be under 1,500 characters.")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Set it in Biomarker/.env to use the poster agent.")

        response = requests.post(
            os.getenv("OPENAI_API_URL", DEFAULT_API_URL),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(prompt)},
                ],
            },
            timeout=90,
        )
        response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"]
            poster = self._validate_content(json.loads(content))
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("The poster model returned an invalid response. Please try again.") from error

        return {"poster": poster, "html": render_poster(poster), "generation_mode": "language-model"}

    @staticmethod
    def _validate_content(data: object) -> dict[str, object]:
        if not isinstance(data, dict):
            raise RuntimeError("The poster model returned an invalid response. Please try again.")

        def text_field(key: str, maximum: int, *, optional: bool = False) -> str:
            value = data.get(key, "")
            if not isinstance(value, str) or len(value) > maximum or (not optional and not value.strip()):
                raise RuntimeError(f"The poster model returned invalid {key} content. Please try again.")
            return value.strip()

        raw_sections = data.get("sections")
        if not isinstance(raw_sections, list) or not 2 <= len(raw_sections) <= 4:
            raise RuntimeError("The poster model returned an invalid section layout. Please try again.")
        sections = []
        for section in raw_sections:
            if not isinstance(section, dict):
                raise RuntimeError("The poster model returned an invalid section. Please try again.")
            bullets = section.get("bullets")
            if not isinstance(bullets, list) or not 1 <= len(bullets) <= 3:
                raise RuntimeError("The poster model returned invalid section bullets. Please try again.")
            if any(not isinstance(item, str) or not item.strip() or len(item) > 150 for item in bullets):
                raise RuntimeError("The poster model returned invalid bullet text. Please try again.")
            heading = section.get("heading")
            body = section.get("body")
            if not isinstance(heading, str) or not heading.strip() or len(heading) > 80:
                raise RuntimeError("The poster model returned an invalid section heading. Please try again.")
            if not isinstance(body, str) or len(body) > 220:
                raise RuntimeError("The poster model returned invalid section text. Please try again.")
            sections.append(
                {
                    "heading": heading.strip(),
                    "body": body.strip(),
                    "bullets": [item.strip() for item in bullets],
                }
            )

        theme = data.get("theme")
        if not isinstance(theme, str) or theme not in ALLOWED_THEMES:
            theme = "editorial"
        sources = data.get("sources", [])
        if (
            not isinstance(sources, list)
            or len(sources) > 6
            or any(not isinstance(item, str) or not item.strip() or len(item) > 180 for item in sources)
        ):
            raise RuntimeError("The poster model returned invalid source notes. Please try again.")

        return {
            "title": text_field("title", 90),
            "subtitle": text_field("subtitle", 180, optional=True),
            "poster_type": text_field("poster_type", 50, optional=True),
            "audience": text_field("audience", 70, optional=True),
            "visual_metaphor": text_field("visual_metaphor", 140, optional=True),
            "theme": theme,
            "sections": sections,
            "call_to_action": text_field("call_to_action", 140, optional=True),
            "sources": [item.strip() for item in sources],
        }
