from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "project-memory"


def load_build_module():
    path = REPO / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("build_release", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryContractTests(unittest.TestCase):
    def test_skill_frontmatter_and_name(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        fields = {}
        for line in match.group(1).splitlines():
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
        self.assertEqual(set(fields), {"name", "description"})
        self.assertEqual(fields["name"], SKILL.name)
        for trigger in ("audit", "migrate", "evolve", ".planning"):
            self.assertIn(trigger, fields["description"])

    def test_skill_references_exist(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^]]+\]\((references/[^)#]+\.md)\)", text)
        self.assertGreaterEqual(len(links), 5)
        for link in links:
            self.assertTrue((SKILL / link).is_file(), link)

    def test_new_and_existing_project_guides_are_discoverable(self):
        english = REPO / "docs" / "workflows.md"
        chinese = REPO / "docs" / "workflows.zh-CN.md"
        self.assertTrue(english.is_file())
        self.assertTrue(chinese.is_file())
        self.assertIn("(docs/workflows.md)", (REPO / "README.md").read_text(encoding="utf-8"))
        self.assertIn(
            "(docs/workflows.zh-CN.md)",
            (REPO / "README.zh-CN.md").read_text(encoding="utf-8"),
        )

    def test_skill_routes_directly_to_initialization_protocol(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r"\[[^]]+\]\(references/initialization\.md\)",
        )

    def test_openai_ui_metadata_contract(self):
        text = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        short = re.search(r'^\s*short_description:\s*"([^"]+)"\s*$', text, re.MULTILINE)
        prompt = re.search(r'^\s*default_prompt:\s*"([^"]+)"\s*$', text, re.MULTILINE)
        self.assertIsNotNone(short)
        self.assertIsNotNone(prompt)
        self.assertGreaterEqual(len(short.group(1)), 25)
        self.assertLessEqual(len(short.group(1)), 64)
        self.assertIn("$project-memory", prompt.group(1))

    def test_long_references_have_contents(self):
        for path in (SKILL / "references").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            if len(text.splitlines()) > 100:
                self.assertIn("## Contents", text, path.name)

    def test_manifests_share_identity_and_version(self):
        codex = json.loads((REPO / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(codex["name"], "project-memory")
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], codex["version"])
        self.assertEqual(codex["skills"], "./skills/")
        self.assertRegex(codex["version"], r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
        self.assertEqual(codex.get("license"), "MIT")

    def test_entry_markers_and_schema_are_consistent(self):
        entry = (SKILL / "references" / "entrypoints.md").read_text(encoding="utf-8")
        context = (SKILL / "references" / "core-templates.md").read_text(encoding="utf-8")
        migration = (SKILL / "references" / "migration.md").read_text(encoding="utf-8")
        self.assertIn("<!-- project-memory:start schema=1 -->", entry)
        self.assertIn("<!-- project-memory:end -->", entry)
        self.assertIn("Project Memory schema: 1", context)
        self.assertIn("schema=1", migration)

    def test_release_inputs_have_no_machine_path_or_junk(self):
        roots = [SKILL, REPO / ".codex-plugin", REPO / ".claude-plugin"]
        for root in roots:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                self.assertNotEqual(path.name, ".DS_Store")
                if path.suffix in {".md", ".yaml", ".json", ".py"}:
                    text = path.read_text(encoding="utf-8")
                    self.assertNotRegex(text, r"/(?:Users|home)/[^/<`\s]+/")
                    self.assertNotIn("[TODO:", text)

    def test_repository_relative_markdown_links_resolve(self):
        link_re = re.compile(r"(?<!!)\[[^]\n]+\]\((<[^>\n]+>|[^\s)]+)")
        paths = (
            list(REPO.glob("*.md"))
            + list((REPO / "docs").rglob("*.md"))
            + list((SKILL / "references").glob("*.md"))
        )
        paths.append(SKILL / "SKILL.md")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"(?ms)^```.*?^```\s*$", "", text)
            text = re.sub(r"(?ms)^~~~.*?^~~~\s*$", "", text)
            for raw in link_re.findall(text):
                target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                resolved = (path.parent / unquote(parsed.path)).resolve()
                self.assertTrue(resolved.exists(), f"{path.relative_to(REPO)} -> {target}")

    def test_migration_requires_zero_write_item_approval(self):
        text = (SKILL / "references" / "migration.md").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("zero-write", lowered)
        self.assertRegex(text, r"MIG-\d{2}")
        self.assertRegex(lowered, r"item[- ]by[- ]item")
        self.assertIn("conversation", lowered)
        self.assertRegex(
            lowered,
            r"must not\s+create,\s+modify,\s+delete,\s+move,\s+or\s+rename",
        )
        self.assertIn("validation-closed", lowered)
        self.assertIn("atomic execution group", lowered)
        self.assertIn("not implicit permission", lowered)
        self.assertRegex(lowered, r"backup.+own `mig-\*` item")

    def test_migration_approval_expires_when_baseline_changes(self):
        text = (SKILL / "references" / "migration.md").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("baseline", lowered)
        self.assertRegex(
            lowered,
            r"(?:affected approval(?: items|s)?|approval(?: items|s)? for affected items)\s+expire",
        )
        self.assertRegex(lowered, r"re-(?:audit|read|propose)")

    def test_collaborative_evolution_safety_contract(self):
        text = (SKILL / "references" / "evolution.md").read_text(encoding="utf-8")
        for phrase in (
            "30",
            "14",
            "3",
            "批准试用",
            "修改后试用",
            "驳回",
            "延后",
            "保持安静",
        ):
            self.assertIn(phrase, text)
        lowered = text.lower()
        self.assertTrue("cannot" in lowered or "不得" in text)
        self.assertIn("github", lowered)


class ReleaseBuildTests(unittest.TestCase):
    def test_builds_deterministic_allowlisted_archives(self):
        build_release = load_build_module()
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = build_release.build(REPO, Path(first))
            second_paths = build_release.build(REPO, Path(second))
            first_zips = [path for path in first_paths if path.suffix == ".zip"]
            second_zips = [path for path in second_paths if path.suffix == ".zip"]
            self.assertEqual([path.name for path in first_zips], [path.name for path in second_zips])
            for left, right in zip(first_zips, second_zips):
                self.assertEqual(hashlib.sha256(left.read_bytes()).digest(), hashlib.sha256(right.read_bytes()).digest())

            standalone, codex, claude = first_zips
            with zipfile.ZipFile(standalone) as archive:
                names = set(archive.namelist())
                self.assertIn("project-memory/SKILL.md", names)
                self.assertIn("project-memory/LICENSE", names)
                self.assertIn("project-memory/references/initialization.md", names)
                self.assertIn("project-memory/references/migration.md", names)
                self.assertNotIn("project-memory/README.md", names)
                self.assertFalse(any(".codex-plugin" in name or ".claude-plugin" in name for name in names))
            with zipfile.ZipFile(codex) as archive:
                names = set(archive.namelist())
                self.assertIn("project-memory/.codex-plugin/plugin.json", names)
                self.assertIn("project-memory/skills/project-memory/SKILL.md", names)
                self.assertIn(
                    "project-memory/skills/project-memory/references/initialization.md",
                    names,
                )
                self.assertIn(
                    "project-memory/skills/project-memory/references/migration.md",
                    names,
                )
                self.assertFalse(any(".claude-plugin" in name for name in names))
            with zipfile.ZipFile(claude) as archive:
                names = set(archive.namelist())
                self.assertIn("project-memory/.claude-plugin/plugin.json", names)
                self.assertIn("project-memory/skills/project-memory/SKILL.md", names)
                self.assertIn(
                    "project-memory/skills/project-memory/references/initialization.md",
                    names,
                )
                self.assertIn(
                    "project-memory/skills/project-memory/references/migration.md",
                    names,
                )
                self.assertFalse(any(".codex-plugin" in name for name in names))


if __name__ == "__main__":
    unittest.main()
