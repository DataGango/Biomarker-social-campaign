---
name: Social Campaign Creator
description: Create source-verified, platform-specific social campaigns and ready-to-review assets from approved project research.
---

# Social Campaign Creator

Use the bundled campaign files under `social_campaign_agent/`. Create drafts and campaign assets; do not publish, schedule, message, or announce anything without separate explicit approval of the exact copy, media, destination, audience, and timing.

## Workflow

1. Gather the topic, objective, audience, requested platforms, account/Page identity, language, tone, and dates/timezone. Draft and mark assumptions if details are missing.
2. Verify health and science claims against primary or official sources. Preserve publication dates, evidence stage, population, and limitations. Never claim experimental work is an available treatment.
3. Adapt copy and creative requirements per platform; include exact captions, citations, accessible alt text, CTA, and health disclaimers where appropriate.
4. Report real platform coverage: Facebook Page photo/Reels and Instagram poster/Reels have bundled publisher code; LinkedIn member posting has bundled local `PUBLISH` confirmation; WhatsApp has no sender and remains draft-only.
5. Run relevant mock tests. Do not contact platform APIs or publish in a draft-generation task.
6. Protect tokens, recipient details, and private media URLs. Never use browser automation, scraping, or undocumented endpoints to publish.

The workflow files under `social_campaign_agent/.github/workflows/` are nested reference copies. GitHub Actions only runs files under root `.github/workflows/`; do not claim a nested workflow is active in this repository.

Use `.github/prompts/create-social-campaign.prompt.md` for campaign creation.
