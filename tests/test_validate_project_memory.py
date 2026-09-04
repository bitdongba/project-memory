from __future__ import annotations

import hashlib
import json
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
ROUTER_SCRIPT = (
    REPOSITORY_ROOT
    / "skills"
    / "project-memory"
    / "scripts"
    / "route_project_memory.py"
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


def enable_ruleset(project: Path) -> None:
    context = project / ".planning/context.md"
    context.write_text(
        context.read_text(encoding="utf-8")
        .replace(
            "- Project Memory schema: 1",
            "- Project Memory schema: 1\n- Project Memory ruleset: 1",
        )
        .replace(
            "| 文档 | 用途 |\n"
            "|---|---|\n"
            "| `.planning/context.md` | 稳定上下文与索引 |\n"
            "| `.planning/state.md` | 当前交接状态 |\n"
            "| `.planning/release-log.md` | 重要变化历史 |\n"
            "| `.planning/decisions/0001-storage.md` | 已接受的决定 |\n"
            "| `.planning/experiences.md` | 经确认的经验 |\n"
            "| `docs/reference.md` | 一手参考资料 |",
            "| 角色 | 文档 | 用途 |\n"
            "|---|---|---|\n"
            "| stable-intent | `.planning/context.md` | 稳定上下文与索引 |\n"
            "| protocol-setting | `.planning/context.md` | 协议设置 |\n"
            "| resumable-state | `.planning/state.md` | 当前交接状态 |\n"
            "| historical-event | `.planning/release-log.md` | 重要变化历史 |\n"
            "| topic-detail | `.planning/decisions/0001-storage.md` | 已接受的决定 |\n"
            "| topic-detail | `.planning/experiences.md` | 经确认的经验 |\n"
            "| topic-detail | `docs/reference.md` | 一手参考资料 |",
        ),
        encoding="utf-8",
    )
    entry = project / "AGENTS.md"
    entry.write_text(
        entry.read_text(encoding="utf-8").replace(
            "project-memory:start schema=1",
            "project-memory:start schema=1 ruleset=1",
        ),
        encoding="utf-8",
    )


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

    def test_document_index_inline_code_bare_filenames_are_project_root_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "README.md").write_text("# README\n", encoding="utf-8")
            (project / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "| `docs/reference.md` | 一手参考资料 |",
                    "| `docs/reference.md` | 一手参考资料 |\n"
                    "| `README.md` | 项目说明 |\n"
                    "| `PROJECT.md` | 项目定义 |",
                ),
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))

    def test_document_index_markdown_link_remains_relative_to_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            (project / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "| `docs/reference.md` | 一手参考资料 |",
                    "| `docs/reference.md` | 一手参考资料 |\n"
                    "| [Project](../PROJECT.md) | 项目定义 |",
                ),
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))

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

    def test_ruleset_is_optional_but_context_and_entry_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)

            self.assertEqual([], validator.validate_project(project))

            entry = project / "AGENTS.md"
            entry.write_text(
                entry.read_text(encoding="utf-8").replace(" ruleset=1", ""),
                encoding="utf-8",
            )
            self.assertIn("ENTRY_CONTEXT_RULESET_MISMATCH", issue_codes(project))

            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "Project Memory ruleset: 1", "Project Memory ruleset: 2"
                ),
                encoding="utf-8",
            )
            entry.write_text(
                entry.read_text(encoding="utf-8").replace(
                    "schema=1", "schema=1 ruleset=2"
                ),
                encoding="utf-8",
            )
            codes = issue_codes(project)
            self.assertIn("CONTEXT_RULESET_UNSUPPORTED", codes)
            self.assertIn("ENTRY_RULESET_UNSUPPORTED", codes)

    def test_ruleset_requires_one_complete_typed_index_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")

            context.write_text(
                original.replace(
                    "| historical-event | `.planning/release-log.md` | 重要变化历史 |\n",
                    "",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_ROLE_CARDINALITY", issue_codes(project))

            context.write_text(
                original.replace(
                    "| topic-detail | `.planning/experiences.md` | 经确认的经验 |",
                    "| topic-detail | `.planning/experiences.md` | 经确认的经验 |\n"
                    "| topic-detail | `.planning/experiences.md` | 重复路径 |",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_ROUTE_DUPLICATE", issue_codes(project))

            context.write_text(
                original.replace("## 文档索引", "## Reference map"),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_SECTION_INVALID", issue_codes(project))

            (project / ".planning/timeline.md").write_text(
                "# Timeline\n",
                encoding="utf-8",
            )
            context.write_text(
                original.replace(
                    "| historical-event | `.planning/release-log.md` | 重要变化历史 |",
                    "| historical-event | `.planning/release-log.md` | 重要变化历史 |\n"
                    "| historical-event | `.planning/timeline.md` | 第二份历史 |",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_ROLE_CARDINALITY", issue_codes(project))

            context.write_text(
                original.replace(
                    "| historical-event | `.planning/release-log.md` | 重要变化历史 |",
                    "| historical-event | `.planning/context.md` | 冲突角色 |",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_ROLE_COLLISION", issue_codes(project))

            context.write_text(
                original.replace(
                    "| resumable-state | `.planning/state.md` | 当前交接状态 |\n",
                    "",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_STATE_CARDINALITY", issue_codes(project))

            context.write_text(
                original.replace(
                    "`.planning/decisions/0001-storage.md`",
                    "` .planning/decisions/0001-storage.md `",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_PATH_INVALID", issue_codes(project))

            second_table = (
                "| 角色 | 文档 | 用途 |\n"
                "|---|---|---|\n"
                "| stable-intent | `.planning/context.md` | 重复表 |\n"
            )
            context.write_text(
                original.replace(
                    "\n## 权威边界",
                    f"\n\n{second_table}\n## 权威边界",
                ),
                encoding="utf-8",
            )
            self.assertIn("RULESET_INDEX_TABLE_INVALID", issue_codes(project))

    def test_ruleset_checks_custom_indexed_history_and_state_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                .replace(
                    "`.planning/release-log.md`",
                    "`.planning/timeline.md`",
                )
                .replace(
                    "`.planning/state.md`",
                    "`docs/handoff.md`",
                ),
                encoding="utf-8",
            )
            (project / ".planning/release-log.md").unlink()
            (project / ".planning/timeline.md").write_text(
                "# Timeline\n\n## 2026-08-10 Older\n\n## 2026-08-20 Newer\n",
                encoding="utf-8",
            )
            (project / "docs/handoff.md").write_text(
                "# Handoff\n\n- Status: active\n\n"
                "## Exact next step\n\n1. Resume the indexed task.\n",
                encoding="utf-8",
            )

            issues = validator.validate_project(project)
            observed = {(issue.code, issue.path) for issue in issues}
            self.assertNotIn(
                ("REQUIRED_FILE_MISSING", ".planning/release-log.md"),
                observed,
            )
            self.assertIn(
                ("RELEASE_LOG_DATE_ORDER", ".planning/timeline.md"),
                observed,
            )
            self.assertIn(
                ("STATE_COMPLETION_SIGNAL_MISSING", "docs/handoff.md"),
                observed,
            )

    def test_validator_and_router_agree_on_custom_canonical_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                .replace("`.planning/release-log.md`", "`.planning/timeline.md`")
                .replace("`.planning/state.md`", "`docs/handoff.md`"),
                encoding="utf-8",
            )
            old_history = project / ".planning/release-log.md"
            (project / ".planning/timeline.md").write_bytes(old_history.read_bytes())
            old_history.unlink()
            old_state = project / ".planning/state.md"
            (project / "docs/handoff.md").write_bytes(old_state.read_bytes())
            old_state.unlink()

            self.assertEqual([], validator.validate_project(project))
            for kind, expected in (
                ("historical-event", ".planning/timeline.md"),
                ("resumable-state", "docs/handoff.md"),
            ):
                with self.subTest(kind=kind):
                    routed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(ROUTER_SCRIPT),
                            str(project),
                            "--kind",
                            kind,
                            "--format",
                            "json",
                        ],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(0, routed.returncode, routed.stdout + routed.stderr)
                    self.assertEqual(expected, json.loads(routed.stdout)["primary_path"])

    def test_ruleset_keeps_stable_intent_and_protocol_setting_in_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            alternate = project / "docs/alternate-context.md"
            alternate.write_text("# Alternate context\n", encoding="utf-8")
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")

            for role in ("stable-intent", "protocol-setting"):
                with self.subTest(role=role):
                    context.write_text(
                        original.replace(
                            f"| {role} | `.planning/context.md` |",
                            f"| {role} | `docs/alternate-context.md` |",
                        ),
                        encoding="utf-8",
                    )
                    self.assertIn(
                        "RULESET_INDEX_CORE_ROUTE_INVALID",
                        issue_codes(project),
                    )

    def test_ruleset_checks_all_indexed_canonical_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            topic = project / "docs/canonical-topic.md"
            topic.write_text(
                "# Canonical topic\n\n"
                "## ADR-0001 Duplicate decision\n\n"
                "## EXP-001 Duplicate experience\n\n"
                "- [Missing](missing.md)\n"
                "- <TODO>\n\n"
                "## Numbered sections\n\n"
                "### 10 Later\n\n"
                "### 5 Earlier\n",
                encoding="utf-8",
            )
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`docs/reference.md`",
                    "`docs/canonical-topic.md`",
                ),
                encoding="utf-8",
            )

            issues = validator.validate_project(project, health=True)
            codes = {issue.code for issue in issues}
            self.assertTrue(
                {
                    "BROKEN_LINK",
                    "PLACEHOLDER_UNRESOLVED",
                    "DUPLICATE_ADR_ID",
                    "DUPLICATE_EXPERIENCE_ID",
                    "NUMERIC_HEADING_REGRESSION",
                }.issubset(codes),
                issues,
            )
            self.assertTrue(
                any(
                    issue.code == "NUMERIC_HEADING_REGRESSION"
                    and issue.path == "docs/canonical-topic.md"
                    for issue in issues
                ),
                issues,
            )

    def test_indexed_adr_alias_is_scanned_once_by_resolved_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            real_directory = project / "records/adr"
            real_directory.mkdir(parents=True)
            (real_directory / "ADR-0002-choice.md").write_text(
                "# ADR-0002 Choice\n",
                encoding="utf-8",
            )
            alias = project / "docs/adr"
            try:
                alias.symlink_to("../records/adr")
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`docs/reference.md`",
                    "`docs/adr/ADR-0002-choice.md`",
                ),
                encoding="utf-8",
            )

            self.assertNotIn("DUPLICATE_ADR_ID", issue_codes(project))

    def test_adr_identity_keeps_the_conventional_filename_for_id_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            decisions = project / ".planning/decisions"
            first = decisions / "0002-first.md"
            first.write_text("# First decision\n", encoding="utf-8")
            (decisions / "0002-second.md").write_text(
                "# Second decision\n",
                encoding="utf-8",
            )
            alias = project / ".planning/a.md"
            try:
                alias.symlink_to("decisions/0002-first.md")
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`docs/reference.md`",
                    "`.planning/a.md`",
                ),
                encoding="utf-8",
            )

            self.assertIn("DUPLICATE_ADR_ID", issue_codes(project))

    def test_fenced_and_commented_indexed_adr_examples_are_not_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            topic = project / "docs/adr-examples.md"
            topic.write_text(
                "# ADR examples\n\n"
                "```md\n## ADR-0001 Fenced example\n```\n\n"
                "<!--\n## ADR-0001 Commented example\n-->\n",
                encoding="utf-8",
            )
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`docs/reference.md`",
                    "`docs/adr-examples.md`",
                ),
                encoding="utf-8",
            )

            self.assertNotIn("DUPLICATE_ADR_ID", issue_codes(project))

    def test_ruleset_rejects_discontinuous_typed_index_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")
            for separator in ("\n", "```md\nexample\n```\n"):
                with self.subTest(separator=separator):
                    context.write_text(
                        original.replace(
                            "| historical-event | `.planning/release-log.md` | 重要变化历史 |\n"
                            "| topic-detail | `.planning/decisions/0001-storage.md` |",
                            "| historical-event | `.planning/release-log.md` | 重要变化历史 |\n"
                            + separator
                            + "| topic-detail | `.planning/decisions/0001-storage.md` |",
                        ),
                        encoding="utf-8",
                    )
                    self.assertIn("RULESET_INDEX_ROW_INVALID", issue_codes(project))

    def test_ruleset_index_accepts_context_relative_markdown_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/decisions/0001-storage.md`",
                    "[Decision](decisions/0001-storage.md)",
                ),
                encoding="utf-8",
            )

            self.assertFalse(
                any(
                    issue.code.startswith("RULESET_INDEX_")
                    for issue in validator.validate_project(project)
                )
            )

    def test_ruleset_rejects_internal_symlink_alias_role_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            alias = project / ".planning/history-alias.md"
            try:
                alias.symlink_to("release-log.md")
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/decisions/0001-storage.md`",
                    "`.planning/history-alias.md`",
                ),
                encoding="utf-8",
            )

            self.assertIn("RULESET_INDEX_ROLE_COLLISION", issue_codes(project))

    def test_ruleset_checks_managed_entries_scoping_indexed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            nested_entry = project / ".planning/decisions/AGENTS.md"
            nested_entry.write_text(
                "# Scoped instructions\n\n"
                "<!-- project-memory:start schema=1 -->\n"
                "Read `.planning/context.md` before work.\n"
                "<!-- project-memory:end -->\n",
                encoding="utf-8",
            )

            issues = validator.validate_project(project)
            self.assertTrue(
                any(
                    issue.code == "ENTRY_CONTEXT_RULESET_MISMATCH"
                    and issue.path == ".planning/decisions/AGENTS.md"
                    for issue in issues
                ),
                issues,
            )

    def test_commented_context_pointer_does_not_satisfy_managed_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            entry = project / "AGENTS.md"
            entry.write_text(
                "# Agent instructions\n\n"
                "<!-- project-memory:start schema=1 -->\n"
                "<!-- Read .planning/context.md before work. -->\n"
                "Follow the visible project instructions.\n"
                "<!-- project-memory:end -->\n",
                encoding="utf-8",
            )

            self.assertIn("ENTRY_CONTEXT_LINK_MISSING", issue_codes(project))

    def test_fenced_contract_examples_do_not_enable_ruleset_or_add_entry_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            context = project / ".planning/context.md"
            hidden_metadata = (
                "````md\n"
                "```md\n"
                "- Project Memory schema: 2\n"
                "- Project Memory ruleset: 1\n"
                "## Document index\n"
                "| Document | Purpose |\n|---|---|\n"
                "| `.planning/missing-hidden.md` | Example |\n"
                "```\n"
                "````\n"
                "<!--\n"
                "- Project Memory schema: 2\n"
                "- Project Memory ruleset: 1\n"
                "## Document index\n"
                "| Document | Purpose |\n|---|---|\n"
                "| `.planning/missing-commented.md` | Example |\n"
                "-->\n\n"
            )
            context.write_text(
                hidden_metadata
                + context.read_text(encoding="utf-8")
                + "\n```md\n- Project Memory schema: 2\n"
                "- Project Memory ruleset: 1\n```\n"
                "<!--\n- Project Memory schema: 2\n"
                "- Project Memory ruleset: 1\n"
                "## Document index\n"
                "| Role | Document |\n|---|---|\n"
                "| stable-intent | `.planning/context.md` |\n"
                "-->\n",
                encoding="utf-8",
            )
            entry = project / "AGENTS.md"
            entry.write_text(
                entry.read_text(encoding="utf-8")
                + "\n```md\n<!-- project-memory:start schema=1 ruleset=1 -->\n"
                "Example only.\n<!-- project-memory:end -->\n```\n",
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))
            health = validator.validate_project(project, health=True)
            self.assertEqual(
                {"RULESET_NOT_ENABLED": "NOTICE"},
                {issue.code: issue.severity for issue in health},
            )

    def test_nested_headings_do_not_satisfy_state_action_or_completion_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            (project / ".planning/state.md").write_text(
                "# State\n\n- Status: active\n\n"
                "## Just completed\n\n"
                "Completion signal: the previous task passed.\n\n"
                "## Exact next step\n\n### Details\n\n"
                "## Completion signal\n\n### Evidence\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("STATE_NEXT_STEP_MISSING", codes)
            self.assertIn("STATE_COMPLETION_SIGNAL_MISSING", codes)

    def test_historical_nested_state_does_not_mask_empty_current_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            (project / ".planning/state.md").write_text(
                "# State\n\n- Status: active\n\n"
                "## Historical snapshot\n\n"
                "### Exact next step\n\n1. Completed old action.\n\n"
                "Completion signal: old evidence exists.\n\n"
                "## Exact next step\n\n"
                "## Completion signal\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("STATE_NEXT_STEP_MISSING", codes)
            self.assertIn("STATE_COMPLETION_SIGNAL_MISSING", codes)

    def test_commonmark_heading_and_fence_indentation_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            for relative in (
                ".planning/context.md",
                ".planning/state.md",
                ".planning/release-log.md",
            ):
                path = project / relative
                path.write_text(
                    "\n".join(
                        f"   {line}" if line.startswith("#") else line
                        for line in path.read_text(encoding="utf-8").splitlines()
                    )
                    + "\n",
                    encoding="utf-8",
                )

            self.assertEqual([], validator.validate_project(project))

            context = project / ".planning/context.md"
            context.write_text(
                "    ```md\n"
                "- Project Memory ruleset: 2\n"
                "    ```\n"
                + context.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            self.assertIn("CONTEXT_RULESET_MULTIPLE", issue_codes(project))

    def test_ruleset_enforces_release_order_and_completion_signal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            release_log = project / ".planning/release-log.md"
            release_log.write_text(
                "# History\n\n## 2026-08-10 Older\n\n- First.\n\n"
                "## 2026-08-20 Newer\n\n- Second.\n",
                encoding="utf-8",
            )
            state = project / ".planning/state.md"
            state.write_text(
                "# State\n\n- Status: paused\n\n## Exact next step\n\n1. Resume it.\n",
                encoding="utf-8",
            )

            codes = issue_codes(project)
            self.assertIn("RELEASE_LOG_DATE_ORDER", codes)
            self.assertIn("STATE_COMPLETION_SIGNAL_MISSING", codes)

            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "\n- Project Memory ruleset: 1", ""
                ),
                encoding="utf-8",
            )
            entry = project / "AGENTS.md"
            entry.write_text(
                entry.read_text(encoding="utf-8").replace(" ruleset=1", ""),
                encoding="utf-8",
            )
            legacy_codes = issue_codes(project)
            self.assertNotIn("RELEASE_LOG_DATE_ORDER", legacy_codes)
            self.assertNotIn("STATE_COMPLETION_SIGNAL_MISSING", legacy_codes)

    def test_release_order_compares_peer_entries_not_nested_dated_headings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            (project / ".planning/release-log.md").write_text(
                "# History\n\n"
                "## 2026-09-02 Newer entry\n\n"
                "### 2026-08-01 Nested evidence date\n\n"
                "## 2026-09-01 Older entry\n",
                encoding="utf-8",
            )

            self.assertNotIn("RELEASE_LOG_DATE_ORDER", issue_codes(project))

    def test_closing_heading_hashes_have_the_same_contract_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            (project / ".planning/release-log.md").write_text(
                "# History #\n\n"
                "## 2026-08-10 Older ##\n\n"
                "## 2026-08-20 Newer ##\n",
                encoding="utf-8",
            )
            (project / ".planning/state.md").write_text(
                "# State #\n\n- Status: active\n\n"
                "## Exact next step ##\n\n1. Resume the task.\n\n"
                "## Completion signal ##\n\nThe named verification passes.\n",
                encoding="utf-8",
            )
            (project / ".planning/topic.md").write_text(
                "# Topic #\n\n## 10 Extension ##\n\n## 5 Core ##\n",
                encoding="utf-8",
            )

            issues = validator.validate_project(project, health=True)
            codes = {issue.code for issue in issues}
            self.assertIn("RELEASE_LOG_DATE_ORDER", codes)
            self.assertIn("NUMERIC_HEADING_REGRESSION", codes)
            self.assertNotIn("STATE_COMPLETION_SIGNAL_MISSING", codes)

    def test_health_checks_are_advisory_and_default_validation_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n## 2026-08-25 Production release\n\n- PID: 1234\n",
                encoding="utf-8",
            )
            topic = project / ".planning/topic.md"
            topic.write_text(
                "# Topic\n\n## 10 Extension\n\nText.\n\n## 5.4 Core\n\nText.\n",
                encoding="utf-8",
            )

            self.assertEqual([], validator.validate_project(project))
            issues = validator.validate_project(project, health=True)
            observed = {issue.code: issue.severity for issue in issues}
            self.assertEqual("REVIEW", observed["CONTEXT_RELEASE_HEADING"])
            self.assertEqual("REVIEW", observed["NUMERIC_HEADING_REGRESSION"])
            self.assertFalse(any(issue.severity == "ERROR" for issue in issues))

    def test_health_thresholds_keep_size_warning_and_density_review_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")
            padding = "\n".join(f"Stable note {index}." for index in range(1, 390))
            context.write_text(original + "\n" + padding + "\n", encoding="utf-8")

            size_issues = validator.validate_project(project, health=True)
            size = next(
                issue for issue in size_issues if issue.code == "CONTEXT_SIZE_BUDGET"
            )
            self.assertEqual("WARNING", size.severity)

            volatile = "\n".join(f"- PID {index}: temporary" for index in range(8))
            context.write_text(original + "\n" + volatile + "\n", encoding="utf-8")
            density_issues = validator.validate_project(project, health=True)
            density = next(
                issue
                for issue in density_issues
                if issue.code == "CONTEXT_VOLATILE_DENSITY"
            )
            self.assertEqual("REVIEW", density.severity)

    def test_health_budget_boundaries_are_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")

            base_lines = original.splitlines()
            exact_lines = "\n".join(
                base_lines + ["Stable padding."] * (400 - len(base_lines))
            ) + "\n"
            self.assertEqual(400, len(exact_lines.splitlines()))
            context.write_text(exact_lines, encoding="utf-8")
            self.assertNotIn(
                "CONTEXT_SIZE_BUDGET",
                {issue.code for issue in validator.validate_project(project, health=True)},
            )
            context.write_text(exact_lines + "Stable line 401.\n", encoding="utf-8")
            self.assertEqual(
                "WARNING",
                next(
                    issue.severity
                    for issue in validator.validate_project(project, health=True)
                    if issue.code == "CONTEXT_SIZE_BUDGET"
                ),
            )

            byte_padding = 65_536 - len(original.encode("utf-8"))
            self.assertGreater(byte_padding, 0)
            exact_bytes = original + ("x" * byte_padding)
            self.assertEqual(65_536, len(exact_bytes.encode("utf-8")))
            context.write_text(exact_bytes, encoding="utf-8")
            self.assertNotIn(
                "CONTEXT_SIZE_BUDGET",
                {issue.code for issue in validator.validate_project(project, health=True)},
            )
            context.write_text(exact_bytes + "x", encoding="utf-8")
            self.assertEqual(
                "WARNING",
                next(
                    issue.severity
                    for issue in validator.validate_project(project, health=True)
                    if issue.code == "CONTEXT_SIZE_BUDGET"
                ),
            )

    def test_volatile_density_requires_both_exact_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")
            base_prose = [line for line in original.splitlines() if line.strip()]
            self.assertFalse(any(validator.VOLATILE_LINE_RE.search(line) for line in base_prose))

            def density_text(volatile_count: int, total_count: int) -> str:
                stable_count = total_count - len(base_prose) - volatile_count
                self.assertGreaterEqual(stable_count, 0)
                additions = [f"- PID {index}: temporary" for index in range(volatile_count)]
                additions += [f"- Stable note {index}." for index in range(stable_count)]
                return original + "\n" + "\n".join(additions) + "\n"

            context.write_text(density_text(7, 50), encoding="utf-8")
            self.assertNotIn(
                "CONTEXT_VOLATILE_DENSITY",
                {issue.code for issue in validator.validate_project(project, health=True)},
            )

            context.write_text(density_text(8, 100), encoding="utf-8")
            _, checker, issues = validator._validate_with_report(project, health=True)
            self.assertEqual(
                "REVIEW",
                next(issue.severity for issue in issues if issue.code == "CONTEXT_VOLATILE_DENSITY"),
            )
            density = next(
                record
                for record in checker.health_measurements
                if record["code"] == "CONTEXT_VOLATILE_DENSITY"
            )
            self.assertEqual(800, density["values"]["density_basis_points"])
            self.assertEqual(8, density["values"]["volatile_lines"])

            context.write_text(density_text(8, 101), encoding="utf-8")
            self.assertNotIn(
                "CONTEXT_VOLATILE_DENSITY",
                {issue.code for issue in validator.validate_project(project, health=True)},
            )

    def test_fenced_or_commented_examples_do_not_satisfy_or_trigger_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n```md\n## 2026-08-25 Production release\n```\n"
                + "\n<!--\n## 2026-08-26 Deployment status\n-->\n",
                encoding="utf-8",
            )
            release_log = project / ".planning/release-log.md"
            release_log.write_text(
                "# History\n\n## 2026-08-20 Current\n\n"
                "```md\n## 2026-08-30 Example only\n```\n\n"
                "<!--\n## 2026-08-31 Commented example\n-->\n\n"
                "## 2026-08-10 Older\n",
                encoding="utf-8",
            )
            topic = project / ".planning/topic.md"
            topic.write_text(
                "# Topic\n\n```md\n## 10 Example\n## 5.4 Example\n```\n",
                encoding="utf-8",
            )
            state = project / ".planning/state.md"
            state.write_text(
                "# State\n\n- Status: active\n\n## Exact next step\n\n"
                "1. Resume the real task.\n\n"
                "```md\nCompletion signal: example only.\n```\n",
                encoding="utf-8",
            )

            issues = validator.validate_project(project, health=True)
            codes = {issue.code for issue in issues}
            self.assertNotIn("CONTEXT_RELEASE_HEADING", codes)
            self.assertNotIn("RELEASE_LOG_DATE_ORDER", codes)
            self.assertNotIn("NUMERIC_HEADING_REGRESSION", codes)
            self.assertIn("STATE_COMPLETION_SIGNAL_MISSING", codes)

    def test_health_json_exposes_a_copyable_baseline_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(
                [
                    "ERROR",
                    "NOTICE",
                    "REVIEW",
                    "WARNING",
                ],
                sorted(payload["summary"]),
            )
            self.assertEqual(1, payload["format_version"])
            self.assertEqual("health", payload["mode"])
            self.assertFalse(payload["review_required"])
            self.assertTrue(payload["guard_passed"])
            self.assertEqual(1, payload["baseline_candidate"]["ruleset"])
            self.assertEqual(
                payload["measurements"],
                payload["baseline_candidate"]["measurements"],
            )
            self.assertEqual(
                payload["source_fingerprints"],
                payload["baseline_candidate"]["source_fingerprints"],
            )
            self.assertTrue(
                all(
                    len(record["sha256"]) == 64
                    for record in payload["source_fingerprints"]
                )
            )
            self.assertIsNone(payload["baseline"])

    def test_baseline_candidate_fingerprint_matches_the_measured_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            inspected = context.read_bytes()
            root, checker, issues = validator._validate_with_report(
                project,
                health=True,
            )

            context.write_text(
                context.read_text(encoding="utf-8") + "\n- Concurrent change.\n",
                encoding="utf-8",
            )
            payload = validator._json_payload(
                root=root,
                health=True,
                checker=checker,
                issues=issues,
            )
            context_measurement = next(
                record
                for record in payload["measurements"]
                if record["code"] == "CONTEXT_SIZE_BUDGET"
            )
            context_fingerprint = next(
                record
                for record in payload["source_fingerprints"]
                if record["path"] == ".planning/context.md"
            )

            self.assertEqual(len(inspected), context_measurement["values"]["bytes"])
            self.assertEqual(
                hashlib.sha256(inspected).hexdigest(),
                context_fingerprint["sha256"],
            )

    def test_one_validation_run_uses_one_cached_context_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            checker = validator.ProjectMemoryValidator(project.resolve(), health=True)
            original_read = checker._read_text
            context = project.resolve() / ".planning/context.md"
            context_reads = 0

            def counted_read(path: Path):
                nonlocal context_reads
                if path == context:
                    context_reads += 1
                return original_read(path)

            checker._read_text = counted_read
            self.assertEqual([], checker.run())
            self.assertEqual(1, context_reads)

    def test_baseline_candidate_is_suppressed_when_validation_has_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            (project / ".planning/release-log.md").unlink()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(1, completed.returncode)
            self.assertIsNone(payload["baseline_candidate"])

    def test_baseline_downgrades_existing_debt_and_blocks_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n## 2026-08-25 Production release\n\n- Temporary deployment.\n",
                encoding="utf-8",
            )
            candidate_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            candidate = json.loads(candidate_run.stdout)["baseline_candidate"]
            baseline_path = project / ".planning/health-baseline.json"
            baseline_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()

            accepted = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            accepted_payload = json.loads(accepted.stdout)
            self.assertEqual(0, accepted.returncode, accepted.stdout + accepted.stderr)
            self.assertTrue(accepted_payload["guard_passed"])
            self.assertEqual("NOTICE", accepted_payload["issues"][0]["severity"])
            self.assertEqual(
                hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
                accepted_payload["baseline"]["sha256"],
            )
            self.assertEqual(
                ".planning/health-baseline.json",
                accepted_payload["baseline"]["path"],
            )

            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n## 2026-08-26 Production release\n\n- Temporary deployment.\n",
                encoding="utf-8",
            )
            regressed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            regressed_payload = json.loads(regressed.stdout)
            self.assertEqual(1, regressed.returncode)
            self.assertFalse(regressed_payload["guard_passed"])
            self.assertTrue(regressed_payload["review_required"])
            self.assertEqual("review_required", regressed_payload["status"])
            self.assertTrue(
                any(
                    issue["code"] == "CONTEXT_RELEASE_HEADING"
                    and issue["severity"] == "REVIEW"
                    for issue in regressed_payload["issues"]
                )
            )

    def test_baseline_does_not_flag_ordinary_growth_below_size_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            candidate_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            candidate = json.loads(candidate_run.stdout)["baseline_candidate"]
            baseline_path = project / ".planning/health-baseline.json"
            baseline_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8") + "\n- One new stable constraint.\n",
                encoding="utf-8",
            )

            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(checked.stdout)
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
            self.assertFalse(payload["review_required"])
            self.assertFalse(
                any(
                    issue["code"] == "CONTEXT_SIZE_BUDGET"
                    for issue in payload["issues"]
                )
            )

    def test_baseline_allows_below_budget_growth_while_oversize_lines_improve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            base_lines = context.read_text(encoding="utf-8").splitlines()
            baseline_lines = base_lines + [""] * (410 - len(base_lines))
            context.write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")

            candidate_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            candidate = json.loads(candidate_run.stdout)["baseline_candidate"]
            baseline_path = project / ".planning/health-baseline.json"
            baseline_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()

            current_lines = (
                base_lines
                + [""] * (404 - len(base_lines))
                + ["Stable detail: " + "x" * 2_000]
            )
            context.write_text("\n".join(current_lines) + "\n", encoding="utf-8")
            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(checked.stdout)
            size_issue = next(
                issue
                for issue in payload["issues"]
                if issue["code"] == "CONTEXT_SIZE_BUDGET"
            )
            self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
            self.assertEqual("NOTICE", size_issue["severity"])
            self.assertFalse(payload["review_required"])

    def test_numeric_baseline_signature_includes_stable_section_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            topic = project / ".planning/scoped-numbering.md"
            topic.write_text(
                "# Topic\n\n## Alpha scope\n\n### 10 Later\n\n### 5 Earlier\n",
                encoding="utf-8",
            )
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/decisions/0001-storage.md`",
                    "`.planning/scoped-numbering.md`",
                ),
                encoding="utf-8",
            )

            candidate_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            candidate = json.loads(candidate_run.stdout)["baseline_candidate"]
            baseline_path = project / ".planning/health-baseline.json"
            baseline_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
            topic.write_text(
                topic.read_text(encoding="utf-8").replace(
                    "## Alpha scope",
                    "## Beta scope",
                ),
                encoding="utf-8",
            )

            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(checked.stdout)
            self.assertEqual(1, checked.returncode, checked.stdout + checked.stderr)
            self.assertTrue(payload["review_required"])
            self.assertTrue(
                any(
                    issue["code"] == "NUMERIC_HEADING_REGRESSION"
                    and "signature" in issue["message"]
                    for issue in payload["issues"]
                )
            )

    def test_baseline_detects_equal_count_finding_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n## 2026-08-25 Production release\n",
                encoding="utf-8",
            )
            candidate_run = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            candidate = json.loads(candidate_run.stdout)["baseline_candidate"]
            baseline_path = project / ".planning/health-baseline.json"
            baseline_path.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "2026-08-25 Production release",
                    "2026-08-26 Production release",
                ),
                encoding="utf-8",
            )

            checked = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    str(project),
                    "--health",
                    "--baseline",
                    ".planning/health-baseline.json",
                    "--baseline-sha256",
                    baseline_sha256,
                    "--format",
                    "json",
                ],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )
            payload = json.loads(checked.stdout)
            self.assertEqual(1, checked.returncode, checked.stdout + checked.stderr)
            self.assertTrue(payload["review_required"])
            self.assertTrue(
                any(
                    issue["code"] == "CONTEXT_RELEASE_HEADING"
                    and "signature" in issue["message"]
                    for issue in payload["issues"]
                )
            )

    def test_baseline_is_ruleset_only_and_cannot_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            project = temporary_path / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            baseline = project / ".planning/health-baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "ruleset": 1,
                        "measurements": [],
                        "source_fingerprints": [],
                    }
                ),
                encoding="utf-8",
            )
            baseline_sha256 = hashlib.sha256(baseline.read_bytes()).hexdigest()

            with self.assertRaises(validator.ValidationRuntimeError):
                validator.validate_project(
                    project,
                    health=True,
                    baseline=Path(".planning/health-baseline.json"),
                    baseline_sha256=baseline_sha256,
                )
            with self.assertRaises(validator.ValidationRuntimeError):
                validator.validate_project(
                    project,
                    health=True,
                    baseline=Path("../outside.json"),
                    baseline_sha256="0" * 64,
                )

    def test_baseline_path_and_expected_digest_are_an_indivisible_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            root, checker, issues = validator._validate_with_report(project, health=True)
            candidate = validator._json_payload(
                root=root,
                health=True,
                checker=checker,
                issues=issues,
            )["baseline_candidate"]
            baseline = project / ".planning/health-baseline.json"
            baseline.write_text(
                json.dumps(candidate, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            digest = hashlib.sha256(baseline.read_bytes()).hexdigest()

            for kwargs in (
                {"baseline": Path(".planning/health-baseline.json")},
                {"baseline_sha256": digest},
                {
                    "baseline": Path(".planning/health-baseline.json"),
                    "baseline_sha256": "0" * 64,
                },
            ):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises(validator.ValidationRuntimeError):
                        validator.validate_project(project, health=True, **kwargs)

    def test_baseline_rejects_nonportable_paths_and_inconsistent_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            baseline = project / ".planning/health-baseline.json"
            context_hash = hashlib.sha256(
                (project / ".planning/context.md").read_bytes()
            ).hexdigest()

            def write_baseline(path: str, values: dict[str, int]) -> None:
                baseline.write_text(
                    json.dumps(
                        {
                            "format_version": 1,
                            "ruleset": 1,
                            "measurements": [
                                {
                                    "code": "CONTEXT_VOLATILE_DENSITY",
                                    "path": path,
                                    "values": values,
                                    "signatures": [],
                                }
                            ],
                            "source_fingerprints": [
                                {"path": path, "sha256": context_hash}
                            ],
                        }
                    ),
                    encoding="utf-8",
                )

            write_baseline(
                ".planning\\context.md",
                {
                    "density_basis_points": 0,
                    "prose_lines": 1,
                    "volatile_lines": 0,
                },
            )
            with self.assertRaises(validator.ValidationRuntimeError):
                validator.validate_project(
                    project,
                    health=True,
                    baseline=Path(".planning/health-baseline.json"),
                    baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
                )

            write_baseline(
                ".planning/context.md",
                {
                    "density_basis_points": 10_001,
                    "prose_lines": 1,
                    "volatile_lines": 2,
                },
            )
            with self.assertRaises(validator.ValidationRuntimeError):
                validator.validate_project(
                    project,
                    health=True,
                    baseline=Path(".planning/health-baseline.json"),
                    baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
                )

    def test_malformed_baseline_paths_fail_as_runtime_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURES / "valid_project", project)
            enable_ruleset(project)
            baseline = project / ".planning/health-baseline.json"
            context_hash = hashlib.sha256(
                (project / ".planning/context.md").read_bytes()
            ).hexdigest()
            valid_measurement = {
                "code": "CONTEXT_RELEASE_HEADING",
                "path": ".planning/context.md",
                "values": {"count": 0},
                "signatures": [],
            }
            invalid_paths = (
                ".planning/\u0000context.md",
                ".planning/\u0009context.md",
                ".planning/\u000acontext.md",
                ".planning/\ud800context.md",
                ".planning/\udfffcontext.md",
            )
            cases = [
                (
                    "measurement code type",
                    [dict(valid_measurement, code=[])],
                    [],
                )
            ]
            for invalid_path in invalid_paths:
                cases.extend(
                    (
                        (
                            "measurement path",
                            [dict(valid_measurement, path=invalid_path)],
                            [],
                        ),
                        (
                            "source fingerprint path",
                            [valid_measurement],
                            [{"path": invalid_path, "sha256": context_hash}],
                        ),
                    )
                )

            for description, measurements, source_fingerprints in cases:
                with self.subTest(description=description, payload_path=(
                    measurements[0]["path"]
                    if description == "measurement path"
                    else source_fingerprints[0]["path"]
                    if source_fingerprints
                    else None
                )):
                    payload = {
                        "format_version": 1,
                        "ruleset": 1,
                        "measurements": measurements,
                        "source_fingerprints": source_fingerprints,
                    }
                    baseline.write_text(
                        json.dumps(payload),
                        encoding="utf-8",
                    )
                    digest = hashlib.sha256(baseline.read_bytes()).hexdigest()
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(SCRIPT),
                            str(project),
                            "--health",
                            "--baseline",
                            ".planning/health-baseline.json",
                            "--baseline-sha256",
                            digest,
                            "--format",
                            "json",
                        ],
                        cwd=project,
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
                    result = json.loads(completed.stdout)
                    self.assertEqual("VALIDATOR_RUNTIME", result["issues"][0]["code"])
                    self.assertEqual("failed", result["status"])
                    self.assertFalse(result["valid"])
                    self.assertFalse(result["guard_passed"])
                    self.assertEqual("", completed.stderr)

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
