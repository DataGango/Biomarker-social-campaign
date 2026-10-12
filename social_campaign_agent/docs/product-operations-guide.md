# Daily Science, Technology and Medicine Social Program

## Product Purpose

The Social Campaign Manager turns a daily science, technology, and medicine topic into source-checked, platform-ready copy and media. It maintains an auditable draft/publishing trail and routes approved content only through platform integrations that are actually configured. It is an editorial and publishing assistant, not an autonomous medical adviser or a general-purpose mass-messaging service.

## Product Outcomes

- Deliver one distinct, useful draft per planned day across rotating science, technology, and evidence-based medicine topics.
- Ground every material factual statement in direct, inspectable sources; prefer primary research, official institutions, regulators, and official prize/announcement sources.
- Adapt the same evidence to each platform's format rather than blindly cross-posting identical content.
- Preserve a human review step for every exact post: copy, asset, target account/Page, audience, timing, citations, and any health disclaimer.
- Record preview and publication evidence, including workflow run URL and returned media/post/message ID.

## Daily Operating Cycle

1. Open `.github/prompts/daily-science-technology-medicine.prompt.md` with the Social Campaign Manager.
2. Set the content dates, timezone, audience, language, subject priorities, and supported destinations. If dates or timezone are omitted, the agent marks the assumption rather than silently scheduling.
3. Generate the requested daily queue. Each entry contains a topic, angle, exact caption, media/storyboard, alt text when relevant, citations, status, and next action.
4. Check the sources and creative. Verify publication dates and attribution, ensure the creative makes no unsupported clinical promise, and inspect any rendered image/video.
5. Approve each post separately. A standing request for daily drafts or an automatic workflow does not approve future posts.
6. Run the supported publisher's preview with `NO`. Confirm the destination, audience, caption, asset path, and source list match the approval.
7. For an exact item approved to publish, use the separate `PUBLISH` run and satisfy the platform's protected-environment review.
8. Record the resulting workflow URL, post ID/permalink, date/time, and status in the campaign ledger. If the result is ambiguous, reconcile it before retrying.

Allowed ledger statuses: `DRAFT`, `NEEDS REVIEW`, `APPROVED`, `PREVIEW PASSED`, `PUBLISHED`, `BLOCKED`.

## Platform Matrix

| Platform | Current mechanism | Content supported | Status / constraints |
| --- | --- | --- | --- |
| Facebook Page | `.github/workflows/publish-facebook-page.yml` and `scripts/publish_facebook_page.py` | Page photo posts and Page Reels | Implemented; preview and mock tests pass. Live publication remains blocked until Page token and protected environment/reviewer settings are configured. Page Reels are Public and capped by Meta at 30 API-published Reels per rolling 24 hours. |
| Instagram | `.github/workflows/publish-instagram.yml`, `.github/workflows/publish-instagram-reel.yml`, `scripts/publish_instagram.py`, and `scripts/publish_instagram_reel.py` | JPEG feed poster and hosted MP4 Reel | Implemented with target-account checks, preview-first behavior, protected environment, and returned media ID/permalink verification. Requires eligible professional account, current Meta permissions, credentials, and publicly fetchable hosted media. |
| LinkedIn | `publish_linkedin.py` and `linkedin_publisher.py` in the separate local `social-media` workspace | Member text or image post | Implemented in that local workspace using LinkedIn REST APIs and local `PUBLISH` confirmation; not part of this GitHub repository's Actions deployment. Requires an authorized member token and `w_member_social`; do not claim it is deployed from this repo. |
| WhatsApp | No publisher in this repository | Business-initiated or service messages, not public feed posts | Not implemented. Requires WhatsApp Business Platform Cloud API onboarding, WABA/phone number, approved templates when outside the customer-service window, documented opt-in, protected credentials, webhook verification/status handling, rate/quality controls, and recipient authorization. Do not broadcast daily content to contacts without opt-in. |

## Exact Platform Workflows

### Facebook Page Photo or Reel

1. Confirm the Page name and numeric Page ID. The Page access token is checked against both so it cannot accidentally post to a different Page.
2. Store the selected photo (`.jpg`, `.jpeg`, `.png`) or Reel (`.mp4`) and caption (`.txt`) under `assets/`.
3. Open Actions → **Publish Facebook Page Post**, choose `photo` or `reel`, enter the Page ID/name, asset/caption paths, and leave approval at `NO`.
4. Inspect the completed preview. It must show the expected Page, Public audience, immediate timing, correct asset, and exact caption.
5. After approval of that exact post, dispatch again with `PUBLISH`. GitHub pauses the publish job at `facebook-production`; a configured reviewer must approve it.
6. Confirm a Page post/photo ID or Reel video ID in the Action summary. For a Reel, Meta processing must be complete before finalization. Do not retry ambiguous results without reconciling the Page first.

Required GitHub configuration is described in the [technical operations guide](technical-architecture-and-runbook.md#github-actions-setup). Facebook Page Reels cannot use a Friends audience through this API.

### Instagram Poster or Reel

1. Prepare a JPEG for the poster or a hosted MP4 for the Reel, plus the exact caption file.
2. Dispatch the matching Instagram workflow with `NO`, then inspect its summary and exact Instagram username.
3. Only after per-post approval run with `PUBLISH`. The `instagram-production` environment review gate must be satisfied.
4. Confirm Meta reports the media ID and, when returned, permalink. Do not resend after an uncertain response before checking the media ID/status.

Poster image URLs must be publicly fetchable HTTPS JPEGs without credentials or signed query parameters. Reel MP4 URLs must also be publicly fetchable and checked against the approved asset hash by the workflow.

### LinkedIn Member Post

The local `social-media` workspace script previews the signed-in member, public audience, exact caption, and media. It requires the operator to type `PUBLISH` locally. It is not an Actions integration in this repository. Keep its `.env` credentials local and ignored.

1. In `/Users/poulomigangopadhyay/social-media`, configure `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN` (optional), and `LINKEDIN_VERSION` in the ignored `.env`. The LinkedIn app must have `w_member_social`; automatic author lookup also needs the OIDC `openid` and `profile` scopes.
2. Save the exact post text to a local UTF-8 file and inspect the chosen image/alt text.
3. Run `python publish_linkedin.py --text-file path/to/caption.txt [--image path/to/image.jpg --alt-text "Description"]` from that workspace.
4. Verify the preview names the correct member and public audience. Type `PUBLISH` locally only for that exact post. The script reports a post ID and URL on success.

### WhatsApp Business Message

WhatsApp is a private messaging channel, not the same product as posting to a Page/feed. Before an implementation is built, define the audience/recipient source, explicit opt-in capture and withdrawal process, the approved template/message category, message cadence, support handoff, and webhook retention policy. Outside a user's 24-hour customer-service window, use an approved template. Delivery is confirmed by webhooks, not merely by the API accepting a send request. Until a compliant Cloud API integration and recipient consent are configured, mark WhatsApp items `BLOCKED` and deliver copy as a draft only.

For an eventual Cloud API implementation, the official send endpoint has this shape (example only; this repository does not send it):

```http
POST https://graph.facebook.com/{version}/{phone-number-id}/messages
Authorization: Bearer {protected-token}
Content-Type: application/json
```

```json
{
	"messaging_product": "whatsapp",
	"recipient_type": "individual",
	"to": "+15555550123",
	"type": "text",
	"text": { "body": "Approved, opted-in message text" }
}
```

In production, recipient consent and opt-out state must be checked before the API call. Outside the 24-hour service window, replace the free-form text payload with a Meta-approved template payload. Store the returned `wamid`, then await a signed/verified webhook status (`sent`, `delivered`, `read`, or `failed`) before recording the delivery result. Never use this sample to message a real recipient without explicit opt-in and platform setup.

## Optogenetics Launch Item

The initial package is in `assets/`:

- Poster: `assets/optogenetics-facebook-page-poster.jpg`
- Reel: `assets/optogenetics-facebook-page-reel.mp4`
- Exact caption and references: `assets/optogenetics-facebook-page-caption.txt`
- Preview/publication status: `assets/optogenetics-facebook-page-publishing-status.md`

The material says the model concerns selected opsin-expressing cells, not whole-brain control or treatment, and includes the official 2026 Nobel Prize and Boyden et al. (2005) citations. GitHub Actions preview runs succeeded: poster `38190505401`, Reel `38190596917`; neither preview published anything.

## Editorial and Health Safeguards

- No invented breakthroughs, prizes, approvals, efficacy, endorsements, or performance metrics.
- Distinguish preclinical, observational, and clinical evidence; do not turn correlation into causation.
- For health topics, include scope/limitations and direct readers to a clinician for personal concerns; never diagnose or prescribe in social copy.
- Do not include identifiable patient/recipient data in creative assets or captions.
- Use only owned, user-provided, or properly licensed visuals and audio; preserve attribution where required.
- Keep tokens, app secrets, Page access tokens, private contact lists, and signed asset URLs out of prompts, files, and logs.