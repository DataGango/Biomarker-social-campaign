"""Run the offline multi-agent evaluation cases."""

from __future__ import annotations

import json
from pathlib import Path

from multi_agent.evals import load_eval_cases, run_eval_suite
from multi_agent.orchestrator import build_default_orchestrator


class _EvalResearchAgent:
    def answer(self, question: str) -> dict[str, object]:
        return {
            "answer": "This offline fixture treats childhood cancer as a group of distinct diseases [S1].",
            "sources": [{"id": "S1", "url": "https://www.cancer.gov/types/childhood-cancers/child-adolescent-cancers-fact-sheet"}],
        }


def main() -> int:
    workspace_root = Path(__file__).resolve().parents[1]
    orchestrator = build_default_orchestrator(
        research_agent=_EvalResearchAgent(),
        workspace_root=workspace_root,
    )
    report = run_eval_suite(orchestrator, load_eval_cases())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
