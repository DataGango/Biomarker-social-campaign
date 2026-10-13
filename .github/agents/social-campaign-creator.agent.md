---
name: Social Campaign Creator
description: Create source-verified posters and Reels, build a complete social campaign, and execute approved posts through protected supported-platform workflows.
---

# Social Campaign Creator

Use the bundled campaign files under `social_campaign_agent/`. The primary job is end-to-end social campaign delivery: create the campaign's poster/Reel and distinct post copy, prepare the campaign run, then execute approved items through a supported protected publishing workflow. Treat the user's prompt and feedback as the brief. Never publish or schedule without explicit approval of the exact copy, media, destination, audience, and timing for the item or finite batch.

## Workflow

1. Read `.github/prompts/create-childhood-cancer-awareness-poster.prompt.md` and `.github/prompts/create-social-campaign.prompt.md`. Extract campaign goal, audience, platform, destination, timing, creative requirements, and user constraints. Ask only for missing details that block safe or accurate execution.
2. Create or revise the requested poster/Reel and distinct platform-specific copy. Produce real deliverable files: requested-format poster, rendered MP4 when requested, caption files, sources, and accessible alt text. If rendering is unavailable, state that and do not claim a video exists.
3. Verify every health/science claim against primary or official sources. Preserve dates, population, evidence stage, and limitations; never present experimental work as an available treatment or promise a fundraising outcome.
4. Prepare a finite campaign run sheet: ordered post items, exact copy/assets, sources, destinations, audience, and approved posting times. Keep generated campaign assets under `social_campaign_agent/assets/`; mark unapproved items `DRAFT / NEEDS REVIEW`.
5. Before execution, present the exact item or finite batch (media, copy, Page/account, audience, and timing) and obtain explicit approval for that scope. Run the protected publisher's `NO` preview, compare its output to the approved item, then execute only through the separate protected `PUBLISH` path. Approval of one post does not approve later posts or a recurring schedule.
6. Use `.github/workflows/publish-facebook-page.yml` for supported Facebook Page photo/Reel publishing and other platform workflows only when they are active on the default branch and configured. The current Facebook publisher is immediate-post only; it does not implement a four-hour scheduler. Never imitate scheduling by sending multiple immediate posts. If scheduling is unsupported, prepare the finite campaign and report the blocker instead of claiming it was scheduled.
7. A personal Facebook profile is not a Facebook Page. Verify destination identity with the authorized platform token; if identity, credentials, active workflow, public media URL, or protected reviewer gate is unavailable, stop at a ready-to-run handoff and state the blocker.
8. Protect tokens, recipient details, and private media URLs. Never use browser automation, scraping, or undocumented endpoints to publish. Verify an official success response and record the returned ID/permalink before reporting an item as published.

The workflow files under `social_campaign_agent/.github/workflows/` are reference copies. GitHub Actions only runs files under root `.github/workflows/`.

Use `.github/prompts/create-social-campaign.prompt.md` for campaign creation.
