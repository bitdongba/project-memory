from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
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
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "validator"

sys.path.insert(0, str(SCRIPT.parent))
import validate_project_memory as validator  # noqa: E402


def issue_codes(project: Path) -> set[str]:
    return {issue.code for issue in validator.validate_project(project)}


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        directory = Path(dirpath)
        for name in sorted(dirnames + filenames):
            path = directory / name
            relative = path.relative_to(root).as_posix()
            stat = path.lstat()
            digest.update(relative.encode("utf-8"))
            digest.update(str(stat.st_mode).encode("ascii"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            if path.is_symlink():
                digest.update(os.readlink(path).encode("utf-8"))
            elif path.is_file():
                digest.update(path.read_bytes())
    return digest.hexdigest()


class ProjectMemoryValidatorTests(unittest.TestCase):
    def test_valid_fixture_passes_without_retrospective(self) -> None:
        project = FIXTURES / "valid_project"

        self.assertFalse((project / ".planning/project-retrospective.md").exists())
        self.assertEqual([], validator.validate_project(project))

    def test_invalid_fixture_exercises_all_core_checks(self) -> None:
        codes = issue_codes(FIXTURES / "invalid_project")

        self.assertTrue(
            {
                "REQUIRED_FILE_MISSING",
                "CONTEXT_SCHEMA_MISSING",
                "BROKEN_LINK",
                "LINK_OUTSIDE_ROOT",
                "PLACEHOLDER_UNRESOLVED",
                "DUPLICATE_ADR_ID",
                "DUPLICATE_EXPERIENCE_ID",
                "STATE_STATUS_INVALID",
                "STATE_NEXT_STEP_MISSING",
                "INDEX_TARGET_MISSING",
            }.issubset(codes),
            codes,
        )

    def test_code_form_context_pointer_is_allowed_in_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "AGENTS.md").write_text(
                "# Instructions\n\n"
                "<!-- project-memory:start schema=1 -->\n"
                "Read `.planning/context.md` before work.\n"
                "<!-- project-memory:end -->\n",
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))

    def test_missing_managed_block_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "AGENTS.md").write_text("# User-authored instructions\n", encoding="utf-8")

            self.assertIn("ENTRY_BLOCK_MISSING", issue_codes(project))

    def test_managed_block_requires_current_schema_and_context_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "AGENTS.md").write_text(
                "<!-- project-memory:start schema=2 -->\n"
                "No canonical context pointer is present.\n"
                "<!-- project-memory:end -->\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("ENTRY_SCHEMA_UNSUPPORTED", codes)
            self.assertIn("ENTRY_CONTEXT_LINK_MISSING", codes)
            self.assertIn("ENTRY_CONTEXT_SCHEMA_MISMATCH", codes)

    def test_context_schema_is_required_unique_and_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            context = project / ".planning/context.md"

            original = context.read_text(encoding="utf-8")
            context.write_text(
                original.replace(
                    "- Project Memory schema: 1",
                    "- Project Memory schema: 1\n- Project Memory schema: 1",
                ),
                encoding="utf-8",
            )
            self.assertIn("CONTEXT_SCHEMA_MULTIPLE", issue_codes(project))

            context.write_text(
                original.replace("- Project Memory schema: 1", "- Project Memory schema: 2"),
                encoding="utf-8",
            )
            codes = issue_codes(project)
            self.assertIn("CONTEXT_SCHEMA_UNSUPPORTED", codes)
            self.assertIn("ENTRY_CONTEXT_SCHEMA_MISMATCH", codes)

            context.write_text(
                original.replace("- Project Memory schema: 1\n", ""),
                encoding="utf-8",
            )
            self.assertIn("CONTEXT_SCHEMA_MISSING", issue_codes(project))

    def test_unclosed_managed_block_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "AGENTS.md").write_text(
                "<!-- project-memory:start schema=1 -->\n"
                "Read `.planning/context.md`.\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("ENTRY_BLOCK_UNCLOSED", codes)
            self.assertIn("ENTRY_BLOCK_MISSING", codes)

    def test_symlink_escape_is_rejected_without_reading_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            project = temporary_path / "project"
            outside = temporary_path / "outside.md"
            shutil.copytree(FIXTURES / "valid_project", project)
            outside.write_text("# <SHOULD-NOT-BE-READ>\n", encoding="utf-8")
            context = project / ".planning/context.md"
            context.unlink()
            try:
                context.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            issues = validator.validate_project(project)
            self.assertIn("SYMLINK_ESCAPE", {issue.code for issue in issues})
            self.assertFalse(
                any(
                    issue.code == "PLACEHOLDER_UNRESOLVED"
                    and issue.path == ".planning/context.md"
                    for issue in issues
                ),
                issues,
            )

    def test_relative_link_through_symlink_cannot_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            project = temporary_path / "project"
            outside = temporary_path / "outside.md"
            shutil.copytree(FIXTURES / "valid_project", project)
            outside.write_text("# Outside\n", encoding="utf-8")
            linked = project / "docs/reference.md"
            linked.unlink()
            try:
                linked.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertIn("LINK_OUTSIDE_ROOT", issue_codes(project))

    def test_active_state_needs_a_meaningful_exact_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / ".planning/state.md").write_text(
                "# State\n\n- Status: paused\n\n## Exact next step\n\n<TODO>\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("STATE_NEXT_STEP_MISSING", codes)
            self.assertIn("PLACEHOLDER_UNRESOLVED", codes)

    def test_idle_state_does_not_require_a_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / ".planning/state.md").write_text(
                "# State\n\n- Status: idle\n",
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))

    def test_cli_has_distinct_success_validation_and_runtime_exit_codes(self) -> None:
        valid = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(FIXTURES / "valid_project")],
            check=False,
            capture_output=True,
            text=True,
        )
        invalid = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(FIXTURES / "invalid_project")],
            check=False,
            capture_output=True,
            text=True,
        )
        missing = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(FIXTURES / "does-not-exist")],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, valid.returncode, valid.stdout + valid.stderr)
        self.assertIn("Validation passed", valid.stdout)
        self.assertEqual(1, invalid.returncode, invalid.stdout + invalid.stderr)
        self.assertIn("Validation failed", invalid.stdout)
        self.assertRegex(invalid.stdout, r"ERROR \[[A-Z_]+\]")
        self.assertEqual(2, missing.returncode, missing.stdout + missing.stderr)
        self.assertIn("VALIDATOR_RUNTIME", missing.stderr)

    def test_cli_is_read_only(self) -> None:
        project = FIXTURES / "invalid_project"
        before = tree_fingerprint(project)

        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(project)],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(1, completed.returncode)
        self.assertEqual(before, tree_fingerprint(project))


if __name__ == "__main__":
    unittest.main()
