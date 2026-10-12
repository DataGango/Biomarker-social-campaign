---
name: Publish Facebook Page Media
description: Preview and publish an approved Facebook Page photo or Reel through the protected official Graph API workflow.
argument-hint: Provide the exact Page ID/name, asset path, caption file, and whether this is a photo or Reel.
agent: Social Campaign Manager
---

Prepare and, only after approval, publish one Facebook Page photo or Reel using `.github/workflows/publish-facebook-page.yml`.

1. Confirm the exact Facebook Page ID and name from the user's supplied destination. Do not substitute a personal profile, Instagram account, or similarly named Page.
2. Select one committed media asset under `assets/` (`.jpg`, `.jpeg`, or `.png` for a photo; `.mp4` for a Reel) and one exact caption file under `assets/`. Inspect the media and verify every factual claim against the linked primary sources.
3. Present the exact Page name/ID, media type, asset path, title for a Reel, caption, Public audience behavior, and immediate timing. Ask the user to approve this exact post before any `PUBLISH` run. A daily-content plan is not blanket approval for future posts.
4. Dispatch a preview with `approval=NO` and confirm the workflow summary matches the Page, media, and caption. Preview makes no network request.
5. Only after the user's exact approval, dispatch a separate run with `approval=PUBLISH`. The publish job uses `facebook-production`; required reviewers must be configured in that GitHub Environment. Never bypass the reviewer gate.
6. Verify the returned Facebook Page post/photo ID or Reel video ID and the completed Actions run before claiming success. If a final API response is ambiguous, reconcile the Page/video ID before any retry. Never automatically retry a publish request.

The workflow needs the protected GitHub Actions secret `FB_PAGE_ACCESS_TOKEN` and the permissions `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`. If credentials, required permissions, Page identity checks, or a production reviewer are missing, stop at preview and state the exact blocker. Never ask for tokens in chat or publish using browser automation, cookies, or hidden endpoints.