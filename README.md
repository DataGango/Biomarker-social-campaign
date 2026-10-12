# Childhood Cancer Research Assistant

A local retrieval-augmented generation (RAG) assistant over the public source files in `data/`. It retrieves relevant passages, sends those passages to a configured OpenAI-compatible chat-completions endpoint, and returns an educational answer with source URLs. This uses an existing language model API; it does not train a new foundation model.

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

Open <http://127.0.0.1:8765/dashboard.html>. The server binds only to localhost and serves the dashboard, research brief, and ingested source files; it does not expose `.env` or Python source code.

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
