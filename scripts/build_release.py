#!/usr/bin/env python3
"""Build deterministic standalone and plugin archives for Project Memory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath


EPOCH = (1980, 1, 1, 0, 0, 0)
IGNORED_CACHE_PARTS = {"__pycache__"}


def fail(message: str) -> "NoReturn":
    raise SystemExit(message)


def validate_input_path(repo: Path, path: Path) -> None:
    """Reject aliases and escapes below the already-normalized repository root."""
    try:
        relative = path.relative_to(repo)
    except ValueError:
        fail(f"Release input is outside repository: {path}")
    current = repo
    try:
        for part in relative.parts:
            current = current / part
            if stat.S_ISLNK(current.lstat().st_mode):
                fail(f"Release input must not contain symlinks: {current}")
        path.resolve(strict=True).relative_to(repo)
    except ValueError:
        fail(f"Release input resolves outside repository: {path}")
    except (OSError, RuntimeError) as exc:
        fail(f"Cannot inspect release input {path}: {exc}")


def load_version(repo: Path) -> str:
    manifest = repo / ".codex-plugin" / "plugin.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read {manifest}: {exc}")
    version = data.get("version")
    if not isinstance(version, str) or not re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
        version,
    ):
        fail(f"Manifest version is not strict semver: {version!r}")
    return version


def files_under(root: Path) -> list[Path]:
    if root.is_symlink():
        fail(f"Release input must not contain symlinks: {root}")
    if not root.is_dir():
        fail(f"Missing directory: {root}")
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            fail(f"Release input must not contain symlinks: {path}")
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_CACHE_PARTS for part in rel.parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        if ".DS_Store" in rel.parts:
            fail(f"Disallowed release file: {path}")
        files.append(path)
    return files


def validate_skill_files(skill_root: Path) -> list[Path]:
    files = files_under(skill_root)
    required = {
        PurePosixPath("SKILL.md"),
        PurePosixPath("agents/openai.yaml"),
    }
    relative = {PurePosixPath(path.relative_to(skill_root).as_posix()) for path in files}
    missing = required - relative
    if missing:
        fail("Missing skill files: " + ", ".join(map(str, sorted(missing))))

    for rel in relative:
        allowed = (
            rel == PurePosixPath("SKILL.md")
            or rel == PurePosixPath("agents/openai.yaml")
            or (len(rel.parts) == 2 and rel.parts[0] == "references" and rel.suffix == ".md")
            or (len(rel.parts) == 2 and rel.parts[0] == "scripts" and rel.suffix == ".py")
        )
        if not allowed:
            fail(f"Unexpected file in standalone skill: {rel}")
    return files


def zip_entries(destination: Path, entries: list[tuple[Path, PurePosixPath]]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, arcname in sorted(entries, key=lambda item: str(item[1])):
            info = zipfile.ZipInfo(str(arcname), EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if source.suffix == ".py" else 0o644) << 16
            archive.writestr(info, source.read_bytes())


def rooted_entries(root: Path, archive_root: str, selected: list[Path]) -> list[tuple[Path, PurePosixPath]]:
    return [
        (path, PurePosixPath(archive_root) / PurePosixPath(path.relative_to(root).as_posix()))
        for path in selected
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(repo: Path, dist: Path) -> list[Path]:
    repo = repo.resolve()
    dist = dist.resolve()
    skill_root = repo / "skills" / "project-memory"
    codex_manifest = repo / ".codex-plugin" / "plugin.json"
    claude_manifest = repo / ".claude-plugin" / "plugin.json"
    license_file = repo / "LICENSE"

    # Preflight every input before reading a manifest or writing any artifact.
    # Normalize only the repository boundary; resolving individual inputs first
    # would hide symlinks, including aliases that stay inside the repository.
    for source in (skill_root, codex_manifest, claude_manifest, license_file):
        validate_input_path(repo, source)
    skill_files = validate_skill_files(skill_root)
    for source in skill_files:
        validate_input_path(repo, source)
    for required in (codex_manifest, claude_manifest, license_file):
        if not required.is_file():
            fail(f"Missing release input: {required}")
    version = load_version(repo)

    artifacts = [
        dist / f"project-memory-skill-v{version}.zip",
        dist / f"project-memory-codex-plugin-v{version}.zip",
        dist / f"project-memory-claude-plugin-v{version}.zip",
    ]

    standalone = [
        (path, PurePosixPath("project-memory") / PurePosixPath(path.relative_to(skill_root).as_posix()))
        for path in skill_files
    ]
    standalone.append((license_file, PurePosixPath("project-memory/LICENSE")))
    zip_entries(artifacts[0], standalone)

    shared = rooted_entries(repo, "project-memory", skill_files)
    # rooted_entries above preserves the repo-relative skills/project-memory path.
    shared.append((license_file, PurePosixPath("project-memory/LICENSE")))
    zip_entries(
        artifacts[1],
        shared
        + [(codex_manifest, PurePosixPath("project-memory/.codex-plugin/plugin.json"))],
    )
    zip_entries(
        artifacts[2],
        shared
        + [(claude_manifest, PurePosixPath("project-memory/.claude-plugin/plugin.json"))],
    )

    sums = dist / "SHA256SUMS"
    sums.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in artifacts),
        encoding="utf-8",
    )
    return artifacts + [sums]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--dist",
        type=Path,
        help="output directory (default: <repo>/dist)",
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    dist = (args.dist or repo / "dist").resolve()
    for artifact in build(repo, dist):
        print(artifact)
    return 0


if __name__ == "__main__":
    sys.exit(main())
