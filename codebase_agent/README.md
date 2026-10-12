# Topic-Focused Codebase Scanner

This local-only agent discovers project folders recorded by VS Code (Stable, Insiders, or VSCodium), searches source/text files for an exact topic and optional variants, then copies matches into this project with a provenance manifest. It does not execute discovered code, modify source workspaces, or make network requests.

Run from the Biomarker project root:

```sh
python -m codebase_agent.scanner --topic "lung cancer" \
  --term "lung carcinoma" \
  --term "non-small cell lung cancer" \
  --term "small cell lung cancer" \
  --term NSCLC --term SCLC \
  --term "lung cancer screening"
```

Results are saved under `retrieved/lung-cancer/` with source copies and `manifest.json`. If that directory already exists, the agent creates a timestamped sibling instead. Persistent local memory at `retrieved/.codebase-agent-state.json` tracks recent topics, scan timestamps, workspace coverage, match counts, and manifest paths without storing source contents. Use `--show-state` to inspect that history. Add project folders not recorded in VS Code with repeated `--root /path/to/project` arguments. The reusable, lung-cancer-specific instructions are in `codebase_agent/prompts/lung_cancer_codebase_review.md`.

## Coverage and Safety

The scanner searches VS Code workspace metadata roots known for macOS and common Linux installs. It only sees workspaces retained in that metadata or explicitly passed with `--root`; it does not crawl the entire filesystem. It skips editor internals, common dependency/build folders, environment files, known credential filenames, key/certificate files, symlinks, binary/unrecognized files, and text files larger than 1 MB. Matching is lexical, not semantic, so review the evidence in the manifest before reusing a match.

Run the focused tests with:

```sh
python -m unittest codebase_agent.tests.test_scanner -v
```