# Childhood Cancer Research Assistant

A local retrieval-augmented generation (RAG) assistant over the public source files in `data/`. It retrieves relevant passages, sends those passages to a configured OpenAI-compatible chat-completions endpoint, and returns an educational answer with source URLs. This uses an existing language model API; it does not train a new foundation model.

For the product overview, repository code map, architecture, configuration, agent protocols, safety boundaries, and known deployment gaps, see [Product and Technical Guide](PRODUCT_AND_TECHNICAL_GUIDE.md).

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. Do not commit `.env`; it is ignored by Git. `OPENAI_MODEL` and `OPENAI_API_URL` are configurable for compatible providers.

Refresh the public sources:

```sh
python ingest.py
```

The ingester records per-source failures and continues to the remaining pages. It downloads the ACS biomarker PDF and extracts the registered NCI/ACS pages into `data/`.

## Use the dashboard agent

```sh
python server.py
```

Open <http://127.0.0.1:8765/>. The dashboard links to the treatment-plan discussion guide, poster maker, and state-based pediatric cancer care directory. The care directory uses the live Children's Oncology Group member locator and links separately to NCI's broader cancer-center directory. The server binds only to localhost and does not expose `.env` or Python source code.

## Project Agents and Prompts

Repository-level VS Code agent roles are in `.github/agents/`, with reusable commands in `.github/prompts/`:

- **RAG Dashboard Builder** · `.github/prompts/create-dashboard-from-rag.prompt.md` creates source-grounded features in the existing `dashboard.html` landing page.
- **Current and Future Treatment Research** · `.github/prompts/research-current-and-future-childhood-cancer-treatment.prompt.md` separates established care from investigational directions and requires dated source citations; it does not create an individual treatment plan.
- **Social Campaign Creator** · `.github/prompts/create-social-campaign.prompt.md` prepares verified, platform-specific drafts and assets for review.
- **Childhood Cancer Awareness Poster** · `.github/prompts/create-childhood-cancer-awareness-poster.prompt.md` creates a family-focused, source-grounded poster draft and explicitly does not publish it.
- **Dashboard Release Manager** · `.github/prompts/deploy-dashboard-release.prompt.md` runs quality/security gates and deploys only to a specifically approved target.

Production deployment and social publication are separate gated actions. Campaign and deployment prompts require explicit approval of the exact content, destination, and environment; the prompts do not create credentials or authorize publication by themselves.

## Multi-Agent Runtime, MCP, and A2A

The shared in-process orchestrator exposes bounded task types for source-grounded research, a reviewed poster draft, read-only codebase search, and campaign drafts. It has no task that publishes, schedules, sends messages, diagnoses, or prescribes.

Start the MCP stdio server for a local MCP client:

```sh
python -m multi_agent.mcp_server
```

Start the A2A 1.0 JSON-RPC agent service separately:

```sh
python -m multi_agent.a2a_server
```

The A2A Agent Card is available at `http://127.0.0.1:8767/.well-known/agent-card.json`. The dashboard HTTP API exposes `GET /api/agents`, `POST /api/agents/run`, and `POST /api/agents/workflow` when `server.py` is running.

## Free Hosting

The static childhood-cancer field guide is already published at <https://datagango.github.io/Biomarker/>. The Python dashboard is a separate application; GitHub Pages cannot run its Python server or API. A Render free-tier blueprint is provided in `render.yaml` for the dashboard service. To deploy it, sign in to Render, create a Blueprint from this repository/branch, review the `biomarker-research-dashboard` service, and deploy. The blueprint disables automatic deploys; trigger a deploy from Render after reviewing changes.

The free service starts without `OPENAI_API_KEY`, so the static dashboard, research index refresh, codebase search, and offline reviewed poster preset can run, but LLM-backed answers and custom poster generation remain unavailable. Do not add an API key until authentication and abuse/rate-limit protection are in place. Render's free filesystem is ephemeral and free services may sleep; refreshed source cache is not guaranteed to persist across restarts. MCP stdio is local-process only, and A2A is a separate service not included in this single-service blueprint. A Render account and user authorization are required to create the hosted service; repository configuration alone does not deploy it.

Run the deterministic offline evals and agent/protocol tests:

```sh
python -m multi_agent.run_evals
python -m unittest tests.test_multi_agent tests.test_multi_agent_protocols -v
```

The eval CLI injects a fixed research fixture and does not require model credentials or network access. All generated poster and campaign content remains `DRAFT / NEEDS REVIEW` until separately approved.

## Use the prompt-driven poster agent

While the server is running, open <http://127.0.0.1:8765/poster-agent/>. Describe the poster's purpose, topic, audience, tone, and required details. The agent creates a themed, single-page HTML poster that can be downloaded for editing or printed/saved as an A3 PDF. It uses the same `OPENAI_API_KEY`, `OPENAI_MODEL`, and `OPENAI_API_URL` settings as the research assistant.

The poster agent is divided by function in `poster_agent/`:

- `prompt/` builds the model instructions and packages the user's brief.
- `content/` calls the configured model and validates its structured response.
- `design/` provides safe, built-in visual themes.
- `rendering/` turns validated content into a self-contained printable HTML poster.
- `ui/` contains the browser prompt form, preview, and download/print controls.
- `tests/` covers prompt validation, model response checks, and safe rendering.

Review dates, names, statistics, and other factual details before sharing generated material. Include exact facts and source notes in the prompt when they need to appear; the agent does not independently verify generated claims.

Ask a question in the dashboard. Retrieved source passages are provided to the LLM, and the answer is instructed to cite sources and avoid diagnosis, treatment recommendations, or individual prognosis. Verify medical decisions with a qualified pediatric oncology team.

CLI:

```sh
python agent.py "What factors affect childhood leukemia survival rates?"
```

Run offline tests (no API key or live API calls needed):

```sh
python -m unittest -v
python -m unittest poster_agent.tests.test_poster_agent -v
```
