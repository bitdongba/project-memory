#!/usr/bin/env python3
"""Read-only structural validation for a project-memory project.

Exit codes:
    0: validation passed
    1: validation found errors, or a supplied health baseline found regression
    2: invalid invocation or the project could not be inspected reliably
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import unquote, urlsplit

from markdown_links import iter_link_destinations, parse_inline_link, unescape_destination


SUPPORTED_ENTRY_SCHEMA = 1
SUPPORTED_RULESET = 1
ENTRY_FILENAMES = ("AGENTS.md", "CLAUDE.md")
REQUIRED_FILES = (".planning/context.md",)
LEGACY_HISTORY_FILE = ".planning/release-log.md"

SEVERITIES = ("ERROR", "REVIEW", "WARNING", "NOTICE")
HEALTH_CODES = {
    "CONTEXT_SIZE_BUDGET",
    "CONTEXT_RELEASE_HEADING",
    "CONTEXT_VOLATILE_DENSITY",
    "NUMERIC_HEADING_REGRESSION",
}
CONTEXT_LINE_BUDGET = 400
CONTEXT_BYTE_BUDGET = 64 * 1024
VOLATILE_LINE_MINIMUM = 8
VOLATILE_DENSITY_BASIS_POINTS = 800

ALLOWED_STATE_VALUES = {"active", "paused", "blocked", "idle", "completed"}
STATE_ALIASES = {
    "进行中": "active",
    "暂停": "paused",
    "已暂停": "paused",
    "阻塞": "blocked",
    "已阻塞": "blocked",
    "空闲": "idle",
    "已完成": "completed",
}
ACTION_REQUIRED_STATES = {"active", "paused", "blocked"}

START_MARKER_RE = re.compile(
    r"<!--\s*project-memory:start\s+schema\s*=\s*([^\s>]+)"
    r"(?:\s+ruleset\s*=\s*([^\s>]+))?\s*-->",
    re.IGNORECASE,
)
END_MARKER_RE = re.compile(r"<!--\s*project-memory:end\s*-->", re.IGNORECASE)
ANY_START_MARKER_RE = re.compile(r"<!--\s*project-memory:start\b.*?-->", re.IGNORECASE)
CONTEXT_SCHEMA_RE = re.compile(
    r"^\s*(?:[-*]\s+)?Project Memory schema\s*:\s*(\S+)\s*$", re.IGNORECASE
)
CONTEXT_RULESET_RE = re.compile(
    r"^\s*(?:[-*]\s+)?Project Memory ruleset\s*:\s*(\S+)\s*$", re.IGNORECASE
)
RULESET_INDEX_HEADINGS = {
    "document index",
    "project memory index",
    "文档索引",
    "项目记忆索引",
}
RULESET_INDEX_ROLES = {
    "stable-intent",
    "protocol-setting",
    "resumable-state",
    "historical-event",
    "topic-detail",
}
RULESET_REQUIRED_SINGLE_ROLES = {
    "stable-intent",
    "protocol-setting",
    "historical-event",
}
RULESET_ROLE_HEADERS = {"role", "角色"}
RULESET_PATH_HEADERS = {"document", "path", "文档", "路径"}

INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
STATE_RE = re.compile(
    r"^\s*[-*]\s*(?:状态|status)\s*[:：]\s*(.+?)\s*$", re.IGNORECASE
)
COMPLETION_SIGNAL_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:完成信号|completion signal)\s*[:：]\s*(.*?)\s*$",
    re.IGNORECASE,
)
RELEASE_DATE_HEADING_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\s|$)")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RELEASE_HEADING_KEYWORDS_RE = re.compile(
    r"发布|上线|部署|构建|版本|环境|进行中|进度|release|deploy|build|rollout|version",
    re.IGNORECASE,
)
VOLATILE_LINE_RE = re.compile(
    r"(?:\bpid\b|\b(?:sha(?:-?1|-?256)?|commit|hash)\b|\b[0-9a-f]{7,40}\b|"
    r"\b(?:uat|prod(?:uction)?|staging|caster|paladin)\b|发布|上线|部署|构建号|"
    r"流水|运行状态|进行中)",
    re.IGNORECASE,
)
NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:[.)、:：])?\s+\S")
ADR_FILENAME_RE = re.compile(r"^(?:ADR[-_])?(\d{4})(?:[-_. ]|$)", re.IGNORECASE)
ADR_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s+(?:ADR[-_ ]*)?(\d{4})(?:\b|[-_:：])", re.IGNORECASE
)
EXPLICIT_ADR_FILENAME_RE = re.compile(
    r"^ADR[-_](\d{4})(?:[-_. ]|$)", re.IGNORECASE
)
EXPLICIT_ADR_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s+ADR[-_ ]*(\d{4})(?:\b|[-_:：])", re.IGNORECASE
)
EXP_FILENAME_RE = re.compile(r"^(EXP[-_]\d+)(?:[-_. ]|$)", re.IGNORECASE)
EXP_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s+(EXP[-_]\d+)(?:\b|[-_:：])", re.IGNORECASE
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<([^<>\n]+)>")
BRACE_PLACEHOLDER_RE = re.compile(r"\{\{\s*[^{}\n]+?\s*\}\}")
WORD_PLACEHOLDER_RE = re.compile(
    r"\b(?:TBD|TO[_ -]?BE[_ -]?FILLED|REPLACE[_ -]?ME)\b", re.IGNORECASE
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
KNOWN_HTML_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "details",
    "div",
    "em",
    "img",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


@dataclass(frozen=True)
class Issue:
    """One validation finding.

    ``severity`` is last and has an ERROR default so callers constructing or
    comparing the legacy four-field object continue to work.
    """

    code: str
    path: str
    line: int
    message: str
    severity: str = "ERROR"

    def render(self) -> str:
        location = self.path
        if self.line:
            location = f"{location}:{self.line}"
        return f"{self.severity} [{self.code}] {location}: {self.message}"

    def as_json(self) -> Dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "path": self.path,
            "line": self.line,
            "message": self.message,
        }


class ValidationRuntimeError(RuntimeError):
    """The validator could not safely or reliably inspect the requested root."""


@dataclass(frozen=True)
class BaselineInfo:
    """A validated, read-only health baseline supplied by the caller."""

    path: str
    sha256: str
    measurements: Mapping[Tuple[str, str], Mapping[str, int]]
    signatures: Mapping[Tuple[str, str], Tuple[str, ...]]
    source_fingerprints: Mapping[str, str]


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _normalise_exp_id(raw: str) -> str:
    number = int(re.search(r"\d+", raw).group(0))
    return f"EXP-{number:03d}"


class ProjectMemoryValidator:
    def __init__(
        self,
        root: Path,
        *,
        health: bool = False,
        baseline: Optional[BaselineInfo] = None,
    ) -> None:
        self.root = root
        self.health = health
        self.baseline = baseline
        self._issues: List[Issue] = []
        self._issue_keys: Set[Tuple[str, str, int, str, str]] = set()
        self._texts: Dict[Path, str] = {}
        self._payloads: Dict[Path, bytes] = {}
        self._health_measurements: Dict[Tuple[str, str], Dict[str, int]] = {}
        self._health_signatures: Dict[Tuple[str, str], Tuple[str, ...]] = {}
        self._context_ruleset: Optional[str] = None
        self._context_ruleset_declared = False
        self._ruleset_routes: Dict[str, List[str]] = {
            role: [] for role in RULESET_INDEX_ROLES
        }

    def run(self) -> List[Issue]:
        self._check_planning_boundary_and_required_files()
        markdown_files = self._collect_planning_markdown()
        context_schema = self._check_context_schema()
        context_ruleset = self._check_context_ruleset()
        self._context_ruleset = context_ruleset
        if context_ruleset != str(SUPPORTED_RULESET):
            self._check_required_file(LEGACY_HISTORY_FILE)
        if self.baseline is not None and context_ruleset != str(SUPPORTED_RULESET):
            raise ValidationRuntimeError(
                "a health baseline requires exactly one supported "
                f"Project Memory ruleset: {SUPPORTED_RULESET} declaration"
            )
        self._check_entrypoints(context_schema, context_ruleset)

        ruleset_enabled = context_ruleset == str(SUPPORTED_RULESET)
        if ruleset_enabled:
            self._check_ruleset_document_index(markdown_files)
            markdown_files = self._include_ruleset_canonical_markdown(markdown_files)

        for path in markdown_files:
            text = self._texts.get(path)
            if text is None:
                text = self._read_text(path)
            if text is None:
                continue
            self._texts[path] = text
            self._check_markdown_links(path, text)
            self._check_placeholders(path, text)

        self._check_document_index()
        self._check_duplicate_adr_ids(markdown_files)
        self._check_duplicate_experience_ids(markdown_files)
        if ruleset_enabled:
            self._check_ruleset_scoped_entrypoints(context_schema, context_ruleset)
        self._check_state_files(
            markdown_files,
            require_completion_signal=ruleset_enabled,
            additional_state_paths=self._ruleset_routes["resumable-state"],
        )
        if ruleset_enabled:
            for release_path in self._ruleset_routes["historical-event"]:
                self._check_release_log_order(release_path)

        if self.health:
            if not self._context_ruleset_declared:
                self._add(
                    "RULESET_NOT_ENABLED",
                    self.root / ".planning/context.md",
                    "health checks are advisory; opt in with Project Memory ruleset: 1",
                    severity="NOTICE",
                )
            self._check_context_health()
            self._check_numeric_heading_regressions(markdown_files)
            self._apply_health_baseline()

        return sorted(
            self._issues,
            key=lambda issue: (
                issue.path,
                issue.line,
                issue.code,
                issue.severity,
                issue.message,
            ),
        )

    def _add(
        self,
        code: str,
        path: Path,
        message: str,
        line: int = 0,
        *,
        severity: str = "ERROR",
    ) -> None:
        if severity not in SEVERITIES:
            raise AssertionError(f"unsupported issue severity: {severity}")
        display_path = self._display_path(path)
        key = (code, display_path, line, message, severity)
        if key in self._issue_keys:
            return
        self._issue_keys.add(key)
        self._issues.append(Issue(code, display_path, line, message, severity))

    @property
    def health_measurements(self) -> List[Dict[str, object]]:
        """Return deterministic, JSON-safe measurements for an explicit baseline."""

        records: List[Dict[str, object]] = []
        for (code, path), values in sorted(self._health_measurements.items()):
            records.append(
                {
                    "code": code,
                    "path": path,
                    "values": {key: values[key] for key in sorted(values)},
                    "signatures": list(
                        self._health_signatures.get((code, path), ())
                    ),
                }
            )
        return records

    @property
    def health_source_fingerprints(self) -> List[Dict[str, str]]:
        """Fingerprint measurement sources for candidate approval provenance."""

        records: List[Dict[str, str]] = []
        source_paths = sorted({path for _, path in self._health_measurements})
        for display_path in source_paths:
            source = self.root / display_path
            payload = self._payloads.get(source)
            if payload is None:
                raise ValidationRuntimeError(
                    f"cannot fingerprint the inspected health source {display_path}"
                )
            records.append(
                {
                    "path": display_path,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )
        return records

    def _display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix() or "."
        except ValueError:
            return str(path)

    def _safe_resolve(
        self,
        path: Path,
        *,
        source: Optional[Path] = None,
        line: int = 0,
        code: str = "PATH_OUTSIDE_ROOT",
    ) -> Optional[Path]:
        try:
            resolved = path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            self._add(
                "PATH_RESOLUTION_FAILED",
                source or path,
                f"cannot resolve {self._display_path(path)} safely: {exc}",
                line,
            )
            return None
        if not _is_within(resolved, self.root):
            self._add(
                code,
                source or path,
                f"path escapes project root: {self._display_path(path)} -> {resolved}",
                line,
            )
            return None
        return resolved

    def _check_symlink(self, path: Path) -> None:
        if not path.is_symlink():
            return
        resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
        if resolved is None:
            return
        if not path.exists():
            self._add("SYMLINK_BROKEN", path, "symlink target does not exist")

    def _check_planning_boundary_and_required_files(self) -> None:
        planning = self.root / ".planning"
        self._check_symlink(planning)
        planning_resolved = self._safe_resolve(planning, code="SYMLINK_ESCAPE")
        if planning_resolved is None:
            return
        if not planning.exists():
            self._add("PLANNING_DIR_MISSING", planning, "required .planning directory is missing")
            return
        if not planning_resolved.is_dir():
            self._add("PLANNING_DIR_INVALID", planning, ".planning must be a directory")
            return

        for relative in REQUIRED_FILES:
            self._check_required_file(relative)

    def _check_required_file(self, relative: str) -> None:
        path = self.root / relative
        self._check_symlink(path)
        resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
        if resolved is None:
            return
        if not path.exists():
            self._add("REQUIRED_FILE_MISSING", path, f"required file is missing: {relative}")
        elif not resolved.is_file():
            self._add("REQUIRED_FILE_INVALID", path, f"required path is not a file: {relative}")

    def _collect_planning_markdown(self) -> List[Path]:
        planning = self.root / ".planning"
        resolved = self._safe_resolve(planning, code="SYMLINK_ESCAPE")
        if resolved is None or not resolved.is_dir():
            return []

        files: Set[Path] = set()

        def traversal_failed(exc: OSError) -> None:
            raise exc

        try:
            for dirpath, dirnames, filenames in os.walk(
                resolved, followlinks=False, onerror=traversal_failed
            ):
                directory = Path(dirpath)
                for name in list(dirnames) + list(filenames):
                    self._check_symlink(directory / name)
                for name in filenames:
                    path = directory / name
                    if path.suffix.lower() != ".md":
                        continue
                    if self._safe_resolve(path, code="SYMLINK_ESCAPE") is not None:
                        files.add(path)
        except OSError as exc:
            raise ValidationRuntimeError(f"cannot traverse {planning}: {exc}") from exc
        return sorted(files, key=lambda path: self._display_path(path))

    def _include_ruleset_canonical_markdown(
        self,
        markdown_files: Sequence[Path],
    ) -> List[Path]:
        """Include every existing typed-index target in applicable checks."""

        files = set(markdown_files)
        for routes in self._ruleset_routes.values():
            for relative in routes:
                target = self.root.joinpath(*PurePosixPath(relative).parts)
                if os.path.lexists(target):
                    files.add(target)
        return sorted(files, key=self._display_path)

    def _read_text(self, path: Path) -> Optional[str]:
        resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
        if resolved is None:
            return None
        try:
            payload = resolved.read_bytes()
            text = payload.decode("utf-8")
            self._payloads[path] = payload
            return text
        except UnicodeDecodeError:
            self._add("FILE_ENCODING", path, "Markdown file is not valid UTF-8")
        except OSError as exc:
            self._add("FILE_UNREADABLE", path, f"cannot read file: {exc}")
        return None

    def _check_context_schema(self) -> Optional[str]:
        context = self._context_text()
        if context is None:
            return None
        path, text = context
        declarations: List[Tuple[str, int]] = []
        for line_number, line in self._iter_visible_markdown_lines(text):
            match = CONTEXT_SCHEMA_RE.match(line)
            if match:
                declarations.append((match.group(1), line_number))

        if not declarations:
            self._add(
                "CONTEXT_SCHEMA_MISSING",
                path,
                "context must declare exactly one 'Project Memory schema: 1' value",
            )
            return None
        if len(declarations) > 1:
            lines = ", ".join(str(line) for _, line in declarations)
            self._add(
                "CONTEXT_SCHEMA_MULTIPLE",
                path,
                f"context declares Project Memory schema more than once (lines {lines})",
                declarations[1][1],
            )
            return None

        schema, line = declarations[0]
        if schema != str(SUPPORTED_ENTRY_SCHEMA):
            self._add(
                "CONTEXT_SCHEMA_UNSUPPORTED",
                path,
                f"context schema must be {SUPPORTED_ENTRY_SCHEMA}, found {schema!r}",
                line,
            )
        return schema

    def _check_context_ruleset(self) -> Optional[str]:
        context = self._context_text()
        if context is None:
            return None
        path, text = context
        declarations: List[Tuple[str, int]] = []
        for line_number, line in self._iter_visible_markdown_lines(text):
            match = CONTEXT_RULESET_RE.match(line)
            if match:
                declarations.append((match.group(1), line_number))

        self._context_ruleset_declared = bool(declarations)
        if not declarations:
            return None
        if len(declarations) > 1:
            lines = ", ".join(str(line) for _, line in declarations)
            self._add(
                "CONTEXT_RULESET_MULTIPLE",
                path,
                f"context declares Project Memory ruleset more than once (lines {lines})",
                declarations[1][1],
            )
            return None

        ruleset, line = declarations[0]
        if ruleset != str(SUPPORTED_RULESET):
            self._add(
                "CONTEXT_RULESET_UNSUPPORTED",
                path,
                f"context ruleset must be {SUPPORTED_RULESET}, found {ruleset!r}",
                line,
            )
        return ruleset

    def _check_entrypoints(
        self,
        context_schema: Optional[str],
        context_ruleset: Optional[str],
    ) -> None:
        managed_block_count = 0
        for filename in ENTRY_FILENAMES:
            path = self.root / filename
            if not os.path.lexists(path):
                continue
            managed_block_count += self._check_entry_file(
                path,
                context_schema,
                context_ruleset,
            )

        if managed_block_count == 0:
            self._add(
                "ENTRY_BLOCK_MISSING",
                self.root,
                "AGENTS.md or CLAUDE.md must contain a project-memory managed block",
            )

    def _check_entry_file(
        self,
        path: Path,
        context_schema: Optional[str],
        context_ruleset: Optional[str],
    ) -> int:
        self._check_symlink(path)
        text = self._read_text(path)
        if text is None:
            return 0
        blocks = self._managed_blocks(path, text)
        if len(blocks) > 1:
            self._add(
                "ENTRY_BLOCK_MULTIPLE",
                path,
                "entry file contains more than one project-memory managed block",
            )
        for schema, ruleset, start_line, block_text in blocks:
            if schema != str(SUPPORTED_ENTRY_SCHEMA):
                self._add(
                    "ENTRY_SCHEMA_UNSUPPORTED",
                    path,
                    f"managed block schema must be {SUPPORTED_ENTRY_SCHEMA}, found {schema!r}",
                    start_line,
                )
            if context_schema is not None and schema != context_schema:
                self._add(
                    "ENTRY_CONTEXT_SCHEMA_MISMATCH",
                    path,
                    f"managed block schema {schema!r} does not match context schema {context_schema!r}",
                    start_line,
                )
            if ruleset is not None and ruleset != str(SUPPORTED_RULESET):
                self._add(
                    "ENTRY_RULESET_UNSUPPORTED",
                    path,
                    f"managed block ruleset must be {SUPPORTED_RULESET}, found {ruleset!r}",
                    start_line,
                )
            if ruleset != context_ruleset:
                self._add(
                    "ENTRY_CONTEXT_RULESET_MISMATCH",
                    path,
                    "managed block ruleset "
                    f"{ruleset!r} does not match context ruleset {context_ruleset!r}",
                    start_line,
                )
            visible_block_text = "\n".join(
                line for _, line in self._iter_visible_markdown_lines(block_text)
            )
            if ".planning/context.md" not in visible_block_text:
                self._add(
                    "ENTRY_CONTEXT_LINK_MISSING",
                    path,
                    "managed block must point to .planning/context.md",
                    start_line,
                )
            self._check_markdown_links(path, block_text, line_offset=start_line)
            self._check_placeholders(path, block_text, line_offset=start_line)
        return len(blocks)

    def _check_ruleset_scoped_entrypoints(
        self,
        context_schema: Optional[str],
        context_ruleset: Optional[str],
    ) -> None:
        """Validate managed host entries that scope an indexed canonical file."""

        directories: Set[Path] = set()
        for paths in self._ruleset_routes.values():
            for relative in paths:
                target = self.root.joinpath(*PurePosixPath(relative).parts)
                current = target.parent
                while current != self.root:
                    directories.add(current)
                    if self.root not in current.parents:
                        break
                    current = current.parent

        for directory in sorted(directories, key=self._display_path):
            for filename in ENTRY_FILENAMES:
                path = directory / filename
                if not os.path.lexists(path):
                    continue
                self._check_entry_file(path, context_schema, context_ruleset)

    def _managed_blocks(
        self,
        path: Path,
        text: str,
    ) -> List[Tuple[str, Optional[str], int, str]]:
        blocks: List[Tuple[str, Optional[str], int, str]] = []
        open_marker: Optional[Tuple[str, Optional[str], int, int]] = None
        lines = text.splitlines(keepends=True)
        offset = 0
        in_fence = False
        fence_char = ""
        fence_length = 0

        for line_number, line_text in enumerate(lines, 1):
            fence = FENCE_RE.match(line_text)
            if fence:
                marker = fence.group(1)
                if not in_fence:
                    in_fence = True
                    fence_char = marker[0]
                    fence_length = len(marker)
                elif (
                    marker[0] == fence_char
                    and len(marker) >= fence_length
                    and not line_text[fence.end() :].strip()
                ):
                    in_fence = False
                    fence_char = ""
                    fence_length = 0
                offset += len(line_text)
                continue
            if in_fence:
                offset += len(line_text)
                continue

            start_match = START_MARKER_RE.search(line_text)
            any_start = ANY_START_MARKER_RE.search(line_text)
            end_match = END_MARKER_RE.search(line_text)

            if any_start and not start_match:
                self._add(
                    "ENTRY_START_MARKER_INVALID",
                    path,
                    "start marker must use <!-- project-memory:start schema=N --> or "
                    "<!-- project-memory:start schema=N ruleset=N -->",
                    line_number,
                )
            if start_match:
                if open_marker is not None:
                    self._add(
                        "ENTRY_BLOCK_NESTED",
                        path,
                        "managed blocks cannot be nested",
                        line_number,
                    )
                else:
                    open_marker = (
                        start_match.group(1),
                        start_match.group(2),
                        line_number,
                        offset + len(line_text),
                    )
            if end_match:
                if open_marker is None:
                    self._add(
                        "ENTRY_END_WITHOUT_START",
                        path,
                        "managed block end marker has no matching start marker",
                        line_number,
                    )
                else:
                    schema, ruleset, start_line, content_start = open_marker
                    content_end = offset + end_match.start()
                    blocks.append((schema, ruleset, start_line, text[content_start:content_end]))
                    open_marker = None
            offset += len(line_text)

        if open_marker is not None:
            self._add(
                "ENTRY_BLOCK_UNCLOSED",
                path,
                "managed block start marker has no matching end marker",
                open_marker[2],
            )
        return blocks

    def _extract_markdown_targets(self, text: str) -> Iterable[Tuple[str, int]]:
        for raw_target, offset in iter_link_destinations(text):
            yield raw_target, _line_number(text, offset)

    def _normalise_link_target(self, raw: str) -> Optional[str]:
        target = unescape_destination(raw.strip())
        if not target or target.startswith(("#", "//")):
            return None

        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            return None
        local = unquote(parsed.path)
        if not local or Path(local).is_absolute():
            return None
        return local

    def _check_markdown_links(self, path: Path, text: str, line_offset: int = 0) -> None:
        for raw_target, local_line in self._extract_markdown_targets(text):
            target = self._normalise_link_target(raw_target)
            if target is None:
                continue
            line = local_line + line_offset
            candidate = path.parent / target
            resolved = self._safe_resolve(
                candidate,
                source=path,
                line=line,
                code="LINK_OUTSIDE_ROOT",
            )
            if resolved is not None and not resolved.exists():
                self._add(
                    "BROKEN_LINK",
                    path,
                    f"relative Markdown link target does not exist: {raw_target}",
                    line,
                )

    def _check_placeholders(self, path: Path, text: str, line_offset: int = 0) -> None:
        for local_line, line_text in self._iter_visible_markdown_lines(text):
            line_number = local_line + line_offset
            angle_destinations = {
                (offset, offset + len(raw))
                for raw, offset in iter_link_destinations(line_text)
                if raw.startswith("<") and raw.endswith(">")
            }
            for match in ANGLE_PLACEHOLDER_RE.finditer(line_text):
                if match.span() in angle_destinations:
                    continue
                inner = match.group(1).strip()
                if self._is_non_placeholder_angle(inner):
                    continue
                self._add(
                    "PLACEHOLDER_UNRESOLVED",
                    path,
                    f"unresolved placeholder <{inner}>",
                    line_number,
                )
            if BRACE_PLACEHOLDER_RE.search(line_text):
                self._add(
                    "PLACEHOLDER_UNRESOLVED",
                    path,
                    "unresolved {{...}} placeholder",
                    line_number,
                )
            if "待补充" in line_text or WORD_PLACEHOLDER_RE.search(line_text):
                self._add(
                    "PLACEHOLDER_UNRESOLVED",
                    path,
                    "unresolved textual placeholder",
                    line_number,
                )

    def _is_non_placeholder_angle(self, inner: str) -> bool:
        lowered = inner.lower()
        if lowered.startswith(("http://", "https://", "mailto:")) or "@" in inner:
            return True
        tag_match = re.match(r"/?([a-zA-Z][a-zA-Z0-9-]*)\b", inner)
        return bool(tag_match and tag_match.group(1).lower() in KNOWN_HTML_TAGS)

    def _context_text(self) -> Optional[Tuple[Path, str]]:
        path = self.root / ".planning/context.md"
        if path in self._texts:
            return path, self._texts[path]
        text = self._read_text(path) if path.exists() else None
        if text is None:
            return None
        self._texts[path] = text
        return path, text

    def _check_document_index(self) -> None:
        context = self._context_text()
        if context is None:
            return
        path, text = context
        lines = list(self._iter_visible_markdown_lines(text))
        section: Optional[Tuple[int, int]] = None

        for index, (_, line) in enumerate(lines):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            title = heading.group(2).strip().lower()
            if "文档索引" in title or "document index" in title or "documentation index" in title:
                section = (len(heading.group(1)), index + 1)
                break
        if section is None:
            return

        heading_level, content_start = section
        content_end = len(lines)
        for index in range(content_start, len(lines)):
            heading = HEADING_RE.match(lines[index][1])
            if heading and len(heading.group(1)) <= heading_level:
                content_end = index
                break

        for line_number, line_text in lines[content_start:content_end]:
            for raw_target, _ in self._extract_markdown_targets(line_text):
                target = self._normalise_link_target(raw_target)
                if target is not None:
                    self._check_index_target(
                        path,
                        target,
                        line_number,
                        markdown_relative=True,
                    )
            for match in INLINE_CODE_RE.finditer(line_text):
                raw_target = match.group(1).strip()
                if self._looks_like_index_path(raw_target):
                    self._check_index_target(
                        path,
                        raw_target,
                        line_number,
                        markdown_relative=False,
                    )

    def _normalise_ruleset_index_path(
        self,
        context_path: Path,
        cell: str,
    ) -> str:
        value = cell.strip()
        inline = INLINE_CODE_RE.fullmatch(value)
        if inline is not None:
            project_relative = inline.group(1)
        else:
            link = parse_inline_link(value)
            if link is None or link[2] != len(value) or value.startswith("!"):
                project_relative = value
            else:
                target = unescape_destination(link[0])
                parsed = urlsplit(target.strip())
                local = unquote(parsed.path)
                windows = PureWindowsPath(local)
                if (
                    parsed.scheme
                    or parsed.netloc
                    or not local
                    or "\\" in local
                    or local.startswith(("/", "~"))
                    or windows.is_absolute()
                    or bool(windows.drive)
                ):
                    raise ValidationRuntimeError(
                        "ruleset index Markdown target is not a safe local path"
                    )
                context_parent = context_path.parent.relative_to(self.root).as_posix()
                project_relative = posixpath.normpath(
                    posixpath.join(context_parent, local)
                )

        return _normalise_contract_path(
            project_relative,
            required_suffix=".md",
            description="ruleset index target",
        )

    def _check_ruleset_document_index(
        self,
        markdown_files: Sequence[Path],
    ) -> None:
        context = self._context_text()
        if context is None:
            return
        context_path, text = context
        visible = list(self._iter_visible_markdown_lines(text))
        sections: List[Tuple[int, List[Tuple[int, str]]]] = []
        index = 0
        while index < len(visible):
            line_number, line = visible[index]
            heading = HEADING_RE.match(line)
            if (
                heading is None
                or re.sub(r"\s+", " ", heading.group(2).strip()).casefold()
                not in RULESET_INDEX_HEADINGS
            ):
                index += 1
                continue
            level = len(heading.group(1))
            end = index + 1
            while end < len(visible):
                following = HEADING_RE.match(visible[end][1])
                if following is not None and len(following.group(1)) <= level:
                    break
                end += 1
            sections.append((line_number, visible[index + 1 : end]))
            index = end

        if len(sections) != 1:
            self._add(
                "RULESET_INDEX_SECTION_INVALID",
                context_path,
                "ruleset 1 requires exactly one recognized document-index section",
                sections[1][0] if len(sections) > 1 else 0,
            )
            return

        section_line, section_lines = sections[0]
        routes: Dict[str, List[Tuple[str, int]]] = {
            role: [] for role in RULESET_INDEX_ROLES
        }
        route_identities: Dict[str, List[Tuple[str, int]]] = {
            role: [] for role in RULESET_INDEX_ROLES
        }
        header: Optional[Tuple[int, int]] = None
        typed_table_count = 0
        previous_visible_line: Optional[int] = None
        for line_number, line in section_lines:
            if (
                previous_visible_line is not None
                and line_number != previous_visible_line + 1
            ):
                header = None
            previous_visible_line = line_number
            stripped = line.strip()
            if not stripped.startswith("|") or not stripped.endswith("|"):
                header = None
                continue
            cells = [cell.strip() for cell in stripped[1:-1].split("|")]
            folded = [re.sub(r"\s+", " ", cell).casefold() for cell in cells]
            if cells and all(
                TABLE_SEPARATOR_RE.fullmatch(cell.replace(" ", "")) is not None
                for cell in folded
            ):
                continue
            role_indexes = [
                position
                for position, value in enumerate(folded)
                if value in RULESET_ROLE_HEADERS
            ]
            path_indexes = [
                position
                for position, value in enumerate(folded)
                if value in RULESET_PATH_HEADERS
            ]
            if len(role_indexes) == 1 and len(path_indexes) == 1:
                header = (role_indexes[0], path_indexes[0])
                typed_table_count += 1
                continue
            if header is None:
                if any(cell.strip().casefold() in routes for cell in cells):
                    self._add(
                        "RULESET_INDEX_ROW_INVALID",
                        context_path,
                        "typed document-index rows must remain in one contiguous table",
                        line_number,
                    )
                continue
            role_index, path_index = header
            if max(role_index, path_index) >= len(cells):
                self._add(
                    "RULESET_INDEX_ROW_INVALID",
                    context_path,
                    "typed document-index row is missing a role or document cell",
                    line_number,
                )
                continue
            role = cells[role_index].strip().casefold()
            if role not in routes:
                self._add(
                    "RULESET_INDEX_ROLE_UNKNOWN",
                    context_path,
                    "typed document-index row uses an unsupported role token",
                    line_number,
                )
                continue
            try:
                route_path = self._normalise_ruleset_index_path(
                    context_path,
                    cells[path_index],
                )
            except ValidationRuntimeError:
                self._add(
                    "RULESET_INDEX_PATH_INVALID",
                    context_path,
                    "typed document-index row does not contain a safe canonical Markdown path",
                    line_number,
                )
                continue
            resolved = self._safe_resolve(
                self.root.joinpath(*PurePosixPath(route_path).parts),
                source=context_path,
                line=line_number,
                code="RULESET_INDEX_PATH_ESCAPE",
            )
            if resolved is None:
                continue
            if not resolved.is_file():
                self._add(
                    "RULESET_INDEX_TARGET_MISSING",
                    context_path,
                    "typed document-index target is not an existing file",
                    line_number,
                )
            routes[role].append((route_path, line_number))
            route_identities[role].append((resolved.as_posix(), line_number))

        self._ruleset_routes = {
            role: [route_path for route_path, _ in records]
            for role, records in routes.items()
        }

        if typed_table_count != 1:
            self._add(
                "RULESET_INDEX_TABLE_INVALID",
                context_path,
                "ruleset 1 requires exactly one typed role/document table",
                section_line,
            )

        for role in sorted(RULESET_REQUIRED_SINGLE_ROLES):
            if len(routes[role]) != 1:
                self._add(
                    "RULESET_INDEX_ROLE_CARDINALITY",
                    context_path,
                    f"ruleset role {role} must map to exactly one canonical path",
                    section_line,
                )

        for role in ("stable-intent", "protocol-setting"):
            for route_path, line in routes[role]:
                if route_path != ".planning/context.md":
                    self._add(
                        "RULESET_INDEX_CORE_ROUTE_INVALID",
                        context_path,
                        f"ruleset role {role} must map to .planning/context.md",
                        line,
                    )

        state_exists = any(
            path == self.root / ".planning/state.md"
            or self.root / ".planning/state" in path.parents
            for path in markdown_files
        )
        state_count = len(routes["resumable-state"])
        if state_count > 1 or (state_exists and state_count != 1):
            self._add(
                "RULESET_INDEX_STATE_CARDINALITY",
                context_path,
                "ruleset resumable-state must map to one canonical path when state exists",
                section_line,
            )

        for role, records in routes.items():
            paths = [route_path for route_path, _ in records]
            identities = [identity for identity, _ in route_identities[role]]
            if len(paths) != len(set(paths)) or len(identities) != len(set(identities)):
                self._add(
                    "RULESET_INDEX_ROUTE_DUPLICATE",
                    context_path,
                    f"ruleset role {role} repeats or aliases one canonical target",
                    next(
                        line
                        for index, (_, line) in enumerate(records)
                        if paths.count(paths[index]) > 1
                        or identities.count(identities[index]) > 1
                    ),
                )

        roles_by_identity: Dict[str, Set[str]] = {}
        for role, records in route_identities.items():
            for identity, _ in records:
                roles_by_identity.setdefault(identity, set()).add(role)
        for identity, roles in sorted(roles_by_identity.items()):
            if len(roles) <= 1 or roles == {"stable-intent", "protocol-setting"}:
                continue
            line = min(
                line
                for role in roles
                for route_identity, line in route_identities[role]
                if route_identity == identity
            )
            self._add(
                "RULESET_INDEX_ROLE_COLLISION",
                context_path,
                "one canonical path is assigned incompatible ruleset roles",
                line,
            )

    def _looks_like_index_path(self, value: str) -> bool:
        if any(token in value for token in ("<", ">", "{{", "}}", "*")):
            return False
        value = value.split("#", 1)[0]
        return value.endswith(".md") or value.endswith("/")

    def _check_index_target(
        self,
        context_path: Path,
        raw_target: str,
        line: int,
        *,
        markdown_relative: bool,
    ) -> None:
        target = raw_target.split("#", 1)[0].strip()
        if not target or Path(target).is_absolute():
            return
        if not markdown_relative:
            candidate = self.root / target
        else:
            candidate = context_path.parent / target
        resolved = self._safe_resolve(
            candidate,
            source=context_path,
            line=line,
            code="INDEX_TARGET_OUTSIDE_ROOT",
        )
        if resolved is not None and not resolved.exists():
            self._add(
                "INDEX_TARGET_MISSING",
                context_path,
                f"document index target does not exist: {raw_target}",
                line,
            )

    def _adr_files(self) -> List[Path]:
        files: Set[Path] = set()
        for directory in (self.root / ".planning/decisions", self.root / "docs/adr"):
            resolved = self._safe_resolve(directory, code="SYMLINK_ESCAPE")
            if resolved is None or not resolved.is_dir():
                continue
            try:
                for path in resolved.rglob("*.md"):
                    if self._safe_resolve(path, code="SYMLINK_ESCAPE") is not None:
                        files.add(path)
            except OSError as exc:
                self._add("DIRECTORY_UNREADABLE", directory, f"cannot inspect ADR directory: {exc}")
        return sorted(files, key=lambda path: self._display_path(path))

    def _check_duplicate_adr_ids(
        self,
        markdown_files: Sequence[Path] = (),
    ) -> None:
        definitions: Dict[str, Dict[Path, Dict[str, object]]] = {}
        conventional_files = set(self._adr_files())
        files_by_identity: Dict[Path, Tuple[Path, bool]] = {}
        for path in sorted(
            conventional_files.union(markdown_files),
            key=self._display_path,
        ):
            resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
            if resolved is None or not resolved.is_file():
                continue
            previous = files_by_identity.get(resolved)
            if previous is None:
                files_by_identity[resolved] = (path, path in conventional_files)
            else:
                current_is_conventional = path in conventional_files
                files_by_identity[resolved] = (
                    path
                    if current_is_conventional and not previous[1]
                    else previous[0],
                    previous[1] or current_is_conventional,
                )

        files = sorted(
            files_by_identity.values(),
            key=lambda item: self._display_path(item[0]),
        )
        for path, is_conventional in files:
            filename_pattern = (
                ADR_FILENAME_RE
                if is_conventional
                else EXPLICIT_ADR_FILENAME_RE
            )
            heading_pattern = (
                ADR_HEADING_RE
                if is_conventional
                else EXPLICIT_ADR_HEADING_RE
            )
            filename_match = filename_pattern.match(path.name)
            if filename_match:
                record = definitions.setdefault(filename_match.group(1), {}).setdefault(
                    path, {"filename": False, "headings": []}
                )
                record["filename"] = True
            text = self._texts.get(path)
            if text is None:
                text = self._read_text(path)
            if text is None:
                continue
            for line_number, line in self._iter_visible_markdown_lines(text):
                heading_match = heading_pattern.match(line)
                if heading_match:
                    record = definitions.setdefault(heading_match.group(1), {}).setdefault(
                        path, {"filename": False, "headings": []}
                    )
                    headings = record["headings"]
                    assert isinstance(headings, list)
                    headings.append(line_number)

        for identifier, by_path in definitions.items():
            heading_duplicates = any(len(record["headings"]) > 1 for record in by_path.values())
            if len(by_path) <= 1 and not heading_duplicates:
                continue
            locations = ", ".join(self._display_path(path) for path in sorted(by_path))
            first_path = sorted(by_path, key=lambda item: self._display_path(item))[0]
            self._add(
                "DUPLICATE_ADR_ID",
                first_path,
                f"ADR ID {identifier} is defined more than once: {locations}",
            )

    def _check_duplicate_experience_ids(self, markdown_files: Sequence[Path]) -> None:
        definitions: Dict[str, Dict[Path, Dict[str, object]]] = {}
        for path in markdown_files:
            filename_match = EXP_FILENAME_RE.match(path.name)
            if filename_match:
                identifier = _normalise_exp_id(filename_match.group(1))
                record = definitions.setdefault(identifier, {}).setdefault(
                    path, {"filename": False, "headings": []}
                )
                record["filename"] = True
            text = self._texts.get(path)
            if text is None:
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                match = EXP_HEADING_RE.match(line)
                if not match:
                    continue
                identifier = _normalise_exp_id(match.group(1))
                record = definitions.setdefault(identifier, {}).setdefault(
                    path, {"filename": False, "headings": []}
                )
                headings = record["headings"]
                assert isinstance(headings, list)
                headings.append(line_number)

        for identifier, by_path in definitions.items():
            explicit_duplicates = any(len(record["headings"]) > 1 for record in by_path.values())
            if len(by_path) <= 1 and not explicit_duplicates:
                continue
            locations = ", ".join(self._display_path(path) for path in sorted(by_path))
            first_path = sorted(by_path, key=lambda item: self._display_path(item))[0]
            self._add(
                "DUPLICATE_EXPERIENCE_ID",
                first_path,
                f"experience ID {identifier} is defined more than once: {locations}",
            )

    def _check_release_log_order(self, relative_path: str) -> None:
        path = self.root.joinpath(*PurePosixPath(relative_path).parts)
        text = self._texts.get(path)
        if text is None and path.exists():
            text = self._read_text(path)
            if text is not None:
                self._texts[path] = text
        if text is None:
            return

        ancestors: Dict[int, int] = {}
        previous: Dict[
            Tuple[int, Tuple[Tuple[int, int], ...]],
            Tuple[date, str, int],
        ] = {}
        for line_number, line in self._iter_visible_markdown_lines(text):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            level = len(heading.group(1))
            for old_level in list(ancestors):
                if old_level >= level:
                    del ancestors[old_level]
            scope = tuple(sorted(ancestors.items()))
            match = RELEASE_DATE_HEADING_RE.match(heading.group(2).strip())
            if not match:
                ancestors[level] = line_number
                continue
            raw_date = match.group(1)
            try:
                current_date = date.fromisoformat(raw_date)
            except ValueError:
                # Ordering cannot be established from a malformed date. Other
                # structural checks still run; health mode remains advisory.
                ancestors[level] = line_number
                continue
            key = (level, scope)
            preceding = previous.get(key)
            if preceding is not None and current_date > preceding[0]:
                self._add(
                    "RELEASE_LOG_DATE_ORDER",
                    path,
                    f"dated entry {raw_date} appears after older entry "
                    f"{preceding[1]} on line {preceding[2]}; keep newest entries first",
                    line_number,
                )
            previous[key] = (current_date, raw_date, line_number)
            ancestors[level] = line_number

    def _check_state_files(
        self,
        markdown_files: Sequence[Path],
        *,
        require_completion_signal: bool = False,
        additional_state_paths: Sequence[str] = (),
    ) -> None:
        state_file = self.root / ".planning/state.md"
        state_directory = self.root / ".planning/state"
        additional = {
            self.root.joinpath(*PurePosixPath(path).parts)
            for path in additional_state_paths
        }
        state_paths: Set[Path] = set(additional)
        for path in markdown_files:
            is_state = path == state_file or path in additional
            if not is_state:
                try:
                    path.relative_to(state_directory)
                    is_state = True
                except ValueError:
                    pass
            if not is_state:
                continue
            state_paths.add(path)

        for path in sorted(state_paths, key=self._display_path):
            text = self._texts.get(path)
            if text is None and path.exists():
                text = self._read_text(path)
                if text is not None:
                    self._texts[path] = text
            if text is not None:
                self._check_state(
                    path,
                    text,
                    require_completion_signal=require_completion_signal,
                )

    def _check_state(
        self,
        path: Path,
        text: str,
        *,
        require_completion_signal: bool = False,
    ) -> None:
        statuses: List[Tuple[str, int]] = []
        for line_number, line in self._iter_visible_markdown_lines(text):
            match = STATE_RE.match(line)
            if match:
                raw = match.group(1).strip().strip("`").lower()
                choices = [part.strip() for part in re.split(r"[/|]", raw) if part.strip()]
                if len(choices) > 1:
                    for choice in choices:
                        statuses.append((STATE_ALIASES.get(choice, choice), line_number))
                else:
                    statuses.append((STATE_ALIASES.get(raw, raw), line_number))
        if not statuses:
            self._add("STATE_STATUS_MISSING", path, "state file has no status field")
            return
        unique_statuses = {status for status, _ in statuses}
        if len(unique_statuses) > 1:
            self._add(
                "STATE_STATUS_AMBIGUOUS",
                path,
                f"state file declares multiple statuses: {', '.join(sorted(unique_statuses))}",
            )
            return
        status, line = statuses[0]
        if status not in ALLOWED_STATE_VALUES:
            self._add(
                "STATE_STATUS_INVALID",
                path,
                f"unsupported state {status!r}; allowed: {', '.join(sorted(ALLOWED_STATE_VALUES))}",
                line,
            )
            return
        if status in ACTION_REQUIRED_STATES and not self._has_exact_next_action(text):
            self._add(
                "STATE_NEXT_STEP_MISSING",
                path,
                f"{status} state must contain a non-placeholder Exact next step / 精确下一步 section",
            )
        if (
            require_completion_signal
            and status in ACTION_REQUIRED_STATES
            and not self._has_completion_signal(text)
        ):
            self._add(
                "STATE_COMPLETION_SIGNAL_MISSING",
                path,
                f"{status} state must contain a meaningful Completion signal / 完成信号",
            )

    def _has_exact_next_action(self, text: str) -> bool:
        lines = list(self._iter_visible_markdown_lines(text))
        section = self._exact_next_step_section(lines)
        if section is None:
            return False
        content_start, content_end, _ = section
        signal_level: Optional[int] = None
        for _, line in lines[content_start:content_end]:
            heading = HEADING_RE.match(line)
            if heading:
                level = len(heading.group(1))
                if signal_level is not None and level <= signal_level:
                    signal_level = None
                if signal_level is None and self._normalise_state_heading(
                    heading.group(2)
                ) in {"完成信号", "completion signal"}:
                    signal_level = level
                continue
            if signal_level is not None:
                continue
            cleaned = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line).strip()
            if not self._meaningful_value(cleaned):
                continue
            if COMPLETION_SIGNAL_RE.match(cleaned):
                continue
            return True
        return False

    def _normalise_state_heading(self, title: str) -> str:
        return re.sub(r"^\d+[.)、]\s*", "", title.strip().casefold())

    def _exact_next_step_section(
        self,
        lines: Sequence[Tuple[int, str]],
    ) -> Optional[Tuple[int, int, int]]:
        heading_stack: List[Tuple[int, int]] = []
        first_heading_index: Optional[int] = None
        for index, (_, line) in enumerate(lines):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            level = len(heading.group(1))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            title = self._normalise_state_heading(heading.group(2))
            is_top_level = not heading_stack or (
                len(heading_stack) == 1
                and heading_stack[0] == (1, first_heading_index)
            )
            if (
                is_top_level
                and title in {"精确下一步", "exact next step", "next action"}
            ):
                end = index + 1
                while end < len(lines):
                    following = HEADING_RE.match(lines[end][1])
                    if following and len(following.group(1)) <= level:
                        break
                    end += 1
                return index + 1, end, level
            if first_heading_index is None:
                first_heading_index = index
            heading_stack.append((level, index))
        return None

    def _has_completion_signal(self, text: str) -> bool:
        lines = list(self._iter_visible_markdown_lines(text))
        section = self._exact_next_step_section(lines)
        if section is None:
            return False
        content_start, content_end, action_level = section

        for index in range(content_start, content_end):
            line = lines[index][1]
            inline = COMPLETION_SIGNAL_RE.match(line)
            if inline and self._meaningful_value(inline.group(1)):
                return True

            heading = HEADING_RE.match(line)
            if not heading:
                continue
            title = self._normalise_state_heading(heading.group(2))
            if title not in {"完成信号", "completion signal"}:
                continue
            level = len(heading.group(1))
            for _, candidate in lines[index + 1 : content_end]:
                next_heading = HEADING_RE.match(candidate)
                if next_heading and len(next_heading.group(1)) <= level:
                    break
                if next_heading:
                    continue
                cleaned = re.sub(
                    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)",
                    "",
                    candidate,
                ).strip()
                if self._meaningful_value(cleaned):
                    return True

        # A dedicated peer section is accepted only when it immediately follows
        # the exact-next-step section, which prevents stale signals elsewhere in
        # the state snapshot from satisfying the current action contract.
        if content_end >= len(lines):
            return False
        peer = HEADING_RE.match(lines[content_end][1])
        if (
            peer is None
            or len(peer.group(1)) != action_level
            or self._normalise_state_heading(peer.group(2))
            not in {"完成信号", "completion signal"}
        ):
            return False
        for _, candidate in lines[content_end + 1 :]:
            next_heading = HEADING_RE.match(candidate)
            if next_heading and len(next_heading.group(1)) <= action_level:
                break
            if next_heading:
                continue
            cleaned = re.sub(
                r"^\s*(?:[-*+]\s+|\d+[.)]\s+)",
                "",
                candidate,
            ).strip()
            if self._meaningful_value(cleaned):
                return True
        return False

    def _meaningful_value(self, value: str) -> bool:
        cleaned = HTML_COMMENT_RE.sub("", value).strip()
        if not cleaned:
            return False
        if cleaned.lower() in {"无", "none", "n/a", "not applicable", "待补充"}:
            return False
        if ANGLE_PLACEHOLDER_RE.search(cleaned) or BRACE_PLACEHOLDER_RE.search(cleaned):
            return False
        if WORD_PLACEHOLDER_RE.search(cleaned):
            return False
        return True

    def _record_health_measurement(
        self,
        code: str,
        path: Path,
        values: Mapping[str, int],
        *,
        signatures: Sequence[str] = (),
    ) -> None:
        key = (code, self._display_path(path))
        self._health_measurements[key] = dict(values)
        self._health_signatures[key] = tuple(sorted(set(signatures)))

    def _health_signature(self, code: str, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value.strip()).casefold()
        return hashlib.sha256(f"{code}\0{normalized}".encode("utf-8")).hexdigest()

    def _iter_visible_markdown_lines(self, text: str) -> Iterable[Tuple[int, str]]:
        """Yield lines outside fenced code and HTML comments.

        Deterministic checks must not treat examples or commented history as
        active project-memory records. The returned line numbers still refer to
        the original file for stable diagnostics.
        """

        in_fence = False
        fence_char = ""
        fence_length = 0
        in_comment = False
        for line_number, original in enumerate(text.splitlines(), 1):
            if not in_comment:
                fence = FENCE_RE.match(original)
                if fence:
                    marker = fence.group(1)
                    if not in_fence:
                        in_fence = True
                        fence_char = marker[0]
                        fence_length = len(marker)
                    elif (
                        marker[0] == fence_char
                        and len(marker) >= fence_length
                        and not original[fence.end() :].strip()
                    ):
                        in_fence = False
                        fence_char = ""
                        fence_length = 0
                    continue
            if in_fence:
                continue

            remaining = original
            visible_parts: List[str] = []
            while remaining:
                if in_comment:
                    end = remaining.find("-->")
                    if end < 0:
                        remaining = ""
                        break
                    in_comment = False
                    remaining = remaining[end + 3 :]
                    continue

                start = remaining.find("<!--")
                if start < 0:
                    visible_parts.append(remaining)
                    break
                visible_parts.append(remaining[:start])
                end = remaining.find("-->", start + 4)
                if end < 0:
                    in_comment = True
                    remaining = ""
                    break
                remaining = remaining[end + 3 :]

            visible = "".join(visible_parts)
            if visible.strip():
                yield line_number, visible

    def _iter_prose_lines(self, text: str) -> Iterable[Tuple[int, str]]:
        for line_number, original in self._iter_visible_markdown_lines(text):
            cleaned = original.strip()
            if cleaned:
                yield line_number, cleaned

    def _check_context_health(self) -> None:
        context = self._context_text()
        if context is None:
            return
        path, text = context
        line_count = len(text.splitlines())
        byte_count = len(text.encode("utf-8"))
        self._record_health_measurement(
            "CONTEXT_SIZE_BUDGET",
            path,
            {"bytes": byte_count, "lines": line_count},
        )
        if line_count > CONTEXT_LINE_BUDGET or byte_count > CONTEXT_BYTE_BUDGET:
            self._add(
                "CONTEXT_SIZE_BUDGET",
                path,
                f"context contains {line_count} lines / {byte_count} bytes; advisory budgets "
                f"are {CONTEXT_LINE_BUDGET} lines / {CONTEXT_BYTE_BUDGET} bytes",
                severity="WARNING",
            )

        release_headings: List[Tuple[int, str]] = []
        for line_number, line in self._iter_visible_markdown_lines(text):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            title = heading.group(2).strip()
            if ISO_DATE_RE.search(title) and RELEASE_HEADING_KEYWORDS_RE.search(title):
                release_headings.append((line_number, title))
        self._record_health_measurement(
            "CONTEXT_RELEASE_HEADING",
            path,
            {"count": len(release_headings)},
            signatures=[
                self._health_signature("CONTEXT_RELEASE_HEADING", title)
                for _, title in release_headings
            ],
        )
        if release_headings:
            first_line = release_headings[0][0]
            self._add(
                "CONTEXT_RELEASE_HEADING",
                path,
                f"context contains {len(release_headings)} date-and-release heading(s); "
                "route event history to its canonical log",
                first_line,
                severity="REVIEW",
            )

        prose_lines = list(self._iter_prose_lines(text))
        volatile_lines = [
            (line_number, line)
            for line_number, line in prose_lines
            if VOLATILE_LINE_RE.search(line)
        ]
        density = (
            round(len(volatile_lines) * 10_000 / len(prose_lines))
            if prose_lines
            else 0
        )
        self._record_health_measurement(
            "CONTEXT_VOLATILE_DENSITY",
            path,
            {
                "density_basis_points": density,
                "prose_lines": len(prose_lines),
                "volatile_lines": len(volatile_lines),
            },
            signatures=[
                self._health_signature("CONTEXT_VOLATILE_DENSITY", line)
                for _, line in volatile_lines
            ],
        )
        if (
            len(volatile_lines) >= VOLATILE_LINE_MINIMUM
            and density >= VOLATILE_DENSITY_BASIS_POINTS
        ):
            self._add(
                "CONTEXT_VOLATILE_DENSITY",
                path,
                f"{len(volatile_lines)} of {len(prose_lines)} nonblank prose lines "
                f"({density / 100:.2f}%) contain volatile operational markers; "
                "review their canonical homes",
                volatile_lines[0][0],
                severity="REVIEW",
            )

    def _parse_numbered_heading(self, title: str) -> Optional[Tuple[int, ...]]:
        match = NUMBERED_HEADING_RE.match(title.strip())
        if not match:
            return None
        raw = match.group(1)
        parts = tuple(int(part) for part in raw.split("."))
        # A bare four-digit year is normally chronology, not section numbering.
        if len(parts) == 1 and parts[0] > 99:
            return None
        return parts

    def _check_numeric_heading_regressions(
        self,
        markdown_files: Sequence[Path],
    ) -> None:
        for path in markdown_files:
            text = self._texts.get(path)
            if text is None:
                continue
            ancestors: Dict[int, int] = {}
            ancestor_titles: Dict[int, str] = {}
            previous: Dict[
                Tuple[int, Tuple[Tuple[int, int], ...]],
                Tuple[Tuple[int, ...], int, str],
            ] = {}
            regressions: List[Tuple[int, int, str]] = []

            for line_number, line in self._iter_visible_markdown_lines(text):
                heading = HEADING_RE.match(line)
                if not heading:
                    continue
                level = len(heading.group(1))
                for old_level in list(ancestors):
                    if old_level >= level:
                        del ancestors[old_level]
                        ancestor_titles.pop(old_level, None)
                scope = tuple(sorted(ancestors.items()))
                title = heading.group(2).strip()
                stable_scope = tuple(sorted(ancestor_titles.items()))
                number = self._parse_numbered_heading(title)
                key = (level, scope)
                if number is not None and key in previous:
                    old_number, old_line, old_title = previous[key]
                    if number < old_number:
                        regressions.append(
                            (
                                line_number,
                                old_line,
                                "\0".join(
                                    [
                                        *(f"h{scope_level}:{scope_title}" for scope_level, scope_title in stable_scope),
                                        f"h{level}:{old_title}",
                                        f"h{level}:{title}",
                                    ]
                                ),
                            )
                        )
                if number is not None:
                    previous[key] = (number, line_number, title)
                ancestors[level] = line_number
                ancestor_titles[level] = title

            if not regressions:
                continue
            self._record_health_measurement(
                "NUMERIC_HEADING_REGRESSION",
                path,
                {"count": len(regressions)},
                signatures=[
                    self._health_signature("NUMERIC_HEADING_REGRESSION", signature)
                    for _, _, signature in regressions
                ],
            )
            line_number, old_line, _ = regressions[0]
            self._add(
                "NUMERIC_HEADING_REGRESSION",
                path,
                f"{len(regressions)} numbered heading regression(s); the first follows "
                f"a higher-numbered peer on line {old_line}",
                line_number,
                severity="REVIEW",
            )

    def _measurement_is_worse(
        self,
        code: str,
        current: Mapping[str, int],
        baseline: Mapping[str, int],
    ) -> bool:
        if code == "CONTEXT_SIZE_BUDGET":
            limits = {
                "lines": CONTEXT_LINE_BUDGET,
                "bytes": CONTEXT_BYTE_BUDGET,
            }
            return any(
                current.get(key, 0) > limit
                and (
                    baseline.get(key, 0) <= limit
                    or current.get(key, 0) > baseline.get(key, 0)
                )
                for key, limit in limits.items()
            )
        elif code == "CONTEXT_VOLATILE_DENSITY":
            keys = ("volatile_lines", "density_basis_points")
        else:
            keys = ("count",)
        return any(key not in baseline or current.get(key, 0) > baseline[key] for key in keys)

    def _measurement_is_better(
        self,
        code: str,
        current: Mapping[str, int],
        baseline: Mapping[str, int],
    ) -> bool:
        if code == "CONTEXT_SIZE_BUDGET":
            if self._measurement_is_worse(code, current, baseline):
                return False
            limits = {
                "lines": CONTEXT_LINE_BUDGET,
                "bytes": CONTEXT_BYTE_BUDGET,
            }
            return any(
                baseline.get(key, 0) > limit
                and current.get(key, 0) < baseline.get(key, 0)
                for key, limit in limits.items()
            )
        elif code == "CONTEXT_VOLATILE_DENSITY":
            keys = ("volatile_lines", "density_basis_points")
        else:
            keys = ("count",)
        if any(key not in baseline or current.get(key, 0) > baseline[key] for key in keys):
            return False
        return any(current.get(key, 0) < baseline[key] for key in keys)

    def _measurement_represents_debt(
        self,
        code: str,
        values: Mapping[str, int],
    ) -> bool:
        if code == "CONTEXT_SIZE_BUDGET":
            return (
                values.get("lines", 0) > CONTEXT_LINE_BUDGET
                or values.get("bytes", 0) > CONTEXT_BYTE_BUDGET
            )
        if code == "CONTEXT_VOLATILE_DENSITY":
            return (
                values.get("volatile_lines", 0) >= VOLATILE_LINE_MINIMUM
                and values.get("density_basis_points", 0)
                >= VOLATILE_DENSITY_BASIS_POINTS
            )
        return values.get("count", 0) > 0

    def _apply_health_baseline(self) -> None:
        if self.baseline is None:
            return

        transformed: List[Issue] = []
        finding_keys: Set[Tuple[str, str]] = set()
        for issue in self._issues:
            key = (issue.code, issue.path)
            if issue.code not in HEALTH_CODES:
                transformed.append(issue)
                continue
            finding_keys.add(key)
            current = self._health_measurements[key]
            accepted = self.baseline.measurements.get(key)
            current_signatures = set(self._health_signatures.get(key, ()))
            accepted_signatures = set(self.baseline.signatures.get(key, ()))
            if accepted is None:
                transformed.append(
                    Issue(
                        issue.code,
                        issue.path,
                        issue.line,
                        issue.message + "; not present in the approved baseline",
                        "REVIEW",
                    )
                )
            elif self._measurement_is_worse(issue.code, current, accepted):
                transformed.append(
                    Issue(
                        issue.code,
                        issue.path,
                        issue.line,
                        issue.message + f"; worsened from baseline {dict(accepted)}",
                        "REVIEW",
                    )
                )
            elif not current_signatures.issubset(accepted_signatures):
                transformed.append(
                    Issue(
                        issue.code,
                        issue.path,
                        issue.line,
                        issue.message
                        + "; contains a finding signature not present in the approved baseline",
                        "REVIEW",
                    )
                )
            else:
                suffix = "; within the approved baseline"
                if self._measurement_is_better(issue.code, current, accepted):
                    suffix += "; a separate approved baseline tightening can lock in the gain"
                transformed.append(
                    Issue(
                        issue.code,
                        issue.path,
                        issue.line,
                        issue.message + suffix,
                        "NOTICE",
                    )
                )

        for key, accepted in sorted(self.baseline.measurements.items()):
            if key in finding_keys or not self._measurement_represents_debt(key[0], accepted):
                continue
            current = self._health_measurements.get(key, {"count": 0})
            if not self._measurement_is_better(key[0], current, accepted):
                continue
            transformed.append(
                Issue(
                    "HEALTH_BASELINE_CAN_TIGHTEN",
                    key[1],
                    0,
                    f"{key[0]} improved from baseline {dict(accepted)}; tightening the "
                    "tracked baseline requires separate approval",
                    "NOTICE",
                )
            )

        self._issues = transformed
        self._issue_keys = {
            (issue.code, issue.path, issue.line, issue.message, issue.severity)
            for issue in transformed
        }


def _resolve_project_root(project_root: Path) -> Path:
    raw_root = Path(project_root).expanduser()
    try:
        root = raw_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationRuntimeError(f"cannot resolve project root {raw_root}: {exc}") from exc
    if not root.is_dir():
        raise ValidationRuntimeError(f"project root is not a directory: {root}")
    return root


def _normalise_contract_path(
    raw: object,
    *,
    required_suffix: str,
    description: str,
) -> str:
    """Return one portable, normalized repository-relative contract path."""

    invalid_message = (
        f"{description} must be a normalized repository-relative "
        f"{required_suffix} path"
    )

    if isinstance(raw, Path):
        value = raw.as_posix()
    elif isinstance(raw, str):
        value = raw
    else:
        raise ValidationRuntimeError(f"{description} must be a string path")

    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValidationRuntimeError(invalid_message) from exc

    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not value
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or "\\" in value
        or value.startswith(("/", "~"))
        or posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or value != posix.as_posix()
        or any(part in {"", ".", ".."} for part in posix.parts)
        or posix.suffix.lower() != required_suffix
    ):
        raise ValidationRuntimeError(invalid_message)
    return posix.as_posix()


def _json_object_without_duplicate_keys(
    pairs: Sequence[Tuple[str, object]],
) -> Dict[str, object]:
    result: Dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _load_health_baseline(
    root: Path,
    baseline_path: Path,
    expected_sha256: str,
) -> BaselineInfo:
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValidationRuntimeError(
            "--baseline-sha256 must be 64 lowercase hexadecimal characters"
        )
    raw_path = Path(baseline_path)
    baseline_relative = _normalise_contract_path(
        raw_path,
        required_suffix=".json",
        description="health baseline path",
    )
    candidate = root.joinpath(*PurePosixPath(baseline_relative).parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationRuntimeError("cannot resolve health baseline safely") from exc
    if not _is_within(resolved, root):
        raise ValidationRuntimeError("health baseline escapes project root")
    if not resolved.is_file():
        raise ValidationRuntimeError("health baseline is not a file")
    try:
        payload = resolved.read_bytes()
        document = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_json_object_without_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationRuntimeError("cannot read health baseline as strict UTF-8 JSON") from exc
    except ValueError as exc:
        raise ValidationRuntimeError("health baseline contains a duplicate JSON key") from exc

    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValidationRuntimeError(
            "health baseline SHA-256 does not match the separately approved digest"
        )

    if not isinstance(document, dict) or set(document) != {
        "format_version",
        "ruleset",
        "measurements",
        "source_fingerprints",
    }:
        raise ValidationRuntimeError(
            "health baseline must contain exactly format_version, ruleset, measurements, "
            "and source_fingerprints"
        )
    if document["format_version"] != 1 or isinstance(document["format_version"], bool):
        raise ValidationRuntimeError("health baseline format_version must be integer 1")
    if document["ruleset"] != SUPPORTED_RULESET or isinstance(document["ruleset"], bool):
        raise ValidationRuntimeError(
            f"health baseline ruleset must be integer {SUPPORTED_RULESET}"
        )
    records = document["measurements"]
    if not isinstance(records, list):
        raise ValidationRuntimeError("health baseline measurements must be a list")
    fingerprint_records = document["source_fingerprints"]
    if not isinstance(fingerprint_records, list):
        raise ValidationRuntimeError("health baseline source_fingerprints must be a list")

    expected_value_keys = {
        "CONTEXT_SIZE_BUDGET": {"bytes", "lines"},
        "CONTEXT_RELEASE_HEADING": {"count"},
        "CONTEXT_VOLATILE_DENSITY": {
            "density_basis_points",
            "prose_lines",
            "volatile_lines",
        },
        "NUMERIC_HEADING_REGRESSION": {"count"},
    }
    measurements: Dict[Tuple[str, str], Mapping[str, int]] = {}
    signatures: Dict[Tuple[str, str], Tuple[str, ...]] = {}
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {
            "code",
            "path",
            "values",
            "signatures",
        }:
            raise ValidationRuntimeError(
                "health baseline measurement "
                f"{index} must contain exactly code, path, values, and signatures"
            )
        code = record["code"]
        path = record["path"]
        values = record["values"]
        raw_signatures = record["signatures"]
        if not isinstance(code, str) or code not in HEALTH_CODES:
            raise ValidationRuntimeError(
                f"health baseline measurement {index} has unsupported code {code!r}"
            )
        normalised_path = _normalise_contract_path(
            path,
            required_suffix=".md",
            description=f"health baseline measurement {index} path",
        )
        measurement_target = root.joinpath(
            *PurePosixPath(normalised_path).parts
        ).resolve(strict=False)
        if not _is_within(measurement_target, root):
            raise ValidationRuntimeError(
                f"health baseline measurement {index} path escapes project root"
            )
        if not isinstance(values, dict) or set(values) != expected_value_keys[code]:
            expected = ", ".join(sorted(expected_value_keys[code]))
            raise ValidationRuntimeError(
                f"health baseline measurement {index} values for {code} must contain "
                f"exactly: {expected}"
            )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in values.values()
        ):
            raise ValidationRuntimeError(
                f"health baseline measurement {index} values must be non-negative integers"
            )
        if (
            not isinstance(raw_signatures, list)
            or any(
                not isinstance(signature, str)
                or re.fullmatch(r"[0-9a-f]{64}", signature) is None
                for signature in raw_signatures
            )
            or raw_signatures != sorted(set(raw_signatures))
        ):
            raise ValidationRuntimeError(
                f"health baseline measurement {index} signatures must be unique sorted SHA-256 values"
            )
        if code == "CONTEXT_SIZE_BUDGET" and raw_signatures:
            raise ValidationRuntimeError(
                f"health baseline measurement {index} size signatures must be empty"
            )
        if code.startswith("CONTEXT_") and normalised_path != ".planning/context.md":
            raise ValidationRuntimeError(
                f"health baseline measurement {index} has an invalid context path"
            )
        if code == "CONTEXT_VOLATILE_DENSITY" and (
            values["density_basis_points"] > 10_000
            or values["volatile_lines"] > values["prose_lines"]
        ):
            raise ValidationRuntimeError(
                f"health baseline measurement {index} has inconsistent density values"
            )
        key = (code, normalised_path)
        if key in measurements:
            raise ValidationRuntimeError(
                f"health baseline contains duplicate measurement for {code} at {path}"
            )
        measurements[key] = dict(values)
        signatures[key] = tuple(raw_signatures)

    source_fingerprints: Dict[str, str] = {}
    for index, record in enumerate(fingerprint_records):
        if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
            raise ValidationRuntimeError(
                f"health baseline source fingerprint {index} must contain exactly path and sha256"
            )
        path = record["path"]
        sha256 = record["sha256"]
        normalised_path = _normalise_contract_path(
            path,
            required_suffix=".md",
            description=f"health baseline source fingerprint {index} path",
        )
        fingerprint_target = root.joinpath(
            *PurePosixPath(normalised_path).parts
        ).resolve(strict=False)
        if not _is_within(fingerprint_target, root):
            raise ValidationRuntimeError(
                f"health baseline source fingerprint {index} path escapes project root"
            )
        if not isinstance(sha256, str) or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            raise ValidationRuntimeError(
                f"health baseline source fingerprint {index} sha256 must be 64 lowercase hex characters"
            )
        if normalised_path in source_fingerprints:
            raise ValidationRuntimeError(
                f"health baseline contains duplicate source fingerprint for {path}"
            )
        source_fingerprints[normalised_path] = sha256

    measurement_paths = {path for _, path in measurements}
    if set(source_fingerprints) != measurement_paths:
        raise ValidationRuntimeError(
            "health baseline source_fingerprints must cover exactly the measurement source paths"
        )

    return BaselineInfo(
        path=baseline_relative,
        sha256=actual_sha256,
        measurements=measurements,
        signatures=signatures,
        source_fingerprints=source_fingerprints,
    )


def _validate_with_report(
    project_root: Path,
    *,
    health: bool = False,
    baseline: Optional[Path] = None,
    baseline_sha256: Optional[str] = None,
) -> Tuple[Path, ProjectMemoryValidator, List[Issue]]:
    root = _resolve_project_root(project_root)
    if baseline is not None and not health:
        raise ValidationRuntimeError("--baseline requires --health")
    if (baseline is None) != (baseline_sha256 is None):
        raise ValidationRuntimeError(
            "--baseline and --baseline-sha256 must be supplied together"
        )
    baseline_info = (
        _load_health_baseline(root, baseline, baseline_sha256)
        if baseline is not None and baseline_sha256 is not None
        else None
    )
    checker = ProjectMemoryValidator(root, health=health, baseline=baseline_info)
    return root, checker, checker.run()


def validate_project(
    project_root: Path,
    *,
    health: bool = False,
    baseline: Optional[Path] = None,
    baseline_sha256: Optional[str] = None,
) -> List[Issue]:
    """Validate a project root without modifying it.

    The one-argument form retains legacy structural-validation behavior.
    Health findings and an approved ratchet baseline are explicit opt-ins.
    """

    return _validate_with_report(
        project_root,
        health=health,
        baseline=baseline,
        baseline_sha256=baseline_sha256,
    )[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only validation for a Markdown project-memory project."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="project root to inspect (default: current directory)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="include advisory document-responsibility health checks",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="repository-relative, read-only health baseline (requires --health and ruleset 1)",
    )
    parser.add_argument(
        "--baseline-sha256",
        help="separately approved lowercase SHA-256 for --baseline",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def _issue_summary(issues: Sequence[Issue]) -> Dict[str, int]:
    return {
        severity: sum(issue.severity == severity for issue in issues)
        for severity in SEVERITIES
    }


def _json_payload(
    *,
    root: Path,
    health: bool,
    checker: ProjectMemoryValidator,
    issues: Sequence[Issue],
) -> Dict[str, object]:
    summary = _issue_summary(issues)
    review_required = summary["REVIEW"] > 0
    guard_passed = summary["ERROR"] == 0 and not (
        checker.baseline is not None and review_required
    )
    status = "failed" if summary["ERROR"] else "review_required" if review_required else "passed"
    measurements = checker.health_measurements if health else []
    source_fingerprints = checker.health_source_fingerprints if health else []
    baseline_echo: Optional[Dict[str, str]] = None
    if checker.baseline is not None:
        baseline_echo = {
            "path": checker.baseline.path,
            "sha256": checker.baseline.sha256,
        }
    baseline_candidate: Optional[Dict[str, object]] = None
    if (
        health
        and checker._context_ruleset == str(SUPPORTED_RULESET)
        and summary["ERROR"] == 0
    ):
        baseline_candidate = {
            "format_version": 1,
            "ruleset": SUPPORTED_RULESET,
            "measurements": measurements,
            "source_fingerprints": source_fingerprints,
        }
    return {
        "format_version": 1,
        "project_root": str(root),
        "mode": "health" if health else "validate",
        "baseline": baseline_echo,
        "status": status,
        "valid": summary["ERROR"] == 0,
        "guard_passed": guard_passed,
        "review_required": review_required,
        "summary": summary,
        "issues": [issue.as_json() for issue in issues],
        "measurements": measurements,
        "source_fingerprints": source_fingerprints,
        "baseline_candidate": baseline_candidate,
    }


def _runtime_json_payload(project_root: Path, health: bool, message: str) -> Dict[str, object]:
    issue = Issue("VALIDATOR_RUNTIME", ".", 0, message)
    return {
        "format_version": 1,
        "project_root": str(Path(project_root).expanduser().absolute()),
        "mode": "health" if health else "validate",
        "baseline": None,
        "status": "failed",
        "valid": False,
        "guard_passed": False,
        "review_required": False,
        "summary": {"ERROR": 1, "REVIEW": 0, "WARNING": 0, "NOTICE": 0},
        "issues": [issue.as_json()],
        "measurements": [],
        "source_fingerprints": [],
        "baseline_candidate": None,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root, checker, issues = _validate_with_report(
            Path(args.project_root),
            health=args.health,
            baseline=args.baseline,
            baseline_sha256=args.baseline_sha256,
        )
    except ValidationRuntimeError as exc:
        if args.format == "json":
            print(
                json.dumps(
                    _runtime_json_payload(Path(args.project_root), args.health, str(exc)),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            print(f"ERROR [VALIDATOR_RUNTIME] {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        message = f"unexpected I/O failure: {exc}"
        if args.format == "json":
            print(
                json.dumps(
                    _runtime_json_payload(Path(args.project_root), args.health, message),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            print(f"ERROR [VALIDATOR_RUNTIME] {message}", file=sys.stderr)
        return 2

    summary = _issue_summary(issues)
    review_required = summary["REVIEW"] > 0
    review_blocks = checker.baseline is not None and review_required
    if args.format == "json":
        print(
            json.dumps(
                _json_payload(
                    root=root,
                    health=args.health,
                    checker=checker,
                    issues=issues,
                ),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1 if summary["ERROR"] or review_blocks else 0

    for issue in issues:
        print(issue.render())
    if summary["ERROR"]:
        print(f"Validation failed: {summary['ERROR']} error(s).")
        return 1
    if review_blocks:
        print(f"Health review required: {summary['REVIEW']} regression finding(s).")
        return 1
    if issues:
        rendered = ", ".join(
            f"{summary[severity]} {severity.lower()}"
            for severity in SEVERITIES[1:]
            if summary[severity]
        )
        print(f"Validation passed with findings: {rendered}.")
        return 0
    print("Validation passed: project memory is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
