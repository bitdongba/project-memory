from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
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
    / "route_project_memory.py"
)
FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "health"
    / "healthy-ruleset"
)
LEGACY_FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "health"
    / "healthy-legacy"
)


def load_router():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("route_project_memory", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


router = load_router()
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


class ProjectMemoryRouterTests(unittest.TestCase):
    def test_each_kind_resolves_to_one_indexed_primary_route(self) -> None:
        cases = {
            "stable-intent": (".planning/context.md", True, None),
            "protocol-setting": (".planning/context.md", True, None),
            "resumable-state": (".planning/state.md", False, None),
            "historical-event": (".planning/release-log.md", False, None),
            "topic-detail": (
                ".planning/topics/interface-contract.md",
                False,
                ".planning/topics/interface-contract.md",
            ),
        }

        for kind, (path, context_allowed, topic_path) in cases.items():
            with self.subTest(kind=kind):
                result = router.route_project_memory(FIXTURE, kind, topic_path)
                self.assertEqual(kind, result.classification)
                self.assertEqual(kind, result.primary_role)
                self.assertEqual(path, result.primary_path)
                self.assertEqual(context_allowed, result.context_allowed)
                self.assertTrue(result.read_only)
                self.assertFalse(result.authorizes_write)
                self.assertIn("does not authorize", result.permission_note)

    def test_route_comes_from_typed_index_instead_of_a_filename_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    ".planning/release-log.md",
                    ".planning/timeline.md",
                ),
                encoding="utf-8",
            )
            (project / ".planning/timeline.md").write_text(
                "# Timeline\n",
                encoding="utf-8",
            )

            result = router.route_project_memory(project, "historical-event")

            self.assertEqual(".planning/timeline.md", result.primary_path)

    def test_markdown_index_links_are_relative_to_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/topics/interface-contract.md`",
                    "[Interface](topics/interface-contract.md)",
                ),
                encoding="utf-8",
            )

            result = router.route_project_memory(
                project,
                "topic-detail",
                ".planning/topics/interface-contract.md",
            )

            self.assertEqual(
                ".planning/topics/interface-contract.md",
                result.primary_path,
            )

    def test_balanced_and_escaped_index_links_validate_and_route_identically(self) -> None:
        cases = (
            ("topics/api(v2).md", "api(v2).md"),
            ("topics/api((v2)).md", "api((v2)).md"),
            (r"topics/api\(v2\).md", "api(v2).md"),
            (r"topics/api\)v2\(.md", "api)v2(.md"),
            ("topics/api%28v2%29.md", "api(v2).md"),
            ("topics/api%20v2.md", "api v2.md"),
            ("<topics/api v2.md>", "api v2.md"),
            (r"topics/api\_v2.md", "api_v2.md"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")
            for destination, filename in cases:
                with self.subTest(destination=destination):
                    canonical = ".planning/topics/" + filename
                    target = project / canonical
                    target.write_text("# API\n", encoding="utf-8")
                    context.write_text(
                        original.replace(
                            "`.planning/topics/interface-contract.md`",
                            f'[API]({destination} "Current reference")',
                        ),
                        encoding="utf-8",
                    )
                    self.assertEqual([], validator.validate_project(project))
                    result = router.route_project_memory(project, "topic-detail", canonical)
                    self.assertEqual(canonical, result.primary_path)
                    target.unlink()
                    self.assertIn(
                        "RULESET_INDEX_TARGET_MISSING",
                        {i.code for i in validator.validate_project(project)},
                    )
                    with self.assertRaises(router.RouteReviewRequired) as raised:
                        router.route_project_memory(project, "topic-detail", canonical)
                    self.assertEqual("CANONICAL_TARGET_MISSING", raised.exception.failure.code)

    def test_decoded_markdown_index_paths_keep_unsafe_path_checks(self) -> None:
        destinations = (
            "../../outside(v2).md",
            r"..\/..\/outside\(v2\).md",
            "%2e%2e/%2e%2e/outside%28v2%29.md",
            r"topics\\api.md",
            "topics%5capi.md",
            "<../../outside(v2).md>",
        )
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")
            for destination in destinations:
                with self.subTest(destination=destination):
                    context.write_text(
                        original.replace(
                            "`.planning/topics/interface-contract.md`",
                            f"[API]({destination})",
                        ),
                        encoding="utf-8",
                    )
                    self.assertIn(
                        "RULESET_INDEX_PATH_INVALID",
                        {i.code for i in validator.validate_project(project)},
                    )
                    with self.assertRaises(router.RouteInputError) as raised:
                        router.route_project_memory(project, "stable-intent")
                    self.assertEqual("INDEX_PATH_UNSAFE", raised.exception.failure.code)

    def test_commonmark_indented_index_heading_is_recognized(self) -> None:
        for indentation in (" ", "  ", "   "):
            with self.subTest(indentation=len(indentation)):
                with tempfile.TemporaryDirectory() as temporary:
                    project = Path(temporary) / "project"
                    shutil.copytree(FIXTURE, project)
                    context = project / ".planning/context.md"
                    context.write_text(
                        context.read_text(encoding="utf-8").replace(
                            "## Document index",
                            f"{indentation}## Document index",
                        ),
                        encoding="utf-8",
                    )

                    result = router.route_project_memory(project, "stable-intent")

                    self.assertEqual(".planning/context.md", result.primary_path)

    def test_four_space_indented_backticks_do_not_open_a_fence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                "    ```md\n" + context.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            result = router.route_project_memory(project, "stable-intent")

            self.assertEqual(".planning/context.md", result.primary_path)

    def test_router_requires_supported_schema_as_well_as_ruleset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "Project Memory schema: 1",
                    "Project Memory schema: 2",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(router.RouteReviewRequired) as raised:
                router.route_project_memory(project, "stable-intent")

            self.assertEqual("SCHEMA_UNSUPPORTED", raised.exception.failure.code)

    def test_legacy_untyped_index_requires_review_instead_of_guessing(self) -> None:
        with self.assertRaises(router.RouteReviewRequired) as raised:
            router.route_project_memory(LEGACY_FIXTURE, "stable-intent")

        self.assertEqual("RULESET_NOT_ENABLED", raised.exception.failure.code)
        self.assertTrue(raised.exception.failure.review_required)
        self.assertTrue(raised.exception.failure.context_allowed)

    def test_fenced_contract_examples_are_not_active_routing_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(LEGACY_FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                "````md\n"
                "```md\n"
                "- Project Memory ruleset: 1\n"
                "## Document index\n\n"
                "| Role | Document |\n|---|---|\n"
                "| stable-intent | `.planning/context.md` |\n"
                "```\n"
                "````\n"
                + context.read_text(encoding="utf-8")
                + "\n```md\n- Project Memory ruleset: 1\n"
                "## Document index\n\n"
                "| Role | Document |\n|---|---|\n"
                "| stable-intent | `.planning/context.md` |\n```\n"
                "<!--\n- Project Memory ruleset: 1\n"
                "## Document index\n\n"
                "| Role | Document |\n|---|---|\n"
                "| stable-intent | `.planning/context.md` |\n"
                "-->\n",
                encoding="utf-8",
            )

            with self.assertRaises(router.RouteReviewRequired) as raised:
                router.route_project_memory(project, "stable-intent")

            self.assertEqual("RULESET_NOT_ENABLED", raised.exception.failure.code)

    def test_missing_or_ambiguous_index_routes_require_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            original = context.read_text(encoding="utf-8")

            context.write_text(
                original.replace(
                    "| resumable-state | `.planning/state.md` | Replace-in-place handoff | active |\n",
                    "",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(router.RouteReviewRequired) as missing:
                router.route_project_memory(project, "resumable-state")
            self.assertEqual("CANONICAL_ROUTE_MISSING", missing.exception.failure.code)

            context.write_text(
                original.replace(
                    "| historical-event | `.planning/release-log.md` | Meaningful history | canonical |",
                    "| historical-event | `.planning/release-log.md` | Meaningful history | canonical |\n"
                    "| historical-event | `.planning/release-log.md` | Duplicate route | canonical |",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(router.RouteReviewRequired) as ambiguous:
                router.route_project_memory(project, "historical-event")
            self.assertEqual("CANONICAL_ROUTE_AMBIGUOUS", ambiguous.exception.failure.code)

    def test_blank_line_ends_typed_table_and_orphan_role_rows_fail_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "| topic-detail | `.planning/topics/interface-contract.md`",
                    "\n| topic-detail | `.planning/topics/interface-contract.md`",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(router.RouteReviewRequired) as raised:
                router.route_project_memory(project, "stable-intent")

            self.assertEqual(
                "DOCUMENT_INDEX_TABLE_INVALID",
                raised.exception.failure.code,
            )

            context.write_text(
                (FIXTURE / ".planning/context.md")
                .read_text(encoding="utf-8")
                .replace(
                    "| topic-detail | `.planning/topics/interface-contract.md`",
                    "```md\nexample\n```\n"
                    "| topic-detail | `.planning/topics/interface-contract.md`",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(router.RouteReviewRequired) as fenced:
                router.route_project_memory(project, "stable-intent")
            self.assertEqual(
                "DOCUMENT_INDEX_TABLE_INVALID",
                fenced.exception.failure.code,
            )

    def test_separate_non_role_table_after_index_does_not_create_a_false_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "\n| Label | Value |\n|---|---|\n| owner | team |\n",
                encoding="utf-8",
            )

            result = router.route_project_memory(project, "stable-intent")

            self.assertEqual(".planning/context.md", result.primary_path)

    def test_stable_and_protocol_routes_are_fixed_to_canonical_context(self) -> None:
        cases = {
            "stable-intent": (
                "| stable-intent | `.planning/context.md`",
                "| stable-intent | `.planning/stable.md`",
                ".planning/stable.md",
            ),
            "protocol-setting": (
                "| protocol-setting | `.planning/context.md`",
                "| protocol-setting | `.planning/protocol.md`",
                ".planning/protocol.md",
            ),
        }
        for kind, (old_row, new_row, custom_path) in cases.items():
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as temporary:
                    project = Path(temporary) / "project"
                    shutil.copytree(FIXTURE, project)
                    (project / custom_path).write_text("# Custom\n", encoding="utf-8")
                    context = project / ".planning/context.md"
                    context.write_text(
                        context.read_text(encoding="utf-8").replace(old_row, new_row),
                        encoding="utf-8",
                    )

                    with self.assertRaises(router.RouteReviewRequired) as raised:
                        router.route_project_memory(project, kind)

                    self.assertEqual(
                        "CANONICAL_ROUTE_INVALID",
                        raised.exception.failure.code,
                    )

    def test_topic_path_is_required_safe_and_exactly_indexed(self) -> None:
        with self.assertRaises(router.RouteReviewRequired) as missing:
            router.route_project_memory(FIXTURE, "topic-detail")
        self.assertEqual("TOPIC_PATH_REQUIRED", missing.exception.failure.code)

        for unsafe in (
            "../outside.md",
            "/tmp/outside.md",
            "C:\\outside.md",
            ".planning/../outside.md",
            " .planning/topics/interface-contract.md ",
            ".planning/topics/control\x00.md",
            ".planning/topics/control\x01.md",
            ".planning/topics/control\t.md",
            ".planning/topics/control\n.md",
            ".planning/topics/control\x1f.md",
            ".planning/topics/control\x7f.md",
            ".planning/topics/surrogate\ud800.md",
            ".planning/topics/surrogate\udfff.md",
        ):
            with self.subTest(path=unsafe):
                with self.assertRaises(router.RouteReviewRequired) as raised:
                    router.route_project_memory(FIXTURE, "topic-detail", unsafe)
                self.assertEqual("TOPIC_PATH_INVALID", raised.exception.failure.code)

        with self.assertRaises(router.RouteReviewRequired) as unindexed:
            router.route_project_memory(FIXTURE, "topic-detail", ".planning/other.md")
        self.assertEqual("CANONICAL_ROUTE_MISSING", unindexed.exception.failure.code)

    def test_index_paths_with_padding_are_not_normalized_silently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/topics/interface-contract.md`",
                    "` .planning/topics/interface-contract.md `",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(router.RouteInputError) as raised:
                router.route_project_memory(
                    project,
                    "topic-detail",
                    ".planning/topics/interface-contract.md",
                )
            self.assertEqual("INDEX_PATH_UNSAFE", raised.exception.failure.code)

    def test_index_paths_reject_controls_before_url_or_path_normalization(self) -> None:
        for character in ("\x00", "\x01", "\t", "\x7f"):
            with self.subTest(character=ascii(character)):
                with tempfile.TemporaryDirectory() as temporary:
                    project = Path(temporary) / "project"
                    shutil.copytree(FIXTURE, project)
                    context = project / ".planning/context.md"
                    context.write_text(
                        context.read_text(encoding="utf-8").replace(
                            ".planning/topics/interface-contract.md",
                            f".planning/topics/{character}interface-contract.md",
                        ),
                        encoding="utf-8",
                    )

                    with self.assertRaises(router.RouteInputError) as raised:
                        router.route_project_memory(project, "stable-intent")

                    self.assertEqual("INDEX_PATH_UNSAFE", raised.exception.failure.code)

    def test_empty_state_directory_does_not_create_a_phantom_state_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "| resumable-state | `.planning/state.md` | Replace-in-place handoff | active |\n",
                    "",
                ),
                encoding="utf-8",
            )
            (project / ".planning/state.md").unlink()
            (project / ".planning/state").mkdir()

            result = router.route_project_memory(project, "stable-intent")
            self.assertEqual(".planning/context.md", result.primary_path)

            (project / ".planning/state/workstream.md").write_text(
                "# Workstream\n\n- Status: active\n",
                encoding="utf-8",
            )
            with self.assertRaises(router.RouteReviewRequired) as raised:
                router.route_project_memory(project, "stable-intent")
            self.assertEqual("CANONICAL_ROUTE_MISSING", raised.exception.failure.code)

    def test_indexed_symlink_cannot_escape_the_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / "project"
            outside = base / "outside.md"
            shutil.copytree(FIXTURE, project)
            outside.write_text("# Outside\n", encoding="utf-8")
            topic = project / ".planning/topics/interface-contract.md"
            topic.unlink()
            try:
                topic.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(router.RouteInputError) as raised:
                router.route_project_memory(
                    project,
                    "topic-detail",
                    ".planning/topics/interface-contract.md",
                )
            self.assertEqual("INDEX_PATH_UNSAFE", raised.exception.failure.code)

    def test_internal_symlink_alias_cannot_hide_a_role_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            shutil.copytree(FIXTURE, project)
            alias = project / ".planning/topics/history-alias.md"
            try:
                alias.symlink_to("../release-log.md")
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            context = project / ".planning/context.md"
            context.write_text(
                context.read_text(encoding="utf-8").replace(
                    "`.planning/topics/interface-contract.md`",
                    "`.planning/topics/history-alias.md`",
                ),
                encoding="utf-8",
            )

            with self.assertRaises(router.RouteReviewRequired) as raised:
                router.route_project_memory(project, "stable-intent")
            self.assertEqual("CANONICAL_ROLE_COLLISION", raised.exception.failure.code)

    def test_cli_supports_stable_text_and_json_output(self) -> None:
        text_result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), str(FIXTURE), "--kind", "stable-intent"],
            check=False,
            capture_output=True,
            text=True,
        )
        json_command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            str(FIXTURE),
            "--kind",
            "historical-event",
            "--format",
            "json",
        ]
        first_json = subprocess.run(json_command, check=False, capture_output=True, text=True)
        second_json = subprocess.run(json_command, check=False, capture_output=True, text=True)

        self.assertEqual(0, text_result.returncode, text_result.stderr)
        self.assertIn("primary_path=.planning/context.md", text_result.stdout)
        self.assertIn("context_allowed=true", text_result.stdout)
        self.assertIn("authorizes_write=false", text_result.stdout)
        self.assertEqual(0, first_json.returncode, first_json.stderr)
        self.assertEqual(first_json.stdout, second_json.stdout)
        payload = json.loads(first_json.stdout)
        self.assertEqual(1, payload["format_version"])
        self.assertEqual("routed", payload["status"])
        self.assertEqual(".planning/release-log.md", payload["primary_path"])
        self.assertFalse(payload["context_allowed"])
        self.assertFalse(payload["authorizes_write"])
        self.assertTrue(payload["read_only"])

    def test_structured_errors_are_stable_and_do_not_reflect_invalid_input(self) -> None:
        secret_kind = "unsupported-private-value"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(FIXTURE),
                "--kind",
                secret_kind,
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(2, result.returncode)
        self.assertNotIn(secret_kind, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("INVALID_KIND", payload["code"])
        self.assertEqual("error", payload["status"])
        self.assertFalse(payload["context_allowed"])
        self.assertFalse(payload["authorizes_write"])

        secret_path = "../private-location.md"
        topic_result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(FIXTURE),
                "--kind",
                "topic-detail",
                "--topic-path",
                secret_path,
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(1, topic_result.returncode)
        self.assertNotIn(secret_path, topic_result.stdout + topic_result.stderr)
        topic_payload = json.loads(topic_result.stdout)
        self.assertEqual("TOPIC_PATH_INVALID", topic_payload["code"])
        self.assertEqual("review_required", topic_payload["status"])

    def test_control_and_surrogate_paths_have_stable_json_failures(self) -> None:
        cases = (
            (".planning/topics/control\x7f.md", 1, "TOPIC_PATH_INVALID"),
            (".planning/topics/surrogate\ud800.md", 1, "TOPIC_PATH_INVALID"),
            ("bad\x00root", 2, "PROJECT_ROOT_INVALID"),
            ("bad\ud800root", 2, "PROJECT_ROOT_INVALID"),
        )
        observed = []
        for raw_path, expected_exit, expected_code in cases:
            with self.subTest(path=ascii(raw_path)):
                argv = [
                    str(FIXTURE) if expected_code == "TOPIC_PATH_INVALID" else raw_path,
                    "--kind",
                    "topic-detail" if expected_code == "TOPIC_PATH_INVALID" else "stable-intent",
                    "--format",
                    "json",
                ]
                if expected_code == "TOPIC_PATH_INVALID":
                    argv.extend(("--topic-path", raw_path))
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = router.main(argv)

                self.assertEqual(expected_exit, exit_code)
                self.assertEqual("", stderr.getvalue())
                payload = json.loads(stdout.getvalue())
                self.assertEqual(expected_code, payload["code"])
                self.assertFalse(payload["authorizes_write"])
                observed.append(stdout.getvalue())

        repeated_stdout = io.StringIO()
        with contextlib.redirect_stdout(repeated_stdout):
            repeated_exit = router.main(
                [
                    str(FIXTURE),
                    "--kind",
                    "topic-detail",
                    "--topic-path",
                    ".planning/topics/surrogate\ud800.md",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(1, repeated_exit)
        self.assertEqual(observed[1], repeated_stdout.getvalue())

    def test_cli_is_strictly_read_only(self) -> None:
        before = tree_fingerprint(FIXTURE)
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                str(FIXTURE),
                "--kind",
                "topic-detail",
                "--topic-path",
                ".planning/topics/interface-contract.md",
                "--format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(before, tree_fingerprint(FIXTURE))


if __name__ == "__main__":
    unittest.main()
