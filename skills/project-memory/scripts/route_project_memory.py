#!/usr/bin/env python3
"""Read-only, deterministic write-preflight routing for Project Memory.

The router does not infer intent from prose and never authorizes a write.  A
caller supplies one machine content kind.  The canonical path is then read
from the ruleset-enabled document index in ``.planning/context.md``.

Exit codes:
    0: one canonical route was found
    1: routing requires review (missing or ambiguous contract data)
    2: invalid input or the project could not be inspected safely
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlsplit

from markdown_links import parse_inline_link, unescape_destination


FORMAT_VERSION = 1
SUPPORTED_RULESET = "1"
CONTENT_KINDS = (
    "stable-intent",
    "protocol-setting",
    "resumable-state",
    "historical-event",
    "topic-detail",
)
CONTEXT_ALLOWED_KINDS = {"stable-intent", "protocol-setting"}
INDEX_HEADINGS = {
    "document index",
    "project memory index",
    "文档索引",
    "项目记忆索引",
}
ROLE_HEADERS = {"role", "角色"}
PATH_HEADERS = {"document", "path", "文档", "路径"}

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
SCHEMA_RE = re.compile(
    r"^\s*(?:[-*]\s+)?Project Memory schema\s*:\s*(\S+)\s*$",
    re.IGNORECASE,
)
RULESET_RE = re.compile(
    r"^\s*(?:[-*]\s+)?Project Memory ruleset\s*:\s*(\S+)\s*$",
    re.IGNORECASE,
)
INLINE_CODE_RE = re.compile(r"^`([^`\n]+)`$")
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")

PERMISSION_NOTE = (
    "This read-only route is advisory and does not authorize creating or "
    "modifying any file; current authorization must be established separately."
)


@dataclass(frozen=True)
class RouteResult:
    """One primary canonical destination obtained from the context index."""

    format_version: int
    status: str
    classification: str
    primary_role: str
    primary_path: str
    context_allowed: bool
    read_only: bool
    authorizes_write: bool
    permission_note: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RouteFailure:
    """A stable, non-sensitive failure suitable for text or JSON output."""

    code: str
    message: str
    review_required: bool
    context_allowed: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "authorizes_write": False,
            "code": self.code,
            "context_allowed": self.context_allowed,
            "format_version": FORMAT_VERSION,
            "message": self.message,
            "permission_note": PERMISSION_NOTE,
            "read_only": True,
            "review_required": self.review_required,
            "status": "review_required" if self.review_required else "error",
        }


class RouteReviewRequired(RuntimeError):
    """The project contract cannot produce one safe canonical route."""

    def __init__(self, code: str, message: str, *, context_allowed: bool = False) -> None:
        super().__init__(message)
        self.failure = RouteFailure(code, message, True, context_allowed)


class RouteInputError(RuntimeError):
    """Input or project state prevents safe inspection."""

    def __init__(self, code: str, message: str, *, context_allowed: bool = False) -> None:
        super().__init__(message)
        self.failure = RouteFailure(code, message, False, context_allowed)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_project_root(raw_root: Path, *, context_allowed: bool) -> Path:
    try:
        root = raw_root.resolve(strict=True)
    except (OSError, RuntimeError, UnicodeError, ValueError):
        raise RouteInputError(
            "PROJECT_ROOT_INVALID",
            "The project root cannot be resolved safely.",
            context_allowed=context_allowed,
        ) from None
    if not root.is_dir():
        raise RouteInputError(
            "PROJECT_ROOT_INVALID",
            "The project root must be an existing directory.",
            context_allowed=context_allowed,
        )
    return root


def _normalise_relative_path(
    raw: str,
    root: Path,
    *,
    code: str,
    context_allowed: bool = False,
) -> Tuple[str, Path]:
    """Return a safe, normalized project-relative Markdown path.

    Error messages intentionally exclude ``raw`` so an invalid caller-provided
    value cannot be reflected into logs or structured output.
    """

    try:
        raw.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise RouteInputError(
            code,
            "The path must be a normalized, root-relative Markdown path.",
            context_allowed=context_allowed,
        ) from None

    value = raw.strip()
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value)
    if (
        not value
        or raw != value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or "\\" in value
        or value.startswith(("/", "~"))
        or windows.is_absolute()
        or bool(windows.drive)
        or posix.is_absolute()
        or any(part in {"", ".", ".."} for part in posix.parts)
        or posix.suffix.lower() != ".md"
        or value != posix.as_posix()
    ):
        raise RouteInputError(
            code,
            "The path must be a normalized, root-relative Markdown path.",
            context_allowed=context_allowed,
        )

    normalized = posix.as_posix()
    candidate = root.joinpath(*posix.parts)
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError, UnicodeError, ValueError):
        raise RouteInputError(
            code,
            "The path cannot be resolved safely.",
            context_allowed=context_allowed,
        ) from None
    if not _is_within(resolved, root):
        raise RouteInputError(
            code,
            "The path escapes the project root.",
            context_allowed=context_allowed,
        )
    return normalized, resolved


def _read_context(root: Path, *, context_allowed: bool) -> str:
    context = root / ".planning" / "context.md"
    try:
        resolved = context.resolve(strict=False)
    except (OSError, RuntimeError):
        raise RouteInputError(
            "CONTEXT_UNSAFE",
            "The canonical context path cannot be resolved safely.",
            context_allowed=context_allowed,
        ) from None
    if not _is_within(resolved, root):
        raise RouteInputError(
            "CONTEXT_UNSAFE",
            "The canonical context path escapes the project root.",
            context_allowed=context_allowed,
        )
    if not resolved.is_file():
        raise RouteReviewRequired(
            "CONTEXT_MISSING",
            "A readable .planning/context.md is required before routing.",
            context_allowed=context_allowed,
        )
    try:
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise RouteInputError(
            "CONTEXT_UNREADABLE",
            "The canonical context file cannot be read as UTF-8.",
            context_allowed=context_allowed,
        ) from None


def _visible_markdown_lines(text: str) -> List[str]:
    """Return active Markdown lines, excluding fenced examples and comments."""

    visible_lines: List[str] = []
    in_fence = False
    fence_char = ""
    fence_length = 0
    in_comment = False
    for original in text.splitlines():
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
                visible_lines.append("")
                continue
        if in_fence:
            continue

        remaining = original
        parts: List[str] = []
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
                parts.append(remaining)
                break
            parts.append(remaining[:start])
            end = remaining.find("-->", start + 4)
            if end < 0:
                in_comment = True
                remaining = ""
                break
            remaining = remaining[end + 3 :]
        visible_lines.append("".join(parts))
    return visible_lines


def _require_supported_ruleset(text: str, *, context_allowed: bool) -> None:
    values = [
        match.group(1)
        for line in _visible_markdown_lines(text)
        if (match := RULESET_RE.match(line)) is not None
    ]
    if not values:
        raise RouteReviewRequired(
            "RULESET_NOT_ENABLED",
            "The project has no machine-readable Project Memory ruleset.",
            context_allowed=context_allowed,
        )
    if len(values) != 1 or values[0] != SUPPORTED_RULESET:
        raise RouteReviewRequired(
            "RULESET_UNSUPPORTED",
            "The Project Memory ruleset is ambiguous or unsupported.",
            context_allowed=context_allowed,
        )


def _require_supported_schema(text: str, *, context_allowed: bool) -> None:
    values = [
        match.group(1)
        for line in _visible_markdown_lines(text)
        if (match := SCHEMA_RE.match(line)) is not None
    ]
    if len(values) != 1 or values[0] != "1":
        raise RouteReviewRequired(
            "SCHEMA_UNSUPPORTED",
            "Exactly one supported Project Memory schema is required for routing.",
            context_allowed=context_allowed,
        )


def _normalise_heading(raw: str) -> str:
    return re.sub(r"\s+", " ", raw.strip()).casefold()


def _conventional_state_exists(root: Path, *, context_allowed: bool) -> bool:
    """Return whether a conventional state Markdown record actually exists."""

    state_file = root / ".planning/state.md"
    state_directory = root / ".planning/state"
    for candidate in (state_file, state_directory):
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError):
            raise RouteInputError(
                "STATE_PATH_UNSAFE",
                "A conventional state path cannot be resolved safely.",
                context_allowed=context_allowed,
            ) from None
        if not _is_within(resolved, root):
            raise RouteInputError(
                "STATE_PATH_UNSAFE",
                "A conventional state path escapes the project root.",
                context_allowed=context_allowed,
            )

    resolved_file = state_file.resolve(strict=False)
    if resolved_file.is_file():
        return True

    resolved_directory = state_directory.resolve(strict=False)
    if not resolved_directory.is_dir():
        return False
    try:
        for dirpath, dirnames, filenames in os.walk(
            resolved_directory,
            followlinks=False,
        ):
            directory = Path(dirpath)
            resolved_files: Dict[str, Path] = {}
            for name in list(dirnames) + list(filenames):
                candidate = directory / name
                try:
                    resolved = candidate.resolve(strict=False)
                except (OSError, RuntimeError):
                    raise RouteInputError(
                        "STATE_PATH_UNSAFE",
                        "A conventional state path cannot be resolved safely.",
                        context_allowed=context_allowed,
                    ) from None
                if not _is_within(resolved, root):
                    raise RouteInputError(
                        "STATE_PATH_UNSAFE",
                        "A conventional state path escapes the project root.",
                        context_allowed=context_allowed,
                    )
                if name in filenames:
                    resolved_files[name] = resolved
            if any(
                Path(name).suffix.lower() == ".md" and resolved_files[name].is_file()
                for name in filenames
            ):
                return True
    except OSError:
        raise RouteInputError(
            "STATE_PATH_UNSAFE",
            "The conventional state directory cannot be inspected safely.",
            context_allowed=context_allowed,
        ) from None
    return False


def _index_sections(text: str) -> List[List[str]]:
    lines = _visible_markdown_lines(text)
    sections: List[List[str]] = []
    index = 0
    while index < len(lines):
        match = HEADING_RE.match(lines[index])
        if match is None or _normalise_heading(match.group(2)) not in INDEX_HEADINGS:
            index += 1
            continue
        level = len(match.group(1))
        end = index + 1
        while end < len(lines):
            following = HEADING_RE.match(lines[end])
            if following is not None and len(following.group(1)) <= level:
                break
            end += 1
        sections.append(lines[index + 1 : end])
        index = end
    return sections


def _table_cells(line: str) -> Optional[List[str]]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _cell_path(cell: str) -> Tuple[str, bool]:
    inline = INLINE_CODE_RE.match(cell)
    if inline is not None:
        return inline.group(1), False
    link = parse_inline_link(cell)
    if link is not None and link[2] == len(cell) and not cell.startswith("!"):
        return unescape_destination(link[0]), True
    return cell, False


def _normalise_markdown_index_path(
    raw: str,
    root: Path,
    *,
    context_allowed: bool,
) -> Tuple[str, Path]:
    """Resolve a standard Markdown-link target relative to context.md."""

    try:
        raw.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise RouteInputError(
            "INDEX_PATH_UNSAFE",
            "An indexed Markdown target is not a safe local path.",
            context_allowed=context_allowed,
        ) from None
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise RouteInputError(
            "INDEX_PATH_UNSAFE",
            "An indexed Markdown target is not a safe local path.",
            context_allowed=context_allowed,
        )
    try:
        parsed = urlsplit(raw.strip())
    except ValueError:
        raise RouteInputError(
            "INDEX_PATH_UNSAFE",
            "An indexed Markdown target is not a safe local path.",
            context_allowed=context_allowed,
        ) from None
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
        raise RouteInputError(
            "INDEX_PATH_UNSAFE",
            "An indexed Markdown target is not a safe local path.",
            context_allowed=context_allowed,
        )
    project_relative = posixpath.normpath(posixpath.join(".planning", local))
    return _normalise_relative_path(
        project_relative,
        root,
        code="INDEX_PATH_UNSAFE",
        context_allowed=context_allowed,
    )


def _indexed_routes(
    text: str,
    root: Path,
    *,
    context_allowed: bool,
) -> Dict[str, List[str]]:
    sections = _index_sections(text)
    if len(sections) != 1:
        raise RouteReviewRequired(
            "DOCUMENT_INDEX_AMBIGUOUS",
            "Exactly one Project Memory document-index section is required.",
            context_allowed=context_allowed,
        )

    routes: Dict[str, List[str]] = {kind: [] for kind in CONTENT_KINDS}
    route_identities: Dict[str, List[str]] = {kind: [] for kind in CONTENT_KINDS}
    header: Optional[Tuple[int, int]] = None
    typed_table_count = 0
    typed_table_ended = False
    for line in sections[0]:
        cells = _table_cells(line)
        if cells is None:
            if header is not None:
                typed_table_ended = True
            header = None
            continue
        folded = [_normalise_heading(cell) for cell in cells]
        if cells and all(
            TABLE_SEPARATOR_RE.fullmatch(cell.replace(" ", "")) is not None
            for cell in folded
        ):
            continue
        role_indexes = [i for i, value in enumerate(folded) if value in ROLE_HEADERS]
        path_indexes = [i for i, value in enumerate(folded) if value in PATH_HEADERS]
        if len(role_indexes) == 1 and len(path_indexes) == 1:
            header = (role_indexes[0], path_indexes[0])
            typed_table_count += 1
            continue
        if header is None:
            if typed_table_ended and any(value in routes for value in folded):
                raise RouteReviewRequired(
                    "DOCUMENT_INDEX_TABLE_INVALID",
                    "A typed document-index table cannot continue after it ends.",
                    context_allowed=context_allowed,
                )
            continue
        role_index, path_index = header
        if max(role_index, path_index) >= len(cells):
            raise RouteReviewRequired(
                "DOCUMENT_INDEX_ROW_INVALID",
                "A typed document-index row is missing a role or document cell.",
                context_allowed=context_allowed,
            )
        role = cells[role_index].strip().casefold()
        if role not in routes:
            raise RouteReviewRequired(
                "DOCUMENT_INDEX_ROLE_UNSUPPORTED",
                "A typed document-index row uses an unsupported role token.",
                context_allowed=context_allowed,
            )
        raw_path, markdown_relative = _cell_path(cells[path_index])
        if markdown_relative:
            normalized, resolved = _normalise_markdown_index_path(
                raw_path,
                root,
                context_allowed=context_allowed,
            )
        else:
            normalized, resolved = _normalise_relative_path(
                raw_path,
                root,
                code="INDEX_PATH_UNSAFE",
                context_allowed=context_allowed,
            )
        if not resolved.is_file():
            raise RouteReviewRequired(
                "CANONICAL_TARGET_MISSING",
                "An indexed canonical target does not exist as a file.",
                context_allowed=context_allowed,
            )
        routes[role].append(normalized)
        route_identities[role].append(resolved.as_posix())

    if typed_table_count != 1:
        raise RouteReviewRequired(
            "DOCUMENT_INDEX_TABLE_AMBIGUOUS",
            "Exactly one typed role/document table is required.",
            context_allowed=context_allowed,
        )

    for role in ("stable-intent", "protocol-setting", "historical-event"):
        if not routes[role]:
            raise RouteReviewRequired(
                "CANONICAL_ROUTE_MISSING",
                "A required canonical route is missing from the document index.",
                context_allowed=context_allowed,
            )
        if len(routes[role]) != 1:
            raise RouteReviewRequired(
                "CANONICAL_ROUTE_AMBIGUOUS",
                "A required role has more than one canonical route.",
                context_allowed=context_allowed,
            )

    if any(
        routes[role] != [".planning/context.md"]
        for role in CONTEXT_ALLOWED_KINDS
    ):
        raise RouteReviewRequired(
            "CANONICAL_ROUTE_INVALID",
            "Stable intent and protocol settings must route to .planning/context.md.",
            context_allowed=context_allowed,
        )

    state_exists = _conventional_state_exists(
        root,
        context_allowed=context_allowed,
    )
    if state_exists and not routes["resumable-state"]:
        raise RouteReviewRequired(
            "CANONICAL_ROUTE_MISSING",
            "Existing resumable state has no canonical route.",
            context_allowed=context_allowed,
        )
    if len(routes["resumable-state"]) > 1:
        raise RouteReviewRequired(
            "CANONICAL_ROUTE_AMBIGUOUS",
            "Resumable state has more than one canonical route.",
            context_allowed=context_allowed,
        )

    for role, paths in routes.items():
        identities = route_identities[role]
        if len(paths) != len(set(paths)) or len(identities) != len(set(identities)):
            raise RouteReviewRequired(
                "CANONICAL_ROUTE_AMBIGUOUS",
                "A role repeats or aliases the same canonical target.",
                context_allowed=context_allowed,
            )

    roles_by_identity: Dict[str, set[str]] = {}
    for role, identities in route_identities.items():
        for identity in identities:
            roles_by_identity.setdefault(identity, set()).add(role)
    if any(
        len(roles) > 1 and roles != {"stable-intent", "protocol-setting"}
        for roles in roles_by_identity.values()
    ):
        raise RouteReviewRequired(
            "CANONICAL_ROLE_COLLISION",
            "One canonical path is assigned incompatible roles.",
            context_allowed=context_allowed,
        )
    return routes


def route_project_memory(
    project_root: Path | str,
    content_type: str,
    topic_path: Optional[str] = None,
) -> RouteResult:
    """Resolve one explicit content type to its indexed canonical path.

    No natural-language classification or write is performed.  Missing and
    ambiguous mappings require review instead of falling back to filenames.
    """

    if content_type not in CONTENT_KINDS:
        raise RouteInputError(
            "INVALID_KIND",
            "The content kind is not supported.",
        )
    context_allowed = content_type in CONTEXT_ALLOWED_KINDS
    root = _resolve_project_root(Path(project_root), context_allowed=context_allowed)
    context = _read_context(root, context_allowed=context_allowed)
    _require_supported_schema(context, context_allowed=context_allowed)
    _require_supported_ruleset(context, context_allowed=context_allowed)
    routes = _indexed_routes(context, root, context_allowed=context_allowed)

    if content_type == "topic-detail":
        if topic_path is None:
            raise RouteReviewRequired(
                "TOPIC_PATH_REQUIRED",
                "Topic detail requires one explicit indexed --topic-path.",
            )
        try:
            requested, _ = _normalise_relative_path(
                topic_path,
                root,
                code="TOPIC_PATH_INVALID",
                context_allowed=context_allowed,
            )
        except RouteInputError as exc:
            raise RouteReviewRequired(
                exc.failure.code,
                exc.failure.message,
                context_allowed=context_allowed,
            ) from None
        matches = [path for path in routes[content_type] if path == requested]
    else:
        if topic_path is not None:
            raise RouteInputError(
                "TOPIC_PATH_NOT_APPLICABLE",
                "--topic-path is valid only for topic-detail.",
                context_allowed=context_allowed,
            )
        matches = routes[content_type]

    if not matches:
        raise RouteReviewRequired(
            "CANONICAL_ROUTE_MISSING",
            "No matching canonical route is declared in the document index.",
            context_allowed=context_allowed,
        )
    if len(matches) != 1:
        raise RouteReviewRequired(
            "CANONICAL_ROUTE_AMBIGUOUS",
            "More than one matching canonical route is declared in the document index.",
            context_allowed=context_allowed,
        )

    return RouteResult(
        format_version=FORMAT_VERSION,
        status="routed",
        classification=content_type,
        primary_role=content_type,
        primary_path=matches[0],
        context_allowed=context_allowed,
        read_only=True,
        authorizes_write=False,
        permission_note=PERMISSION_NOTE,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve an explicit content kind using a Project Memory index.",
    )
    parser.add_argument("project_root", help="project root containing .planning/context.md")
    parser.add_argument("--kind", required=True, help="explicit machine content kind")
    parser.add_argument("--topic-path", help="indexed root-relative path for topic-detail")
    parser.add_argument("--format", default="text", help="text or json")
    return parser


def _render_text(result: RouteResult) -> str:
    return (
        f"ROUTE classification={result.classification} "
        f"primary_role={result.primary_role} primary_path={result.primary_path} "
        f"context_allowed={str(result.context_allowed).lower()}\n"
        f"READ_ONLY read_only=true authorizes_write=false\n"
        f"{result.permission_note}"
    )


def _render_json(payload: Dict[str, object]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _emit_failure(failure: RouteFailure, output_format: str) -> None:
    if output_format == "json":
        print(_render_json(failure.to_dict()))
        return
    print(
        f"{'REVIEW' if failure.review_required else 'ERROR'} [{failure.code}] "
        f"{failure.message}\nREAD_ONLY read_only=true authorizes_write=false\n"
        f"{failure.permission_note}",
        file=sys.stderr,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_format = args.format.casefold()
    if output_format not in {"text", "json"}:
        failure = RouteFailure(
            "INVALID_FORMAT",
            "The output format must be text or json.",
            False,
        )
        _emit_failure(failure, "text")
        return 2

    try:
        result = route_project_memory(args.project_root, args.kind, args.topic_path)
    except RouteReviewRequired as exc:
        _emit_failure(exc.failure, output_format)
        return 1
    except RouteInputError as exc:
        _emit_failure(exc.failure, output_format)
        return 2

    if output_format == "json":
        print(_render_json(result.to_dict()))
    else:
        print(_render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
