---
name: codebase-search
description: Search the configured project workspace for topic evidence without modifying source files.
---

# Codebase Search

Search only the configured workspace root using the existing `codebase_agent.scanner`. Skip environment files, credentials, dependencies, generated folders, and symlinks. Return relative paths and bounded matching excerpts; do not return entire files, copy files, mutate scan memory, or search outside the configured root.

Evaluation: evidence includes a relative source path, full contents are absent, and secret markers are not returned.