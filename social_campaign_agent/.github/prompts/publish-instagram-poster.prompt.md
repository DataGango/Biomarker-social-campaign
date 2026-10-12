---
name: Publish Instagram Poster
description: Prepare any Instagram poster, review its exact post details, and trigger the protected publishing workflow after explicit approval.
argument-hint: Describe the poster topic or provide an assets/ JPEG and caption file, public image URL, and Instagram account alias.
agent: Social Campaign Manager
---

Prepare and, only after approval, publish one Instagram image post through the GitHub Actions workflow in `DataGango/social-media-agent`.

1. Identify the poster JPEG and its caption file. If the user asks to create a poster, create an original campaign asset in `assets/` and a matching `assets/<name>-caption.txt`. Keep poster files inside `assets/`; use `.jpg` or `.jpeg`. The caption file must contain a `Caption` section followed by exact post copy and an `Alt text` section with an accurate visual description. Verify factual claims and cite reliable sources in the caption where appropriate.
2. Confirm the public HTTPS image URL for this exact JPEG and the human-readable target Instagram account alias. The URL must be fetchable by Meta, end in `.jpg` or `.jpeg`, and contain no credentials, query parameters, or fragments. Never request or place a password, access token, or signed URL in chat. The workflow publishes immediately using the account's existing audience settings; it does not schedule posts.
3. Inspect the image and read the caption file. Present the exact poster asset, public image URL, account alias, audience behavior, immediate timing, caption, and alt-text handoff. State that the current API workflow sends the image and caption; alt text must be added manually in Instagram if the client offers that control. Ask the user to approve this exact post by replying `PUBLISH`. A general request to create a poster is not approval to post it.
4. Before triggering GitHub Actions, confirm the asset and caption are pushed to a branch and the workflow exists on the repository's default branch. Check `gh auth status`; if authentication or workflow access is missing, stop and give the precise setup blocker. Do not expose credentials.
5. Dispatch a preview-only run with `approval=NO` using `gh workflow run publish-instagram.yml --repo DataGango/social-media-agent --ref <branch> -f target_account_alias="<alias>" -f poster_asset_path="<assets path>" -f caption_file_path="<assets path>" -f public_image_url="<public HTTPS JPEG URL>" -f approval=NO`. Wait for that run to complete and inspect its summary. Correct any mismatch before proceeding.
6. Only after the user has explicitly replied `PUBLISH` for the exact preview, trigger a separate run with the same inputs and `-f approval=PUBLISH`. The publish job pauses at the protected `instagram-production` environment for a GitHub reviewer. Do not bypass this gate. Inspect the final run and report published only if Actions confirms success and returns an Instagram media ID.

If the poster is unavailable at a public URL, the caption or account alias is missing, user approval is absent, or any API prerequisite is incomplete, stop at preview/handoff. Never publish via browser automation, cookies, scraping, or an unapproved workflow run.
