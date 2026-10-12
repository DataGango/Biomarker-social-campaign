---
name: Deploy Dashboard Release
description: Run quality and security gates, then deploy the existing dashboard only to a specifically approved target.
agent: Dashboard Release Manager
argument-hint: Specify branch, preview/production target, hosting resource, public URL, and rollback owner.
---

Prepare and, only when explicitly authorized, deploy a release of the existing dashboard.

1. Confirm branch, preview or production environment, hosting target/resource, public URL, health endpoint, rollback owner, and whether deployment is authorized. Do not infer production approval from an ambiguous request.
2. Review the diff for `.env`, credentials, retrieved workspace files, local cache, private recipient data, and unauthorized media. Do not stage, commit, or push unless separately requested.
3. Run pytest/unittest, Playwright UI/API tests, Selenium smoke tests, dependency/security checks, and applicable frontend build checks. Stop on failures; do not skip or weaken gates to get a green result.
4. Build and identify the immutable artifact or container digest. Keep secrets out of command arguments, build args, logs, and artifacts.
5. Deploy production only after explicit approval for the named environment using configured protected reviewers and deployment credentials. Never bypass missing configuration.
6. Verify `/`, `/api/health`, `/api/status`, and a browser smoke path after deployment. Report success and the URL only when provider and health checks confirm it; include rollback guidance.
7. Do not publish a social announcement as a side effect. Use the separate social campaign prompt, present the exact copy/media/destination/audience/timing, and require separate approval before publishing.
