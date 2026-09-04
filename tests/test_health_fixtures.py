from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPOSITORY_ROOT
    / "skills"
    / "project-memory"
    / "scripts"
    / "validate_project_memory.py"
)
FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures" / "health"

sys.path.insert(0, str(SCRIPT.parent))
import validate_project_memory as validator  # noqa: E402


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        directory = Path(dirpath)
        for name in sorted(dirnames + filenames):
            path = directory / name
            stat = path.lstat()
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(stat.st_mode).encode("ascii"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            if path.is_symlink():
                digest.update(os.readlink(path).encode("utf-8"))
            elif path.is_file():
                digest.update(path.read_bytes())
    return digest.hexdigest()


class HealthFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (FIXTURES / "manifest.json").read_text(encoding="utf-8")
        )

    def test_manifest_has_independent_anonymized_projects(self) -> None:
        cases = self.manifest["cases"]
        self.assertEqual(1, self.manifest["formatVersion"])
        self.assertEqual(6, len(cases))
        self.assertEqual(len(cases), len({case["directory"] for case in cases}))

        for case in cases:
            with self.subTest(case=case["directory"]):
                project = FIXTURES / case["directory"]
                self.assertTrue((project / "AGENTS.md").is_file())
                self.assertTrue((project / ".planning/context.md").is_file())
                self.assertTrue((project / ".planning/release-log.md").is_file())
                for path in project.rglob("*"):
                    if path.is_file():
                        text = path.read_text(encoding="utf-8")
                        self.assertNotRegex(text, r"/(?:Users|home)/[^/\s]+/")

    def test_health_cases_emit_the_declared_codes_and_severities(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["directory"]):
                project = FIXTURES / case["directory"]
                issues = validator.validate_project(project, health=True)
                observed = {issue.code: issue.severity for issue in issues}
                for code, severity in case["expected"].items():
                    self.assertEqual(severity, observed.get(code), issues)

                if case["directory"] == "healthy-ruleset":
                    self.assertEqual([], issues)
                elif case["directory"] == "healthy-legacy":
                    self.assertEqual(
                        {"RULESET_NOT_ENABLED": "NOTICE"},
                        observed,
                    )

    def test_review_mutations_do_not_become_blocking_errors(self) -> None:
        for directory in ("context-drift", "heading-regression"):
            with self.subTest(case=directory):
                issues = validator.validate_project(FIXTURES / directory, health=True)
                self.assertFalse(
                    any(issue.severity == "ERROR" for issue in issues),
                    issues,
                )

    def test_deterministic_mutations_are_blocking_errors(self) -> None:
        for directory, code in (
            ("release-log-order", "RELEASE_LOG_DATE_ORDER"),
            ("missing-completion-signal", "STATE_COMPLETION_SIGNAL_MISSING"),
        ):
            with self.subTest(case=directory):
                issues = validator.validate_project(FIXTURES / directory, health=True)
                self.assertTrue(
                    any(issue.code == code and issue.severity == "ERROR" for issue in issues),
                    issues,
                )

    def test_health_json_is_deterministic_and_read_only(self) -> None:
        project = FIXTURES / "context-drift"
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            str(project),
            "--health",
            "--format",
            "json",
        ]
        before = tree_fingerprint(project)
        first = subprocess.run(command, check=False, capture_output=True, text=True)
        second = subprocess.run(command, check=False, capture_output=True, text=True)

        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, tree_fingerprint(project))
        payload = json.loads(first.stdout)
        self.assertEqual(1, payload["format_version"])
        self.assertEqual("health", payload["mode"])
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["guard_passed"])
        self.assertTrue(payload["review_required"])
        self.assertEqual("review_required", payload["status"])
        self.assertEqual(0, payload["summary"]["ERROR"])
        self.assertGreaterEqual(payload["summary"]["REVIEW"], 1)
        self.assertTrue(
            any(issue["code"] == "CONTEXT_RELEASE_HEADING" for issue in payload["issues"])
        )


if __name__ == "__main__":
    unittest.main()
