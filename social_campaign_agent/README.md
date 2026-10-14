# Protected Social Publishing Pipelines

Product workflow and capability matrix: [Product Operations Guide](docs/product-operations-guide.md). System design, code map, environment setup, and recovery runbook: [Technical Architecture and Operations Runbook](docs/technical-architecture-and-runbook.md).

## Daily Science, Technology and Medicine

Use `.github/prompts/daily-science-technology-medicine.prompt.md` with the Social Campaign Manager to prepare a rotating, source-verified daily draft queue. It creates captions/storyboards and a non-secret ledger; it does not auto-publish. Every item requires approval of its exact text, media, destination, audience, and timing.

## Facebook Page Photos and Reels

Use the repository-root `.github/workflows/publish-facebook-page.yml` for approved Facebook Page image posts and Reels. GitHub Actions only discovers workflows under the root `.github/workflows/` directory; this package contains the publisher implementation and tests, not a second workflow copy. The workflow has a no-network `NO` preview job and a separate `PUBLISH` job that uses the protected `facebook-production` environment. Configure that environment with required reviewers before publishing.

Required GitHub configuration:

- Secret `FB_PAGE_ACCESS_TOKEN`: Page access token for a person who can create Page content. Never put token values in source control, workflow inputs, URLs, or chat.
- Secret `FB_APP_ACCESS_TOKEN`: Meta app access token used by the protected preflight to inspect Page-token validity and granted scopes through the token-debug endpoint. Never put token values in source control, workflow inputs, URLs, or chat.
- Variable `FB_GRAPH_API_VERSION`: a currently supported Graph API version (the workflow defaults to `v26.0`).
- Environment `facebook-production`: configure required reviewers.
- Variable `FB_PRODUCTION_REVIEW_GATE`: set to `enabled` only after verifying the environment's required reviewers are configured. The publish job fails closed otherwise.
- The protected `VERIFY` mode checks token validity and the `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts` scopes using the app access token, then resolves the Page token to the exact approved Page ID and name. It does not upload media or create a post. `PUBLISH` repeats all checks before upload.

If `verify_page` fails with HTTP 401 / OAuth code 190 during the token-debug request, Meta rejected the authenticating `FB_APP_ACCESS_TOKEN`, not necessarily the Page token being inspected. Replace that secret in the protected `facebook-production` environment with a valid app access token for the Meta app that issued the Page token. If the debugger reports an invalid/expired Page token, or Page identity verification rejects `FB_PAGE_ACCESS_TOKEN`, replace the Page secret with a current token for the approved Page and required permissions. After updating credentials, start a new workflow dispatch with the same destination/assets and `approval=VERIFY`; retries of the original run are intentionally disabled. Do not bypass verification or dispatch `PUBLISH` to test credentials.

Photo posts use Meta's official `/{page-id}/photos` endpoint. Reels use the Page Reels Publishing API: initialize, upload to the returned `rupload.facebook.com` URL, poll processing status with a bounded wait, and finish only when ready. Page Reels are Public and limited by Meta to 30 API-published Reels per rolling 24 hours. The workflow is manual-dispatch only; a daily draft cadence does not enable unattended publication. Do not retry an ambiguous final publish request before reconciling the returned Page post or video ID.

Official docs: [Page Photos](https://developers.facebook.com/docs/graph-api/reference/page/photos/), [Reels Publishing API](https://developers.facebook.com/docs/video-api/guides/reels-publishing/), [Permissions](https://developers.facebook.com/docs/permissions/).

## Instagram Poster Publishing

### Publish Any Poster

The reusable `/publish-instagram-poster` prompt prepares a post and triggers `.github/workflows/publish-instagram.yml` through GitHub Actions. The workflow accepts any JPEG poster and caption file checked into `assets/`, plus its matching publicly fetchable image URL. It uses Meta's official Instagram Graph API and publishes immediately; it does not schedule posts. The account's existing audience/privacy settings apply.

The workflow is fail-closed. A `NO` run previews the target alias, selected asset, and caption without network requests. A `PUBLISH` run waits at the protected `instagram-production` GitHub Environment before calling Meta. Configure that Environment with required reviewers. Never enable publishing until a reviewer can inspect the exact post. The access token is supplied only as a GitHub Actions secret and is never printed.

### Required GitHub Configuration

Configure these repository settings before running with `PUBLISH`:

- Secret `IG_ACCESS_TOKEN`: valid Instagram User access token for the Meta app and account, granted `instagram_business_basic` and `instagram_business_content_publish`. For compatibility with the existing deployment environment, `CAMPAIGN123` is accepted as a fallback secret name. The workflow resolves the Instagram professional account ID through Meta's `/me?fields=user_id,username` endpoint and verifies it matches the target alias before upload. Never put token values in source control or chat.
- Public image URL: preview-only workflow dispatches may leave this blank. A publish run requires a public HTTPS URL for the selected JPEG. It must be fetchable by Meta, end in `.jpg` or `.jpeg`, and have no query parameters or credentials. Private-repository raw links and local paths will not work. Never use a signed URL or put a token in the URL.
- Repository variable `IG_GRAPH_API_VERSION`: supported version in the form `vNN.N` (for example, `v25.0`); keep it current with Meta's supported versions.

Meta's current [Content Publishing documentation](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing/) requires a JPEG image URL. The publisher rejects PNG URLs before making any request. Host the selected JPEG at a stable, publicly fetchable HTTPS URL before dispatching the workflow.

The Meta app must use Instagram API with Instagram Login, target an eligible Business or Creator professional account, and grant `instagram_business_basic` and `instagram_business_content_publish` to the token. Complete any app review/access-level requirements for the intended account, keep the token valid, and complete Page Publishing Authorization if Meta requires it. Meta may reject publishing if account, app, token, permissions, media, or rate-limit prerequisites are not met.

The workflow and prompt must be merged to the repository's default branch before the agent can trigger them. Add poster JPEGs and matching caption files under `assets/`; the caption file format is `Caption`, the exact post copy, `Alt text`, and a visual description. In GitHub Actions, choose **Publish Instagram poster**, enter the poster and caption paths and target account alias. You may leave the public JPEG URL blank for the first preview; the summary explicitly marks publishing blocked until a valid public URL is supplied. Only after you explicitly approve the exact post should the agent dispatch a separate `PUBLISH` run with the public URL; the protected Environment then requires reviewer approval before the API call. Add required reviewers to the `instagram-production` Environment in repository settings. The publisher creates a media container, polls its status at bounded intervals, and calls `media_publish` only after Meta reports `FINISHED`.

The Instagram publishing endpoint sends the image and caption. It does not apply the caption file's alt-text field; add that text manually in Instagram after publishing if the client/API does not expose alt-text support.

### Local Tests

Run the mock-only tests without Instagram credentials or network access:

```sh
python -m unittest discover -s tests -v
```