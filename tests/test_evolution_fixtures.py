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
        self.assertEqual(len(cases), 9)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))

        for case in cases:
            with self.subTest(case=case["id"]):
                root = FIXTURES / case["directory"]
                self.assertTrue((root / "prompt.md").is_file())
                self.assertTrue((root / "oracle.md").is_file())
                project = root / "project"
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR), str(project)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_oracles_are_not_inside_test_projects(self):
        for oracle in FIXTURES.glob("*/oracle.md"):
            self.assertNotIn(oracle, (oracle.parent / "project").rglob("*"))


if __name__ == "__main__":
    unittest.main()
