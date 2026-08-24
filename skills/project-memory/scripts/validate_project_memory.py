#!/usr/bin/env python3
"""Read-only structural validation for a project-memory project.

Exit codes:
    0: validation passed
    1: validation completed and found project-memory errors
    2: invalid invocation or the project could not be inspected reliably
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote, urlsplit


SUPPORTED_ENTRY_SCHEMA = 1
ENTRY_FILENAMES = ("AGENTS.md", "CLAUDE.md")
REQUIRED_FILES = (".planning/context.md", ".planning/release-log.md")

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
    r"<!--\s*project-memory:start\s+schema\s*=\s*([^\s>]+)\s*-->", re.IGNORECASE
)
END_MARKER_RE = re.compile(r"<!--\s*project-memory:end\s*-->", re.IGNORECASE)
ANY_START_MARKER_RE = re.compile(r"<!--\s*project-memory:start\b.*?-->", re.IGNORECASE)
CONTEXT_SCHEMA_RE = re.compile(
    r"^\s*(?:[-*]\s+)?Project Memory schema\s*:\s*(\S+)\s*$", re.IGNORECASE
)

MARKDOWN_LINK_RE = re.compile(
    r"!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)", re.MULTILINE
)
REFERENCE_LINK_RE = re.compile(
    r"^\s{0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", re.MULTILINE
)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STATE_RE = re.compile(
    r"^\s*[-*]\s*(?:状态|status)\s*[:：]\s*(.+?)\s*$", re.IGNORECASE
)
ADR_FILENAME_RE = re.compile(r"^(?:ADR[-_])?(\d{4})(?:[-_. ]|$)", re.IGNORECASE)
ADR_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s+(?:ADR[-_ ]*)?(\d{4})(?:\b|[-_:：])", re.IGNORECASE
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
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
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
    """One deterministic validation error."""

    code: str
    path: str
    line: int
    message: str

    def render(self) -> str:
        location = self.path
        if self.line:
            location = f"{location}:{self.line}"
        return f"ERROR [{self.code}] {location}: {self.message}"


class ValidationRuntimeError(RuntimeError):
    """The validator could not safely or reliably inspect the requested root."""


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
    def __init__(self, root: Path) -> None:
        self.root = root
        self._issues: List[Issue] = []
        self._issue_keys: Set[Tuple[str, str, int, str]] = set()
        self._texts: Dict[Path, str] = {}

    def run(self) -> List[Issue]:
        self._check_planning_boundary_and_required_files()
        markdown_files = self._collect_planning_markdown()
        context_schema = self._check_context_schema()
        self._check_entrypoints(context_schema)

        for path in markdown_files:
            text = self._read_text(path)
            if text is None:
                continue
            self._texts[path] = text
            self._check_markdown_links(path, text)
            self._check_placeholders(path, text)

        self._check_document_index()
        self._check_duplicate_adr_ids()
        self._check_duplicate_experience_ids(markdown_files)
        self._check_state_files(markdown_files)

        return sorted(
            self._issues,
            key=lambda issue: (issue.path, issue.line, issue.code, issue.message),
        )

    def _add(self, code: str, path: Path, message: str, line: int = 0) -> None:
        display_path = self._display_path(path)
        key = (code, display_path, line, message)
        if key in self._issue_keys:
            return
        self._issue_keys.add(key)
        self._issues.append(Issue(code, display_path, line, message))

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
            path = self.root / relative
            self._check_symlink(path)
            resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
            if resolved is None:
                continue
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
        try:
            for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
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

    def _read_text(self, path: Path) -> Optional[str]:
        resolved = self._safe_resolve(path, code="SYMLINK_ESCAPE")
        if resolved is None:
            return None
        try:
            return resolved.read_text(encoding="utf-8")
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
        for line_number, line in enumerate(text.splitlines(), 1):
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

    def _check_entrypoints(self, context_schema: Optional[str]) -> None:
        managed_block_count = 0
        for filename in ENTRY_FILENAMES:
            path = self.root / filename
            if not os.path.lexists(path):
                continue
            self._check_symlink(path)
            text = self._read_text(path)
            if text is None:
                continue
            blocks = self._managed_blocks(path, text)
            managed_block_count += len(blocks)
            if len(blocks) > 1:
                self._add(
                    "ENTRY_BLOCK_MULTIPLE",
                    path,
                    "entry file contains more than one project-memory managed block",
                )
            for schema, start_line, block_text in blocks:
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
                if ".planning/context.md" not in block_text:
                    self._add(
                        "ENTRY_CONTEXT_LINK_MISSING",
                        path,
                        "managed block must point to .planning/context.md",
                        start_line,
                    )
                self._check_markdown_links(path, block_text, line_offset=start_line)
                self._check_placeholders(path, block_text, line_offset=start_line)

        if managed_block_count == 0:
            self._add(
                "ENTRY_BLOCK_MISSING",
                self.root,
                "AGENTS.md or CLAUDE.md must contain a project-memory managed block",
            )

    def _managed_blocks(self, path: Path, text: str) -> List[Tuple[str, int, str]]:
        blocks: List[Tuple[str, int, str]] = []
        open_marker: Optional[Tuple[str, int, int]] = None
        lines = text.splitlines(keepends=True)
        offset = 0

        for line_number, line_text in enumerate(lines, 1):
            start_match = START_MARKER_RE.search(line_text)
            any_start = ANY_START_MARKER_RE.search(line_text)
            end_match = END_MARKER_RE.search(line_text)

            if any_start and not start_match:
                self._add(
                    "ENTRY_START_MARKER_INVALID",
                    path,
                    "start marker must use <!-- project-memory:start schema=N -->",
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
                    open_marker = (start_match.group(1), line_number, offset + len(line_text))
            if end_match:
                if open_marker is None:
                    self._add(
                        "ENTRY_END_WITHOUT_START",
                        path,
                        "managed block end marker has no matching start marker",
                        line_number,
                    )
                else:
                    schema, start_line, content_start = open_marker
                    content_end = offset + end_match.start()
                    blocks.append((schema, start_line, text[content_start:content_end]))
                    open_marker = None
            offset += len(line_text)

        if open_marker is not None:
            self._add(
                "ENTRY_BLOCK_UNCLOSED",
                path,
                "managed block start marker has no matching end marker",
                open_marker[1],
            )
        return blocks

    def _extract_markdown_targets(self, text: str) -> Iterable[Tuple[str, int]]:
        for regex in (MARKDOWN_LINK_RE, REFERENCE_LINK_RE):
            for match in regex.finditer(text):
                yield match.group(1), _line_number(text, match.start(1))

    def _normalise_link_target(self, raw: str) -> Optional[str]:
        target = raw.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        target = target.replace(r"\(", "(").replace(r"\)", ")")
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
        in_fence = False
        fence_char = ""
        for local_line, original_line in enumerate(text.splitlines(), 1):
            fence = FENCE_RE.match(original_line)
            if fence:
                marker = fence.group(1)[0]
                if not in_fence:
                    in_fence = True
                    fence_char = marker
                elif marker == fence_char:
                    in_fence = False
                    fence_char = ""
                continue
            if in_fence:
                continue

            line_text = HTML_COMMENT_RE.sub("", original_line)
            line_number = local_line + line_offset
            for match in ANGLE_PLACEHOLDER_RE.finditer(line_text):
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
        return path, text

    def _check_document_index(self) -> None:
        context = self._context_text()
        if context is None:
            return
        path, text = context
        lines = text.splitlines()
        section: Optional[Tuple[int, int, int]] = None

        for index, line in enumerate(lines):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            title = heading.group(2).strip().lower()
            if "文档索引" in title or "document index" in title or "documentation index" in title:
                section = (index, len(heading.group(1)), index + 1)
                break
        if section is None:
            return

        heading_index, heading_level, content_start = section
        content_end = len(lines)
        for index in range(content_start, len(lines)):
            heading = HEADING_RE.match(lines[index])
            if heading and len(heading.group(1)) <= heading_level:
                content_end = index
                break

        section_text = "\n".join(lines[content_start:content_end])
        for raw_target, local_line in self._extract_markdown_targets(section_text):
            target = self._normalise_link_target(raw_target)
            if target is None:
                continue
            line = content_start + local_line
            self._check_index_target(path, target, line, markdown_relative=True)
        for match in INLINE_CODE_RE.finditer(section_text):
            raw_target = match.group(1).strip()
            if not self._looks_like_index_path(raw_target):
                continue
            local_line = _line_number(section_text, match.start(1))
            line = content_start + local_line
            self._check_index_target(path, raw_target, line, markdown_relative=False)

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

    def _check_duplicate_adr_ids(self) -> None:
        definitions: Dict[str, Dict[Path, Dict[str, object]]] = {}
        for path in self._adr_files():
            filename_match = ADR_FILENAME_RE.match(path.name)
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
            for line_number, line in enumerate(text.splitlines(), 1):
                heading_match = ADR_HEADING_RE.match(line)
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

    def _check_state_files(self, markdown_files: Sequence[Path]) -> None:
        state_file = self.root / ".planning/state.md"
        state_directory = self.root / ".planning/state"
        for path in markdown_files:
            is_state = path == state_file
            if not is_state:
                try:
                    path.relative_to(state_directory)
                    is_state = True
                except ValueError:
                    pass
            if not is_state:
                continue
            text = self._texts.get(path)
            if text is not None:
                self._check_state(path, text)

    def _check_state(self, path: Path, text: str) -> None:
        statuses: List[Tuple[str, int]] = []
        for line_number, line in enumerate(text.splitlines(), 1):
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

    def _has_exact_next_action(self, text: str) -> bool:
        lines = text.splitlines()
        start: Optional[Tuple[int, int]] = None
        for index, line in enumerate(lines):
            heading = HEADING_RE.match(line)
            if not heading:
                continue
            title = re.sub(r"^\d+[.)、]\s*", "", heading.group(2).strip().lower())
            if title in {"精确下一步", "exact next step", "next action"}:
                start = (index + 1, len(heading.group(1)))
                break
        if start is None:
            return False
        content_start, level = start
        for line in lines[content_start:]:
            heading = HEADING_RE.match(line)
            if heading and len(heading.group(1)) <= level:
                break
            cleaned = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line).strip()
            if not cleaned or cleaned.startswith("<!--"):
                continue
            if cleaned.lower() in {"无", "none", "n/a", "not applicable", "待补充"}:
                continue
            if ANGLE_PLACEHOLDER_RE.search(cleaned) or BRACE_PLACEHOLDER_RE.search(cleaned):
                continue
            if cleaned.startswith(("完成信号：", "完成信号:", "completion signal:")):
                continue
            return True
        return False


def validate_project(project_root: Path) -> List[Issue]:
    """Validate a project root without modifying it."""

    raw_root = Path(project_root).expanduser()
    try:
        root = raw_root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValidationRuntimeError(f"cannot resolve project root {raw_root}: {exc}") from exc
    if not root.is_dir():
        raise ValidationRuntimeError(f"project root is not a directory: {root}")
    return ProjectMemoryValidator(root).run()


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
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        issues = validate_project(Path(args.project_root))
    except ValidationRuntimeError as exc:
        print(f"ERROR [VALIDATOR_RUNTIME] {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR [VALIDATOR_RUNTIME] unexpected I/O failure: {exc}", file=sys.stderr)
        return 2

    for issue in issues:
        print(issue.render())
    if issues:
        print(f"Validation failed: {len(issues)} error(s).")
        return 1
    print("Validation passed: project memory is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
