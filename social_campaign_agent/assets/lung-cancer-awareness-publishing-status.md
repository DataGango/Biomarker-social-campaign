# Lung Cancer Awareness Campaign

Status: DRAFT / BLOCKED pending destination identity, exact-post approval, and configured workflow access.

## Campaign files

- Editable original artwork: `assets/lung-cancer-awareness-poster.svg`
- Instagram JPEG (1080 x 1350): `assets/lung-cancer-awareness-instagram-poster.jpg`
- Instagram caption and alt text: `assets/lung-cancer-awareness-instagram-caption.txt`
- Facebook JPEG (1200 x 1500): `assets/lung-cancer-awareness-facebook-poster.jpg`
- Facebook caption: `assets/lung-cancer-awareness-facebook-caption.txt`

## Evidence notes

- CDC states annual LDCT screening is recommended for adults ages 50-80 with at least a 20 pack-year smoking history who currently smoke or quit within the past 15 years. Source page: https://www.cdc.gov/lung-cancer/screening/index.html (page dated May 12, 2026).
- CDC describes false-positive results, unnecessary follow-up tests or surgeries, overdiagnosis, and radiation as screening risks. Same source.
- NCI's patient PDQ states LDCT screening reduced lung-cancer mortality in studied heavy smokers and describes potential screening harms, including false positives, overdiagnosis, and radiation: https://www.cancer.gov/types/lung/patient/lung-screening-pdq (updated May 24, 2024).
- This is general U.S. public-health information, not individualized medical advice. Recommendations and coverage can vary; readers are directed to a health professional.

## Publication state

- Facebook: Not previewed or published. Exact Page name and numeric Page ID have not been confirmed by the user; the workflow prompt requires the actual destination, and a repository default is not treated as user authorization.
- Instagram: Not previewed or published. Exact account alias and public, fetchable HTTPS JPEG URL are not configured in the campaign request.
- GitHub Actions: Not dispatched. `gh auth status` reports no authenticated GitHub host, so workflow access is unavailable. No credentials were requested or inspected.
- Exact-post user approval: Not received. The request to publish both platforms does not waive the repository's mandatory review of exact copy, artwork, destination, audience, and timing.
- Protected environment review: Not attempted. No `PUBLISH` run was started and no environment gate was bypassed.
- Local commit: Pending. No Git author identity is configured in this worktree, and no identity was inferred or written.

## Preview details

Both workflows publish immediately after the protected environment review. Facebook Page posts use the Page's public audience. Instagram uses the account's existing audience settings. Instagram's API does not apply alt text; add the supplied alt text in the Instagram client if that option is available.

No platform publication ID, permalink, or successful Actions run exists for this campaign.