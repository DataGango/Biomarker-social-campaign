"""Discover VS Code workspaces and retrieve text files relevant to a topic."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


TEXT_SUFFIXES = {
    ".c", ".cc", ".cfg", ".cjs", ".cpp", ".cs", ".css", ".csv", ".go",
    ".h", ".hpp", ".html", ".ini", ".ipynb", ".java", ".js", ".json",
    ".jsx", ".kt", ".md", ".mjs", ".php", ".pl", ".properties", ".py",
    ".r", ".rb", ".rs", ".scala", ".scss", ".sh", ".sql", ".swift",
    ".svg", ".toml", ".ts", ".tsx", ".txt", ".vue", ".xml", ".yaml", ".yml",
}
SKIP_DIRS = {
    ".aws", ".azure", ".git", ".gnupg", ".hg", ".next", ".ssh", ".svn",
    ".venv", ".vscode", ".vscode-insiders", ".Trash", "Applications", "build",
    "chatEditingSessions", "chat-session-resources", "coverage", "debug-logs",
    "codebase_agent", "dist", "Library", "node_modules", "Pods", "__pycache__", "retrieved",
    "target", "vendor", "venv", "workspaceStorage",
}
SKIP_FILES = {
    ".env", ".env.local", ".npmrc", ".pypirc", "id_rsa", "id_ed25519",
    "credentials", "secrets.json",
}
SKIP_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".jks", ".keystore"}
TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
MAX_FILE_BYTES = 1_000_000
MAX_FILES_PER_SCAN = 300_000


def _path_from_uri(value: str) -> Path:
    parsed = urlparse(value)
    if parsed.scheme == "file":
        path = unquote(parsed.path)
        if parsed.netloc and parsed.netloc != "localhost":
            path = f"//{parsed.netloc}{path}"
        return Path(path).expanduser()
    return Path(value).expanduser()


def _workspace_file_roots(workspace_file: Path) -> list[Path]:
    try:
        settings = json.loads(workspace_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []

    roots = []
    for folder in settings.get("folders", []):
        if not isinstance(folder, dict):
            continue
        value = folder.get("path") or folder.get("uri")
        if not isinstance(value, str):
            continue
        folder_path = _path_from_uri(value)
        if not folder_path.is_absolute():
            folder_path = workspace_file.parent / folder_path
        roots.append(folder_path.resolve())
    return roots


def discover_workspace_roots(
    additional_roots: list[str | Path] | None = None,
    metadata_roots: list[Path] | None = None,
) -> list[Path]:
    """Find local folders recorded in VS Code and explicitly supplied roots."""
    home = Path.home()
    default_metadata_roots = [
        home / "Library/Application Support/Code/User/workspaceStorage",
        home / "Library/Application Support/Code - Insiders/User/workspaceStorage",
        home / "Library/Application Support/VSCodium/User/workspaceStorage",
        home / ".config/Code/User/workspaceStorage",
        home / ".config/Code - Insiders/User/workspaceStorage",
        home / ".config/VSCodium/User/workspaceStorage",
    ]
    metadata_roots = metadata_roots if metadata_roots is not None else default_metadata_roots
    roots: set[Path] = set()

    for storage_root in metadata_roots:
        if not storage_root.is_dir():
            continue
        for metadata_file in storage_root.glob("*/workspace.json"):
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            folder_uri = metadata.get("folder")
            workspace_uri = metadata.get("workspace")
            if isinstance(folder_uri, str):
                roots.add(_path_from_uri(folder_uri).resolve())
            elif isinstance(workspace_uri, str):
                workspace_file = _path_from_uri(workspace_uri).resolve()
                roots.update(_workspace_file_roots(workspace_file))

    for root in additional_roots or []:
        candidate = Path(root).expanduser().resolve()
        if candidate.is_dir():
            roots.add(candidate)

    return sorted((root for root in roots if root.is_dir()), key=lambda path: str(path).casefold())


def _topic_groups(topic: str, extra_terms: list[str] | None) -> list[tuple[str, set[str]]]:
    groups = []
    for phrase in [topic, *(extra_terms or [])]:
        tokens = {token.lower() for token in TOKEN_PATTERN.findall(phrase)}
        if tokens:
            groups.append((phrase, tokens))
    return groups


def _matching_lines(text: str, groups: list[tuple[str, set[str]]]) -> list[dict[str, object]]:
    matches = []
    for line_number, line in enumerate(text.splitlines(), 1):
        tokens = {token.lower() for token in TOKEN_PATTERN.findall(line)}
        matching_terms = [phrase for phrase, required_tokens in groups if required_tokens <= tokens]
        if matching_terms:
            matches.append(
                {
                    "line": line_number,
                    "terms": matching_terms,
                    "excerpt": line.strip()[:500],
                }
            )
            if len(matches) >= 20:
                break
    return matches


def scan_workspaces(
    roots: list[Path],
    topic: str,
    extra_terms: list[str] | None = None,
) -> list[dict[str, object]]:
    """Return matching text files and evidence lines without modifying sources."""
    groups = _topic_groups(topic, extra_terms)
    results = []
    scanned = 0
    visited: set[Path] = set()

    for root_index, root in enumerate(roots, 1):
        for current_dir, directory_names, file_names in os.walk(root, followlinks=False):
            directory_names[:] = [
                name for name in directory_names
                if name not in SKIP_DIRS and not Path(current_dir, name).is_symlink()
            ]
            current_path = Path(current_dir)
            for file_name in file_names:
                scanned += 1
                if scanned > MAX_FILES_PER_SCAN:
                    return results
                source_path = current_path / file_name
                lowered_name = file_name.lower()
                if source_path.is_symlink() or lowered_name in SKIP_FILES or lowered_name.startswith(".env"):
                    continue
                if source_path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                if source_path.suffix.lower() in SKIP_SUFFIXES:
                    continue
                try:
                    resolved = source_path.resolve(strict=True)
                    if resolved in visited or resolved.stat().st_size > MAX_FILE_BYTES:
                        continue
                    visited.add(resolved)
                    text = resolved.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    continue

                evidence = _matching_lines(text, groups)
                path_matches = [
                    phrase for phrase, required_tokens in groups
                    if required_tokens <= {token.lower() for token in TOKEN_PATTERN.findall(str(source_path))}
                ]
                if evidence or path_matches:
                    results.append(
                        {
                            "root_index": root_index,
                            "workspace": str(root),
                            "relative_path": str(source_path.relative_to(root)),
                            "source_path": str(source_path),
                            "path_terms": path_matches,
                            "evidence": evidence,
                            "text": text,
                        }
                    )
    return results


def save_retrieval(
    roots: list[Path],
    results: list[dict[str, object]],
    topic: str,
    output_dir: Path,
) -> Path:
    """Copy matches and write a provenance manifest under a new output folder."""
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest_results = []
    for index, result in enumerate(results, 1):
        relative_path = Path(str(result["relative_path"]))
        destination = output_dir / f"workspace-{result['root_index']}" / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(result["source_path"]), destination)
        manifest_results.append(
            {
                "workspace": result["workspace"],
                "source_path": result["source_path"],
                "retrieved_path": str(destination.relative_to(output_dir)),
                "path_terms": result["path_terms"],
                "evidence": result["evidence"],
            }
        )

    manifest = {
        "topic": topic,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspaces_scanned": [str(root) for root in roots],
        "match_count": len(manifest_results),
        "matches": manifest_results,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_dir


def load_agent_state(state_path: Path) -> dict[str, object]:
    """Load persisted local scan memory, returning an empty state when absent."""
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    return {
        "schema_version": 1,
        "scan_count": int(state.get("scan_count", 0)),
        "last_scan_at": state.get("last_scan_at"),
        "known_workspaces": state.get("known_workspaces", {}),
        "recent_scans": state.get("recent_scans", []),
    }


def update_agent_state(
    state_path: Path,
    topic: str,
    roots: list[Path],
    output_dir: Path,
    results: list[dict[str, object]],
) -> dict[str, object]:
    """Remember scan history and workspace coverage without storing file contents."""
    state = load_agent_state(state_path)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    workspaces = state["known_workspaces"]
    if not isinstance(workspaces, dict):
        workspaces = {}
    for root in roots:
        key = str(root)
        previous = workspaces.get(key, {})
        if not isinstance(previous, dict):
            previous = {}
        workspaces[key] = {
            "first_seen": previous.get("first_seen", now),
            "last_seen": now,
            "scan_count": int(previous.get("scan_count", 0)) + 1,
        }

    recent_scans = state["recent_scans"]
    if not isinstance(recent_scans, list):
        recent_scans = []
    recent_scans.append(
        {
            "topic": topic,
            "scanned_at": now,
            "workspaces": [str(root) for root in roots],
            "match_count": len(results),
            "manifest_path": str(output_dir / "manifest.json"),
            "matched_sources": [str(result["source_path"]) for result in results[:500]],
        }
    )

    updated = {
        "schema_version": 1,
        "scan_count": int(state["scan_count"]) + 1,
        "last_scan_at": now,
        "known_workspaces": workspaces,
        "recent_scans": recent_scans[-100:],
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = state_path.with_suffix(state_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    temporary_path.replace(state_path)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", default="lung cancer", help="Topic phrase to retrieve")
    parser.add_argument("--term", action="append", default=[], help="Additional exact phrase; repeat as needed")
    parser.add_argument("--root", action="append", default=[], help="Add a workspace folder explicitly")
    parser.add_argument("--output-dir", default="retrieved/lung-cancer", help="Destination for copies and manifest")
    parser.add_argument(
        "--state-file", default="retrieved/.codebase-agent-state.json", help="Local persistent scan memory"
    )
    parser.add_argument("--show-state", action="store_true", help="Print saved scan history without scanning")
    args = parser.parse_args()

    state_path = Path(args.state_file)
    if args.show_state:
        print(json.dumps(load_agent_state(state_path), indent=2))
        return

    current_root = Path.cwd().resolve()
    roots = discover_workspace_roots([current_root, *args.root])
    if not roots:
        parser.error("No VS Code workspace roots were found; pass one or more --root folders.")

    matches = scan_workspaces(roots, args.topic, args.term)
    output_dir = Path(args.output_dir)
    if output_dir.exists():
        suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = output_dir.with_name(f"{output_dir.name}-{suffix}")
    save_retrieval(roots, matches, args.topic, output_dir)
    state = update_agent_state(state_path, args.topic, roots, output_dir, matches)
    print(f"Workspaces scanned: {len(roots)}")
    print(f"Topic matches copied: {len(matches)}")
    print(f"Retrieval saved to: {output_dir.resolve()}")
    print(f"Persistent scan history: {state['scan_count']} scans ({state_path.resolve()})")


if __name__ == "__main__":
    main()