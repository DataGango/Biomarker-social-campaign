---
name: Research Current and Future Childhood Cancer Treatment
description: Build a cited, date-stamped research overview of established childhood-cancer treatment approaches and investigational directions without creating an individual treatment plan.
agent: RAG Dashboard Builder
argument-hint: Optionally name a cancer type/subtype, country, evidence cutoff date, or research question; otherwise give a broad overview and state its limits.
---

Using the project's source-grounded RAG materials, prepare a research overview of current and future treatment approaches for childhood cancer. This is a literature-information task, not a treatment plan for an individual child.

## Scope and evidence rules

1. Start by identifying which local NCI/ACS source passages support each statement. Include the source title, URL, source/update date when available, and the data period. Use inline citations consistently.
2. Make clear that childhood cancer comprises many diseases and that care varies by exact diagnosis/subtype, age, tumor biology, risk group, treatment response, health status, and family circumstances. Do not combine different cancers into one treatment pathway.
3. Separate the evidence into:
   - **Established/current care:** describe only approaches supported by the sources as current clinical practice. If the local sources do not describe specific modalities or indications, say that the local evidence is insufficient rather than filling gaps from memory.
   - **Future/investigational directions:** include an approach only when an authoritative source or cited study directly supports it. Label preclinical, early-phase, clinical-trial, and approved/current status distinctly. An ongoing trial is not evidence that a treatment works or is appropriate.
   - **Questions for the oncology team:** provide neutral questions families can ask about goals, options, benefits/risks, testing, trials, supportive care, and follow-up.
4. For claims about the latest standards, approvals, or trials, use current primary/official sources such as NCI, FDA, ClinicalTrials.gov, or peer-reviewed original studies, and record the retrieval/access date. Do not present the locally indexed material as current if its update date is older. If live source verification is unavailable, explicitly label the overview as limited to the indexed source dates.
5. Do not calculate or imply a personalized prognosis, rank a child's prospects, diagnose, select a regimen, recommend starting/stopping/changing care, or imply that a research-stage intervention is available treatment. Direct individual decisions to the child's pediatric oncology team.
6. Do not infer a treatment success rate from the number or status of registered trials. Distinguish trial registration, posted results, and published evidence; report denominators, periods, and limitations when summarizing counts.

## Output format

- **Scope and evidence cutoff**
- **Established approaches described by the sources** (with cancer type/context and citations)
- **Investigational and future directions** (stage of evidence, what is known, what remains unknown, citations)
- **Evidence gaps and source limitations**
- **Questions families can discuss with the pediatric oncology team**
- **Sources** (title, organization, URL, update/access date, and relevant data period)

End with this notice: “This research overview is educational information, not an individualized treatment plan, diagnosis, or prognosis. Treatment decisions should be discussed with the child's pediatric oncology team.”
