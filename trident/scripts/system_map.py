#!/usr/bin/env python3
"""Locate, initialize, and refresh Trident's per-repository System Map cache.

The System Map is how Trident remembers how a system works between reviews:
user-facing flows, architecture, contracts and invariants, how to run and prove
behavior, and known hazards. It lives outside the reviewed repository, under
``$TRIDENT_CACHE_DIR`` (default ``~/.cache/trident``), so reviews stay read-only.

This helper owns only bookkeeping: where the map lives, which sections are stale
for a given head, and stamping a section after the model re-verifies it. The
model writes the section content in ``system-map.md``.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "trident-system-map-v1"
SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("flows", "Flows", "User-, job-, and API-facing flows: entry point, how to drive it, and the observable result that proves it works."),
    ("architecture", "Architecture", "Components, ownership, and how data moves from input to storage to output."),
    ("contracts", "Contracts and invariants", "Producer/consumer contracts, documented invariants, ADR constraints, each with a source anchor."),
    ("operations", "Operations and proof", "Exact build, test, launch, doctor, drive, and cleanup commands; disposable data; isolation limits."),
    ("hazards", "Hazards", "Fragile areas, past incidents, reverts, and gotchas that change how a diff should be verified."),
)


def git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=repo, text=True, capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return result.returncode, result.stdout.strip()


def repo_root(repo: Path) -> Path:
    code, out = git(repo, "rev-parse", "--show-toplevel")
    if code != 0 or not out:
        raise SystemExit(f"error: {repo} is not inside a git repository")
    return Path(out)


def repo_key(root: Path) -> str:
    """Stable key: normalized upstream/origin path, else folder name plus a path hash."""
    for remote in ("upstream", "origin"):
        code, url = git(root, "remote", "get-url", remote)
        if code == 0 and url:
            path = re.sub(r"^[a-z]+://([^@/]+@)?[^/]+/", "", url.strip())
            path = re.sub(r"^[^@]+@[^:]+:", "", path)
            path = re.sub(r"\.git$", "", path).strip("/")
            if path:
                return re.sub(r"[^A-Za-z0-9._-]+", "__", path)
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:10]
    return f"{root.name}-{digest}"


def cache_dir(root: Path) -> Path:
    base = Path(os.environ.get("TRIDENT_CACHE_DIR") or Path.home() / ".cache" / "trident")
    return base / repo_key(root)


def paths(root: Path) -> dict[str, Path]:
    directory = cache_dir(root)
    return {"dir": directory, "map": directory / "system-map.md", "index": directory / "system-map.json"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {}
    return json.loads(index_path.read_text(encoding="utf-8"))


def skeleton_markdown(key: str) -> str:
    lines = [
        f"# System Map — {key}",
        "",
        "Maintained by Trident. Every claim names a `path:line` anchor or the command that proved it.",
        "Treat this map as a starting point: re-read anchors in stale sections before relying on them.",
        "",
    ]
    for section_id, title, purpose in SECTIONS:
        lines.extend([f"## {title}", f"<!-- section:{section_id} -->", f"_{purpose}_", "", "Not mapped yet.", ""])
    return "\n".join(lines)


def command_locate(root: Path) -> dict[str, Any]:
    p = paths(root)
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_key": repo_key(root),
        "dir": str(p["dir"]),
        "map": str(p["map"]),
        "index": str(p["index"]),
        "exists": p["map"].exists() and p["index"].exists(),
    }


def command_init(root: Path) -> dict[str, Any]:
    p = paths(root)
    p["dir"].mkdir(parents=True, exist_ok=True)
    created = []
    if not p["map"].exists():
        p["map"].write_text(skeleton_markdown(repo_key(root)), encoding="utf-8")
        created.append(str(p["map"]))
    if not p["index"].exists():
        index = {
            "schema_version": SCHEMA_VERSION,
            "repo_key": repo_key(root),
            "created_at": now(),
            "sections": {
                section_id: {"title": title, "anchors": [], "verified_sha": None, "verified_at": None}
                for section_id, title, _ in SECTIONS
            },
        }
        p["index"].write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        created.append(str(p["index"]))
    return {**command_locate(root), "created": created}


def anchor_matches(anchor: str, changed: str) -> bool:
    anchor = anchor.rstrip("/")
    if any(char in anchor for char in "*?["):
        return fnmatch.fnmatch(changed, anchor)
    return changed == anchor or changed.startswith(anchor + "/")


def changed_since(root: Path, sha: str, head: str) -> list[str] | None:
    code, _ = git(root, "cat-file", "-e", f"{sha}^{{commit}}")
    if code != 0:
        return None
    code, out = git(root, "diff", "--name-only", f"{sha}..{head}")
    if code != 0:
        return None
    return [line for line in out.splitlines() if line]


def command_status(root: Path, head: str, manifest_paths: list[str]) -> dict[str, Any]:
    p = paths(root)
    index = load_index(p["index"])
    if not index:
        return {**command_locate(root), "state": "missing", "sections": {}, "refresh": [sid for sid, _, _ in SECTIONS]}
    report: dict[str, Any] = {}
    refresh: list[str] = []
    for section_id, entry in sorted((index.get("sections") or {}).items()):
        anchors = entry.get("anchors") or []
        sha = entry.get("verified_sha")
        touched = sorted({path for path in manifest_paths for anchor in anchors if anchor_matches(anchor, path)})
        if not sha or not anchors:
            state, drift = "unmapped", []
        else:
            changed = changed_since(root, sha, head)
            if changed is None:
                state, drift = "unknown_base", []
            else:
                drift = sorted({path for path in changed for anchor in anchors if anchor_matches(anchor, path)})
                state = "stale" if drift else "fresh"
        if state != "fresh" or touched:
            refresh.append(section_id)
        report[section_id] = {
            "state": state,
            "verified_sha": sha,
            "drifted_anchors": drift[:50],
            "touched_by_review": touched[:50],
        }
    return {**command_locate(root), "state": "present", "head": head, "sections": report, "refresh": refresh}


def command_stamp(root: Path, section_id: str, sha: str, anchors: list[str]) -> dict[str, Any]:
    p = paths(root)
    index = load_index(p["index"])
    if not index:
        raise SystemExit("error: run `system_map.py init` before stamping a section")
    sections = index.setdefault("sections", {})
    if section_id not in sections:
        raise SystemExit(f"error: unknown section {section_id!r}; expected one of {sorted(sections)}")
    for anchor in anchors:
        if anchor.startswith("/") or ".." in Path(anchor).parts:
            raise SystemExit(f"error: anchor must be repository-relative: {anchor}")
    entry = sections[section_id]
    if anchors:
        entry["anchors"] = sorted(set(anchors))
    entry["verified_sha"] = sha
    entry["verified_at"] = now()
    p["index"].write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"section": section_id, **entry}


def read_manifest(path: Path | None) -> list[str]:
    if not path:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("coverage_manifest", data) if isinstance(data, dict) else data
    return sorted({entry["path"] for entry in entries if isinstance(entry, dict) and entry.get("path")})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("locate", "init", "status", "stamp"):
        command = sub.add_parser(name)
        command.add_argument("--repo", type=Path, required=True)
        if name == "status":
            command.add_argument("--head", required=True)
            command.add_argument("--triage", type=Path, help="Triage Evidence JSON; its manifest marks sections touched by this review")
        if name == "stamp":
            command.add_argument("--section", required=True)
            command.add_argument("--sha", required=True)
            command.add_argument("--anchor", action="append", default=[], help="repository-relative path, directory, or glob")
    args = parser.parse_args()
    root = repo_root(args.repo)
    if args.command == "locate":
        result = command_locate(root)
    elif args.command == "init":
        result = command_init(root)
    elif args.command == "status":
        result = command_status(root, args.head, read_manifest(args.triage))
    else:
        result = command_stamp(root, args.section, args.sha, args.anchor)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
