import json
import tempfile
import unittest
from pathlib import Path

from codebase_agent.scanner import (
    discover_workspace_roots,
    load_agent_state,
    save_retrieval,
    scan_workspaces,
    update_agent_state,
)


class CodebaseScannerTests(unittest.TestCase):
    def test_discovers_folder_and_multi_root_workspace_records(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            storage_one = base / "workspaceStorage" / "one"
            storage_two = base / "workspaceStorage" / "two"
            project_one = base / "project-one"
            project_two = base / "project-two"
            project_three = base / "project-three"
            for project in (project_one, project_two, project_three):
                project.mkdir()
            storage_one.mkdir(parents=True)
            storage_two.mkdir()
            workspace_file = base / "sample.code-workspace"
            workspace_file.write_text(
                json.dumps(
                    {
                        "folders": [
                            {"path": str(project_two)},
                            {"path": "project-three"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (storage_one / "workspace.json").write_text(
                json.dumps({"folder": project_one.as_uri()}), encoding="utf-8"
            )
            (storage_two / "workspace.json").write_text(
                json.dumps({"workspace": workspace_file.as_uri()}), encoding="utf-8"
            )

            roots = discover_workspace_roots([], [base / "workspaceStorage"])

            self.assertEqual(
                roots,
                [project_one.resolve(), project_three.resolve(), project_two.resolve()],
            )

    def test_finds_topic_evidence_and_skips_secret_and_dependency_files(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "src").mkdir()
            (root / "node_modules").mkdir()
            (root / "codebase_agent").mkdir()
            (root / "assets").mkdir()
            (root / "Library" / "workspaceStorage").mkdir(parents=True)
            (root / ".env").write_text("lung cancer secret", encoding="utf-8")
            (root / "node_modules" / "package.py").write_text("lung cancer", encoding="utf-8")
            (root / "codebase_agent" / "prompt.py").write_text("lung cancer", encoding="utf-8")
            (root / "Library" / "workspaceStorage" / "state.json").write_text(
                "lung cancer", encoding="utf-8"
            )
            source = root / "src" / "screening.py"
            source.write_text('"""Lung cancer screening workflow."""\n', encoding="utf-8")
            poster = root / "assets" / "lung-cancer-poster.svg"
            poster.write_text("<svg><!-- lung cancer poster --></svg>\n", encoding="utf-8")

            results = scan_workspaces([root], "lung cancer")

            self.assertEqual(
                [result["relative_path"] for result in results],
                ["assets/lung-cancer-poster.svg", "src/screening.py"],
            )
            self.assertEqual(results[1]["evidence"][0]["line"], 1)

    def test_saves_copies_and_provenance_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "project"
            root.mkdir()
            source = root / "lung_cancer.py"
            source.write_text("lung cancer topic", encoding="utf-8")
            results = scan_workspaces([root], "lung cancer")
            output = Path(temporary_dir) / "retrieved"

            save_retrieval([root], results, "lung cancer", output)

            copied = output / "workspace-1" / "lung_cancer.py"
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(copied.read_text(encoding="utf-8"), "lung cancer topic")
            self.assertEqual(manifest["match_count"], 1)
            self.assertEqual(manifest["matches"][0]["source_path"], str(source))

    def test_agent_state_remembers_topics_roots_and_scan_history(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            root = base / "project"
            root.mkdir()
            state_path = base / "retrieved" / "agent-state.json"
            first_results = [{"source_path": str(root / "first.py")}]

            update_agent_state(state_path, "lung cancer", [root], base / "run-one", first_results)
            state = update_agent_state(state_path, "brain tumor", [root], base / "run-two", [])
            loaded = load_agent_state(state_path)

            self.assertEqual(state["scan_count"], 2)
            self.assertEqual(len(state["recent_scans"]), 2)
            self.assertEqual(state["recent_scans"][0]["topic"], "lung cancer")
            self.assertEqual(state["known_workspaces"][str(root)]["scan_count"], 2)
            self.assertEqual(loaded["last_scan_at"], state["last_scan_at"])


if __name__ == "__main__":
    unittest.main()