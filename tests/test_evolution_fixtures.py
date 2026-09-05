from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "evolution"
VALIDATOR = REPO / "skills" / "project-memory" / "scripts" / "validate_project_memory.py"


class EvolutionFixtureTests(unittest.TestCase):
    def test_manifest_cases_are_complete_and_structurally_valid(self):
        manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        cases = manifest["cases"]
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertEqual(
            {case["directory"] for case in cases},
            {path.name for path in FIXTURES.iterdir() if path.is_dir()},
        )

        for case in cases:
            with self.subTest(case=case["id"]):
                root = FIXTURES / case["directory"]
                self.assertTrue((root / "prompt.md").is_file())
                self.assertTrue((root / "oracle.md").is_file())
                project = root / "project"
                before = {
                    path.relative_to(project): path.read_bytes()
                    for path in project.rglob("*") if path.is_file()
                }
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR), str(project)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                after = {
                    path.relative_to(project): path.read_bytes()
                    for path in project.rglob("*") if path.is_file()
                }
                self.assertEqual(before, after, "Fixture validation must stay read-only")

    def test_mutation_contracts_name_only_existing_project_files(self):
        manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
        for case in manifest["cases"]:
            with self.subTest(case=case["id"]):
                project = FIXTURES / case["directory"] / "project"
                self.assertIn(case["mutation"], {"forbidden", "project-local-only"})
                allowed = case.get("allowedFiles", [])
                if case["mutation"] == "forbidden":
                    self.assertFalse(allowed)
                else:
                    self.assertTrue(allowed)
                self.assertEqual(len(allowed), len(set(allowed)))
                for name in allowed:
                    target = (project / name).resolve()
                    self.assertTrue(target.is_relative_to(project.resolve()))
                    self.assertTrue(target.is_file())

    def test_oracles_are_not_inside_test_projects(self):
        for oracle in FIXTURES.glob("*/oracle.md"):
            self.assertNotIn(oracle, (oracle.parent / "project").rglob("*"))


if __name__ == "__main__":
    unittest.main()
