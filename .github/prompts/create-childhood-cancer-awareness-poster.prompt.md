---
name: Create Childhood Cancer Awareness Poster
description: Create or revise an accessible, evidence-grounded childhood cancer poster and Reel from a prompt; deploy only after exact-item approval through a protected publisher.
agent: Social Campaign Creator
argument-hint: Optionally specify audience, language, print/social dimensions, brand colors, or a childhood cancer topic.
---

Create or revise a prompt-driven childhood cancer awareness campaign for families and communities. By default, deliver both a poster and a short vertical Reel. Treat later user feedback as a revision brief for the current campaign, preserving approved facts and changing the requested creative elements. Never publish, schedule, send, or announce content automatically.

## Audience and claim scope

- Audience: families, caregivers, and community members seeking a careful general overview of childhood cancer.
- Explain that childhood cancer includes many distinct diseases; do not imply there is one typical diagnosis, treatment, or prognosis.
- If using statistics, state the age group, country, measure, and data period. The existing research brief reports NCI U.S. estimates of 14,910 diagnoses and 1,590 deaths among people ages 0–19 in 2024, and age-group five-year survival estimates for diagnoses from 2013–2019. These are population estimates, not predictions for an individual child.
- If mentioning leukemia survival, state that ACS figures are approximate historical group estimates and differ by leukemia type and clinical factors. Do not present them as personalized odds or rank an individual child's prospects.
- Do not suggest that a family caused a child's cancer, that screening is recommended for all children, or that a particular treatment is right for a child. Direct questions about symptoms, tests, diagnosis, treatment, or prognosis to the child's pediatric oncology team.
- This is general educational information, not diagnosis, treatment advice, or an individual prognosis.

## Creative direction

Use a calm, respectful, hopeful-but-not-promissory editorial design. Make the topic unmistakable at first glance. Use a simple, age-appropriate visual, a strong readable headline, concise sections, high contrast, and large type. Avoid fear-based imagery, pity, identifiable patient imagery without permission, unsupported cure claims, clutter, and invented statistics. Provide accessible alt text and a text-only version of the poster copy.

Suggested headline: “Childhood cancer is not one disease.”
Suggested call to action: “Bring questions about diagnosis, treatment, clinical trials, and follow-up to your child's care team.”

Use a distinct visual concept from the previous campaign. The prompt may specify a different dataset, message, image, format, palette, audience, or platform; honor those directions while keeping claims source-grounded. Create a platform-ready poster asset and, when requested, render a real vertical MP4 Reel with timed scenes, readable on-screen captions, and source/disclaimer end card. Do not reuse prior copy or composition unless explicitly requested. A storyboard or narration file alone is not a rendered Reel.

## Sources to cite on the poster

1. National Cancer Institute, “Cancer in Children and Adolescents”: https://www.cancer.gov/types/childhood-cancers/child-adolescent-cancers-fact-sheet
2. American Cancer Society, “Childhood Leukemia Survival Rates”: https://www.cancer.org/cancer/types/leukemia-in-children/detection-diagnosis-staging/survival-rates.html

Verify all wording against these sources before finalizing. Preserve source dates and data periods; do not fabricate an access date or add unsupported claims.

## Deliverables and deployment

Save new files under `social_campaign_agent/assets/` with new versioned filenames; never overwrite the previous approved or draft asset. Return the exact poster and Reel paths, rendered formats, caption, Reel script/on-screen text, alt text, source audit, and the status `DRAFT / NEEDS REVIEW`.

If the user asks to deploy, first present the exact final asset(s), caption, verified destination account, audience, and timing. Require a separate explicit approval of those exact details. For Facebook Page photo/Reel deployment, use the active `.github/workflows/publish-facebook-page.yml`: run `NO` preview first, verify it matches, then request/act on approval for a separate `PUBLISH` run through the protected `facebook-production` environment. Never treat a Facebook profile as a Page, never use an unverified account, never ask for tokens in chat, and never bypass protected reviewers. If deployment prerequisites are absent, provide a handoff and identify them; do not claim the post was deployed.
