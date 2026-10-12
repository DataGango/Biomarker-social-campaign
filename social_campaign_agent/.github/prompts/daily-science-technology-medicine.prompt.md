---
name: Daily Science, Technology and Medicine
description: Create a source-verified daily draft queue and route each approved item through a supported protected publisher.
argument-hint: Provide campaign dates, timezone, audience, language, and any topic priorities.
agent: Social Campaign Manager
---

Prepare a recurring daily content queue for science, technology, and medicine. Default to seven consecutive daily drafts unless the user specifies another horizon. Ask only for missing details that materially change content or destination; otherwise state assumptions and proceed.

## Editorial Checks

1. Rotate foundational science, current discoveries, technology, and evidence-based medicine. Avoid repeating the same topic and creative format on consecutive days.
2. Verify timely claims against primary sources: original research, official scientific/public-health institutions, trial registries, standards bodies, and official award/regulator pages. Record source URLs and publication or announcement dates.
3. Separate evidence from interpretation. Do not exaggerate causality, clinical readiness, or early/preclinical findings. Medical posts are general education, never personalized medical advice.
4. Include citations in the caption or visual when the format allows, accessible alt text for images, and readable captions/on-screen text for video.
5. Use only original or properly licensed media/audio. Never claim a Reel was created unless its actual video file has been rendered and checked.

## Daily Queue

For every date, provide the pillar, topic, audience, platform, exact caption, media asset or timed Reel storyboard, source list tied to its claims, alt text where applicable, timezone, and status. Use only these statuses: `DRAFT`, `NEEDS REVIEW`, `APPROVED`, `PREVIEW PASSED`, `PUBLISHED`, `BLOCKED`.

Maintain a non-secret ledger with date, topic, Page/account destination, asset and caption paths, sources, approval state, workflow run, and returned post ID/permalink. Do not store tokens, signed media URLs, or credentials in the ledger.

## Posting Rules

- Each item requires separate approval of its exact text, media, destination, audience, and timing. Never treat the daily cadence as approval to auto-publish future posts.
- Facebook Page photos and Reels use `/publish-facebook-page` and `.github/workflows/publish-facebook-page.yml`; preview with `NO`, then use `PUBLISH` only for the approved item. The `facebook-production` environment must require reviewers.
- Instagram posters and Reels use their existing protected Instagram workflows and the exact approved Instagram account alias. Do not route Facebook Page posts through Instagram.
- LinkedIn member posts use `publish_linkedin.py` with its local confirmation.
- If a destination's official integration, permission, or reviewer gate is not configured, mark that item `BLOCKED` and provide a handoff. Do not switch platforms or use browser automation to bypass the missing route.

End with a seven-day overview showing source/asset readiness, per-item approval state, supported destination, and the next action. No scheduled or automatic publish unless a supported scheduler is separately implemented and every item has the required approval.