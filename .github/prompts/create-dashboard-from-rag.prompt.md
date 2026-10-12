---
name: Create Dashboard Feature from RAG
description: Implement a user-requested dashboard page or feature using the existing childhood-cancer RAG service and trusted sources.
agent: RAG Dashboard Builder
argument-hint: Describe the dashboard page or feature, audience, and approved source material.
---

Implement the requested feature in the existing Python-served dashboard.

1. Inspect `dashboard.html`, `server.py`, `agent.py`, `ingest.py`, `research_refresh.py`, relevant tests, and `data/` sources before editing. The existing dashboard at `/` is the landing page.
2. Keep claims source-grounded. Cite original NCI/ACS or primary research URLs and retain dates, populations, and limitations. Do not provide individual diagnosis, prognosis, screening direction, or a personalized treatment plan.
3. Follow Material Design 3 visual roles, HIG-style hierarchy and feedback, and WCAG 2.2 keyboard, focus, contrast, semantic, form-label, responsive, and reduced-motion expectations.
4. Preserve `/api/health`, `/api/status`, `/api/ask`, and the three-hour refresh contract unless the requested feature requires a deliberate, tested API change.
5. Failed scrapes must not erase the last good cache/index. Do not claim a source refreshed unless status confirms it.
6. Add focused tests, then run the Python suite and Playwright tests against `/`. Run Selenium smoke tests when configured.
7. Report implementation, evidence sources, tests, accessibility/responsive checks, and unresolved limitations.
