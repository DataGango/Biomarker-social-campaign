# Optogenetics Facebook Page Publishing Status

## Target and reviewed content

- Facebook Page: CHILD & HOPE
- Page URL: https://www.facebook.com/profile.php?id=61595341701921
- Page ID: 61595341701921
- Audience: Public Page audience
- Timing: published immediately through the native Facebook Page Reel composer on 2026-10-12
- Photo: `assets/optogenetics-facebook-page-poster.jpg`
- Reel: `assets/optogenetics-facebook-page-reel.mp4`
- Caption: `assets/optogenetics-facebook-page-caption.txt`
- Reel title: `Optogenetics: Focused Light, Selected Neurons`
- Reel format: 1080x1920 H.264 MP4, 20 seconds, with AAC narration summarizing excitatory/inhibitory opsin responses

## Preview evidence

- Photo preview run: https://github.com/DataGango/social-media-agent/actions/runs/38190505401
- Reel preview run: https://github.com/DataGango/social-media-agent/actions/runs/38190596917
- Both preview jobs succeeded with approval `NO`; the summaries match the Page ID/name, Public audience, selected media, and cited caption. The publisher states preview made no network requests.
- Poster SHA-256: `c56ba4b3579a3c612ae496ef87c3bcc0e30f3071da02f9a17457097cb960f755`
- Reel SHA-256: `b89930589df981594a49a8aa9982c55ce5900d92e396fca8163bbc4af69936a7`

## Publication state and blocker

The optogenetics poster was published earlier and confirmed at photo ID `122097940011511390`: https://www.facebook.com/photo/?fbid=122097940011511390&set=pb.61595341701921.-2207520000

The updated robotic-console Reel was published through the authenticated native Page composer. Facebook confirmed: “Your Post is successfully shared with EVERYONE.” Facebook then reported that the post is being processed and will be viewable when ready. A stable permalink or Reel ID was not available at confirmation time.

The GitHub Actions API publisher remains separately unconfigured: `facebook-production` does not exist, and `FB_PAGE_ACCESS_TOKEN` has not been configured or verified. The two recorded Actions runs were preview-only (`NO`) and made no network requests. Do not confuse those previews with the confirmed native Page publication.

To enable future API-based publishing, configure the `facebook-production` environment with required reviewers and add a valid Page access token as the `FB_PAGE_ACCESS_TOKEN` repository secret. The Meta app/token must have `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`, with Page content creation access. Do not paste the token into chat, the repo, CLI arguments, or a URL.

After configuration, inspect the exact preview for a separate photo or Reel request, approve that specific item, then dispatch with `PUBLISH`. Verify the returned Page post/photo ID or video ID before claiming success. Never retry an ambiguous final request without first reconciling the returned ID against the Page.