"""Task router and skill contracts for the local research multi-agent system."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


MAX_TEXT_LENGTH = 1500
TASKS = frozenset({"research_question", "poster_draft", "codebase_search", "campaign_draft"})
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class AgentSkill:
    """A narrow task contract, including its safety and evaluation criteria."""

    name: str
    description: str
    required_fields: tuple[str, ...]
    constraints: tuple[str, ...]
    eval_checks: tuple[str, ...]

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    skill: AgentSkill
    handler: Callable[[dict[str, Any]], dict[str, Any]]

    def public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "skill": self.skill.public_dict(),
        }


class AgentOrchestrator:
    """Route explicit task types to least-privilege handlers and retain traces."""

    def __init__(self, agents: list[AgentSpec]):
        self._agents = {agent.skill.name: agent for agent in agents}

    def list_agents(self) -> list[dict[str, object]]:
        return [agent.public_dict() for agent in self._agents.values()]

    def get_skill(self, task_type: str) -> AgentSkill:
        try:
            return self._agents[task_type].skill
        except KeyError as error:
            raise ValueError(f"Unknown task type: {task_type}") from error

    def run(self, task_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("Task payload must be an object.")
        agent = self._agents.get(task_type)
        if agent is None:
            raise ValueError(f"Unknown task type: {task_type}")
        missing = [field for field in agent.skill.required_fields if not payload.get(field)]
        if missing:
            raise ValueError("Missing required fields: " + ", ".join(missing))

        run_id = str(uuid.uuid4())
        trace = [{"event": "agent_started", "agent": agent.name, "task_type": task_type}]
        result = agent.handler(payload)
        trace.append({"event": "agent_completed", "agent": agent.name, "task_type": task_type})
        return {
            "run_id": run_id,
            "task_type": task_type,
            "agent": agent.name,
            "status": "completed",
            "result": result,
            "trace": trace,
        }

    def run_workflow(self, workflow: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a documented, sequential workflow with explicit hand-offs."""
        if workflow == "research_to_campaign_draft":
            research = self.run("research_question", {"question": payload.get("question", "")})
            campaign_payload = {
                "topic": payload.get("topic") or payload.get("question", ""),
                "audience": payload.get("audience", "Families and community members"),
                "platform": payload.get("platform", "general"),
                "sources": research["result"].get("sources", []),
                "evidence_summary": research["result"].get("answer", ""),
            }
            campaign = self.run("campaign_draft", campaign_payload)
            return {
                "workflow": workflow,
                "status": "completed",
                "steps": [research, campaign],
                "result": campaign["result"],
            }
        raise ValueError(f"Unknown workflow: {workflow}")


def _bounded_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text.")
    value = value.strip()
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"{key} must be at most {MAX_TEXT_LENGTH} characters.")
    return value


def _campaign_draft(payload: dict[str, Any]) -> dict[str, Any]:
    topic = _bounded_text(payload, "topic")
    audience = _bounded_text(payload, "audience")
    platform = _bounded_text(payload, "platform")
    evidence = payload.get("evidence_summary", "")
    if not isinstance(evidence, str):
        raise ValueError("evidence_summary must be text.")
    sources = payload.get("sources", [])
    if not isinstance(sources, list) or any(not isinstance(source, dict) for source in sources):
        raise ValueError("sources must be a list of source objects.")
    citations = [source for source in sources if isinstance(source.get("url"), str)]
    copy = (
        f"{topic}\n\n"
        "Childhood cancer includes many distinct diseases. Learn from reliable sources and bring personal "
        "questions about symptoms, tests, or treatment to a pediatric oncology team.\n\n"
        "Educational information only; not diagnosis, treatment advice, or an individual prognosis."
    )
    return {
        "status": "DRAFT / NEEDS REVIEW",
        "topic": topic,
        "audience": audience,
        "platform": platform,
        "copy": copy,
        "evidence_summary_for_review": evidence[:2000],
        "sources": citations,
        "publication": {"allowed": False, "reason": "Publishing requires separate approval of exact copy, asset, destination, audience, and timing."},
    }


def build_default_orchestrator(
    *,
    research_agent: Any | None = None,
    poster_agent: Any | None = None,
    workspace_root: str | Path | None = None,
) -> AgentOrchestrator:
    """Create the local system using the existing agents as bounded workers."""
    from agent import ChildhoodCancerAgent
    from codebase_agent.scanner import scan_workspaces
    from poster_agent.content.generator import PosterAgent

    root = Path(workspace_root or Path(__file__).resolve().parents[1]).expanduser().resolve()
    research_agent = research_agent or ChildhoodCancerAgent(root / "data")
    poster_agent = poster_agent or PosterAgent()

    def research_handler(payload: dict[str, Any]) -> dict[str, Any]:
        question = _bounded_text(payload, "question")
        return research_agent.answer(question)

    def poster_handler(payload: dict[str, Any]) -> dict[str, Any]:
        preset = payload.get("preset", "childhood-cancer")
        if preset != "childhood-cancer":
            raise ValueError("Only the reviewed childhood-cancer poster preset is enabled.")
        generated = poster_agent.generate_childhood_cancer_preset()
        return {
            **generated,
            "status": "DRAFT / NEEDS REVIEW",
            "alt_text": "A family-focused educational poster explaining that childhood cancer includes distinct diseases and encouraging questions for a pediatric oncology team.",
            "publication": {"allowed": False},
        }

    def codebase_handler(payload: dict[str, Any]) -> dict[str, Any]:
        topic = _bounded_text(payload, "topic")
        terms = payload.get("terms", [])
        if not isinstance(terms, list) or any(not isinstance(term, str) for term in terms):
            raise ValueError("terms must be a list of text values.")
        matches = scan_workspaces([root], topic, terms)
        # File contents are not returned; only bounded evidence excerpts leave the scanner.
        return {
            "workspace": str(root),
            "topic": topic,
            "match_count": len(matches),
            "matches": [
                {
                    "relative_path": item["relative_path"],
                    "path_terms": item["path_terms"],
                    "evidence": item["evidence"],
                }
                for item in matches[:100]
            ],
        }

    skills = [
        AgentSpec(
            "Research Assistant",
            "Answers childhood-cancer questions from the local source index with citations.",
            AgentSkill("research_question", "Source-grounded educational Q&A.", ("question",), ("No diagnosis or prescriptions.", "Cite indexed sources."), ("nonempty_answer", "source_ids_resolve")),
            research_handler,
        ),
        AgentSpec(
            "Poster Drafter",
            "Creates the reviewed childhood-cancer poster preset for human review.",
            AgentSkill("poster_draft", "Generate an accessible poster draft.", (), ("Draft only.", "Never publish."), ("draft_status", "publication_disabled", "has_alt_text")),
            poster_handler,
        ),
        AgentSpec(
            "Codebase Researcher",
            "Finds topic evidence in the configured project workspace without modifying source files.",
            AgentSkill("codebase_search", "Read-only topic search over the configured workspace.", ("topic",), ("Read-only scan.", "Do not return full file contents.", "Never scan outside the configured root."), ("evidence_has_paths", "secrets_not_returned")),
            codebase_handler,
        ),
        AgentSpec(
            "Social Campaign Drafter",
            "Creates a source-linked social draft package; it cannot publish or message.",
            AgentSkill("campaign_draft", "Prepare a reviewable campaign copy draft.", ("topic", "audience", "platform"), ("Draft only.", "No unsupported medical claim.", "Never publish or send."), ("draft_status", "publication_disabled", "contains_disclaimer")),
            _campaign_draft,
        ),
    ]
    return AgentOrchestrator(skills)