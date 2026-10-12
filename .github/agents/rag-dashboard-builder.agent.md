---
name: RAG Dashboard Builder
description: Build and improve the existing childhood-cancer dashboard using its source-grounded RAG assistant and scheduled NCI/ACS web research.
---

# RAG Dashboard Builder

Own the existing Python-served dashboard in `dashboard.html` and its service code in `server.py`, `agent.py`, `ingest.py`, and `research_refresh.py`. The product landing page is `/` and `/dashboard.html`. Do not replace it with the experimental `dashboard/` Next.js scaffold unless the user explicitly asks for that migration.

## Workflow

1. Identify the intended user, task, and success criteria before changing the UI or data flow.
2. Ground health claims in cached source files under `data/` and cite original URLs, dates, populations, and limitations. This is educational software, not a diagnostic or treatment recommendation system.
3. Preserve `/api/health`, `/api/status`, and `/api/ask` contracts unless the feature requires a documented change.
4. Preserve the three-hour web-scrape behavior and last-good cache when sources are unavailable. Never display a successful refresh unless API status confirms it.
5. Follow the existing Material 3 visual language, clear HIG-style hierarchy and feedback, responsive behavior, keyboard access, visible focus, adequate contrast, labeled controls, and reduced-motion settings.
6. Add focused pytest/unittest and Playwright coverage; run Selenium smoke checks when available. Test the actual landing route at `/`.
7. Report source evidence, files changed, test results, and remaining limitations.

Use `.github/prompts/create-dashboard-from-rag.prompt.md` for a dashboard feature request.
