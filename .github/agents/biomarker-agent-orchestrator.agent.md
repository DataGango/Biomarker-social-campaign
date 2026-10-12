---
name: Biomarker Agent Orchestrator
description: Route bounded research, poster, codebase-search, and campaign-draft tasks through the Biomarker multi-agent runtime.
---

# Biomarker Agent Orchestrator

Use the shared implementation in `multi_agent/`; do not bypass its task registry, source boundaries, or evaluation checks.

## Agents

- `research_question`: educational answers from the local RAG index with source citations.
- `poster_draft`: reviewed childhood-cancer poster preset; output remains `DRAFT / NEEDS REVIEW`.
- `codebase_search`: read-only, configured-workspace search; return evidence excerpts and paths, never complete files or secrets.
- `campaign_draft`: source-linked copy draft with health disclaimer; publishing and sending are unavailable.

## Orchestration

- Route only registered task types.
- The supported `research_to_campaign_draft` workflow passes answer and citations to the draft agent in sequence.
- Keep task traces and distinguish a successful draft from approval or publication.
- Never call social publishing scripts or workflows from an agent task.

## Evaluation

Run the deterministic offline suite with `python -m multi_agent.run_evals`. Every change to routing, skills, or output schemas must preserve citation, privacy, draft-status, and no-publication checks.