#!/usr/bin/env python3
"""Collect deterministic, read-only Triage Evidence for Trident.

The collector deliberately returns facts and blocked operations, not a diff or
an interpretation of review findings. It uses only the Python standard library
and the repository's git, rg, and optional gh executables.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "trident-triage-v2"
COMMAND_TIMEOUT = 20


def run(repo: Path, *command: str, timeout: int = COMMAND_TIMEOUT) -> dict[str, Any]:
    """Run one read-only command and serialize failures as evidence."""
    try:
        result = subprocess.run(
            command,
            cwd=repo,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": list(command),
            "status": "blocked",
            "stdout": "",
            "stderr": f"timeout after {timeout}s: {exc}",
            "code": None,
        }
    except OSError as exc:
        return {
            "command": list(command),
            "status": "blocked",
            "stdout": "",
            "stderr": str(exc),
            "code": None,
        }
    return {
        "command": list(command),
        "status": "ok" if result.returncode == 0 else "blocked",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "code": result.returncode,
    }


def output(result: dict[str, Any]) -> str:
    return str(result.get("stdout", ""))


def lines(result: dict[str, Any]) -> list[str]:
    return [line for line in output(result).splitlines() if line]


def classify(path: str, status: str = "") -> str:
    lower = path.lower()
    if status.startswith("D"):
        return "deleted"
    if status.startswith("R"):
        return "renamed"
    if lower.endswith((".lock", "lock.json", "lock.yaml", "lock.yml")):
        return "lockfile"
    if "snapshot" in lower or lower.endswith(".snap"):
        return "snapshot"
    if any(part in lower for part in ("vendor/", "vendored/", "third_party/")):
        return "vendored"
    if lower.endswith((
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
        ".wasm", ".woff", ".woff2", ".ttf", ".mp3", ".mp4",
    )):
        return "binary"
    if any(part in lower for part in ("generated/", "/generated", ".gen.", ".generated.", "dist/")):
        return "generated"
    return "source"


def parse_name_status(text: str) -> list[dict[str, str]]:
    """Parse git's NUL-delimited name-status output, including renames."""
    tokens = text.split("\0")
    result: list[dict[str, str]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            continue
        if status.startswith("R") or status.startswith("C"):
            if index + 1 >= len(tokens):
                break
            old_path, path = tokens[index], tokens[index + 1]
            index += 2
            result.append({"status": status, "path": path, "old_path": old_path})
            continue
        if index >= len(tokens):
            break
        result.append({"status": status, "path": tokens[index]})
        index += 1
    return result


def parse_numstat(text: str) -> dict[str, tuple[int | None, int | None]]:
    stats: dict[str, tuple[int | None, int | None]] = {}
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added, deleted, path = parts[0], parts[1], parts[-1]
        stats[path] = (
            int(added) if added.isdigit() else None,
            int(deleted) if deleted.isdigit() else None,
        )
    return stats


def untracked_stats(repo: Path, path: str) -> tuple[int | None, int | None]:
    """Give text untracked files deterministic additions/deletions counts."""
    try:
        data = (repo / path).read_bytes()
    except OSError:
        return None, None
    if b"\0" in data:
        return None, None
    return len(data.splitlines()), 0


def manifest_from_diff(repo: Path, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    if args.mode in ("pr", "range"):
        name_command = ("git", "diff", "--name-status", "-z", args.base, args.head)
        num_command = ("git", "diff", "--numstat", args.base, args.head)
    elif args.mode == "staged":
        name_command = ("git", "diff", "--cached", "--name-status", "-z")
        num_command = ("git", "diff", "--cached", "--numstat")
    elif args.mode == "all-local":
        name_command = ("git", "diff", "HEAD", "--name-status", "-z")
        num_command = ("git", "diff", "HEAD", "--numstat")
    else:
        name_command = ("git", "diff", "--name-status", "-z")
        num_command = ("git", "diff", "--numstat")

    names = run(repo, *name_command)
    numbers = run(repo, *num_command)
    if names["status"] != "ok":
        errors.append(names)
    if numbers["status"] != "ok":
        errors.append(numbers)
    stats = parse_numstat(output(numbers))
    manifest: list[dict[str, Any]] = []
    known: set[str] = set()
    for item in parse_name_status(output(names)):
        path = item["path"]
        added, deleted = stats.get(path, (None, None))
        entry: dict[str, Any] = {
            "path": path,
            "status": item["status"],
            "class": classify(path, item["status"]),
            "additions": added,
            "deletions": deleted,
        }
        if "old_path" in item:
            entry["old_path"] = item["old_path"]
        manifest.append(entry)
        known.add(path)

    if args.mode in ("unstaged", "all-local"):
        untracked = run(repo, "git", "ls-files", "--others", "--exclude-standard")
        if untracked["status"] != "ok":
            errors.append(untracked)
        for path in lines(untracked):
            if path in known:
                continue
            added, deleted = untracked_stats(repo, path)
            manifest.append({
                "path": path,
                "status": "??",
                "class": classify(path),
                "additions": added,
                "deletions": deleted,
            })
    for item in manifest:
        added, deleted = item["additions"], item["deletions"]
        item["lines_changed"] = added + deleted if isinstance(added, int) and isinstance(deleted, int) else None
    manifest.sort(key=lambda item: (item["path"], item["status"]))
    return manifest, errors


def directory_manifest(repo: Path, directory: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = run(repo, "rg", "--files", "--hidden", "--glob", "!.git/**", directory)
    if result["status"] != "ok":
        return [], [result]
    manifest = [
        {
            "path": path,
            "status": "present",
            "class": classify(path),
            "additions": None,
            "deletions": None,
            "lines_changed": None,
        }
        for path in sorted(lines(result))
    ]
    return manifest, []


def discover_files(repo: Path) -> tuple[list[str], list[dict[str, Any]]]:
    result = run(repo, "rg", "--files", "--hidden", "--glob", "!.git/**")
    if result["status"] != "ok":
        return [], [result]
    return sorted(lines(result)), []


def first_ref(repo: Path, *command: str) -> str | None:
    result = run(repo, *command)
    value = output(result).strip()
    return value or None


def snapshot(repo: Path, args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    current_head = first_ref(repo, "git", "rev-parse", "HEAD")
    branch = first_ref(repo, "git", "branch", "--show-current")
    root = first_ref(repo, "git", "rev-parse", "--show-toplevel")
    git_dir = first_ref(repo, "git", "rev-parse", "--git-dir")
    if args.mode in ("pr", "range"):
        base_sha = first_ref(repo, "git", "rev-parse", args.base)
        head_sha = first_ref(repo, "git", "rev-parse", args.head)
        merge_base = first_ref(repo, "git", "merge-base", args.base, args.head)
    else:
        base_sha = current_head
        head_sha = current_head
        merge_base = current_head
    if not root:
        errors.append(run(repo, "git", "rev-parse", "--show-toplevel"))
    return {
        "repository_root": root,
        "git_dir": git_dir,
        "mode": args.mode,
        "base_ref": args.base,
        "head_ref": args.head or branch,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "merge_base": merge_base,
        "branch": branch,
        "pr_number": int(args.pr) if args.pr and args.pr.isdigit() else args.pr,
    }, errors


def package_metadata(repo: Path, all_files: list[str]) -> dict[str, Any]:
    manifest_names = {
        "package.json", "pyproject.toml", "setup.cfg", "setup.py", "Cargo.toml",
        "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "composer.json",
        "Gemfile", "mix.exs", "Makefile", "justfile",
    }
    manifests = [path for path in all_files if Path(path).name in manifest_names]
    scripts: list[dict[str, str]] = []
    for path in manifests:
        if Path(path).name != "package.json":
            continue
        try:
            data = json.loads((repo / path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        for name, command in sorted((data.get("scripts") or {}).items()):
            if isinstance(command, str):
                scripts.append({"manifest": path, "name": str(name), "command": command})
    for path in all_files:
        if Path(path).name in {"Makefile", "justfile"}:
            scripts.append({"manifest": path, "name": "native-file", "command": "see manifest"})
    workflows = [
        path for path in all_files
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))
    ]
    standards_names = {
        "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CODING_STANDARDS.md",
        ".cursorrules", "README.md",
    }
    standards = [path for path in all_files if Path(path).name in standards_names]
    adr = [path for path in all_files if "/adr/" in f"/{path.lower()}" or Path(path).name.lower().startswith("adr-")]
    specs = []
    for path in all_files:
        lower = path.lower()
        name = Path(path).name.lower()
        is_requirement_path = lower.startswith(("docs/specs/", "specs/", ".scratch/", "docs/requirements/"))
        is_requirement_name = name in {"prd.md", "requirements.md", "specification.md", "acceptance-criteria.md"}
        if (is_requirement_path or is_requirement_name) and path.endswith((".md", ".rst", ".txt", ".yaml", ".yml", ".json")):
            specs.append(path)
    return {
        "manifests": manifests,
        "scripts": scripts,
        "workflows": workflows,
        "standards": standards,
        "adr_candidates": sorted(set(adr)),
        "spec_candidates": sorted(set(specs)),
        "workspaces": sorted({str(Path(path).parent) for path in manifests}),
    }


def issue_references(repo: Path, args: argparse.Namespace) -> list[str]:
    if args.mode in ("pr", "range") and args.base and args.head:
        result = run(repo, "git", "log", "--format=%B", f"{args.base}..{args.head}")
    else:
        result = run(repo, "git", "log", "-1", "--format=%B")
    references = re.findall(r"(?:#[0-9]+|[A-Z][A-Z0-9]+-[0-9]+)", output(result), flags=re.IGNORECASE)
    return sorted(set(references), key=str.lower)


SIGNAL_PATTERNS: dict[str, tuple[str, ...]] = {
    "auth_trust": ("auth", "authorization", "permission", "role", "tenant", "secret", "token", "oauth", "cors", "csrf", "crypto", "url", "upload"),
    "persistence_data": ("schema", "migration", "database", "db", "model", "repository", "transaction", "queue", "retry", "cache", "billing", "counter"),
    "contracts": ("api", "dto", "schema", "event", "webhook", "sdk", "client", "serializer", "route", "graphql", "openapi"),
    "edge_functions": ("function", "handler", "validator", "parser", "mapper"),
    "ui_runtime": ("component", "frontend", "browser", "route", "form", "view", "page", "screen", "react", "vue", "svelte", ".css", ".tsx", ".jsx"),
    "structural_growth": ("refactor", "adapter", "dispatcher", "state", "workflow", "handler", "service", "controller"),
    "deletion_deprecation": ("deprecated", "deprecation", "remove", "delete", "cleanup", "legacy", "feature-flag"),
    "tests": ("test", "spec", "__tests__", "fixture", "snapshot"),
    "generated": ("generated", ".gen.", "dist/", "codegen"),
    "migrations": ("migration", "migrate", "schema"),
}


def signal_evidence(repo: Path, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    signals: dict[str, dict[str, Any]] = {}
    for name, patterns in SIGNAL_PATTERNS.items():
        signals[name] = {"present": False, "paths": [], "sources": []}
    for entry in manifest:
        path = entry["path"]
        haystack = path.lower()
        for name, patterns in SIGNAL_PATTERNS.items():
            if any(pattern in haystack for pattern in patterns):
                signals[name]["present"] = True
                signals[name]["paths"].append(path)
        if entry["class"] in {"binary", "vendored"}:
            continue
        try:
            content = (repo / path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lower = content.lower()
        for name, patterns in SIGNAL_PATTERNS.items():
            if any(re.search(r"(?<![a-z0-9_])" + re.escape(pattern) + r"(?![a-z0-9_])", lower) for pattern in patterns if pattern.isalpha()):
                signals[name]["present"] = True
                signals[name]["sources"].append(path)
    for value in signals.values():
        value["paths"] = sorted(set(value["paths"]))
        value["sources"] = sorted(set(value["sources"]))
    if any(entry["class"] == "source" for entry in manifest) and not any(
        entry["class"] == "tests" or "test" in entry["path"].lower() for entry in manifest
    ):
        signals["tests"]["present"] = False
    return signals


def parse_json_stdout(result: dict[str, Any]) -> dict[str, Any] | None:
    if result["status"] != "ok":
        return None
    try:
        value = json.loads(output(result))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def check_sha(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{7,64}", value):
        return value
    if isinstance(value, dict):
        for key in ("oid", "sha", "headSha", "headRefOid"):
            found = check_sha(value.get(key))
            if found:
                return found
    return None


def github_evidence(repo: Path, args: argparse.Namespace, head_sha: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if args.mode != "pr":
        return {"requested": False, "available": False, "exact_head": False, "checks": []}, []
    blocked: list[dict[str, Any]] = []
    if not shutil.which("gh"):
        missing = {"command": ["gh", "pr", "view", str(args.pr)], "status": "blocked", "stdout": "", "stderr": "gh not found", "code": None}
        return {"requested": True, "available": False, "exact_head": False, "checks": [], "blocked_reason": "gh unavailable"}, [missing]
    result = run(
        repo,
        "gh", "pr", "view", str(args.pr),
        "--json", "number,title,body,baseRefName,headRefName,baseRefOid,headRefOid,state,isDraft,mergeStateStatus,statusCheckRollup,commits",
    )
    if result["status"] != "ok":
        blocked.append(result)
        return {"requested": True, "available": False, "exact_head": False, "checks": [], "blocked_reason": "gh request failed"}, blocked
    data = parse_json_stdout(result) or {}
    pr_head = data.get("headRefOid")
    checks: list[dict[str, Any]] = []
    for check in data.get("statusCheckRollup") or []:
        if not isinstance(check, dict):
            continue
        conclusion = check.get("conclusion") or check.get("state")
        subject_sha = check_sha(check.get("commit")) or check_sha(check.get("sha"))
        checks.append({
            "name": check.get("name") or check.get("context") or check.get("workflowName"),
            "status": check.get("status") or check.get("state"),
            "conclusion": conclusion,
            "subject_sha": subject_sha,
            "exact_head": bool(subject_sha and head_sha and subject_sha == head_sha),
            "url": check.get("detailsUrl") or check.get("targetUrl"),
        })
    exact_head = bool(pr_head and head_sha and pr_head == head_sha)
    exact_success = exact_head and any(
        item["exact_head"] and str(item["conclusion"]).upper() in {"SUCCESS", "SUCCESSFUL", "PASS", "PASSED"}
        for item in checks
    )
    return {
        "requested": True,
        "available": True,
        "number": data.get("number"),
        "state": data.get("state"),
        "is_draft": data.get("isDraft"),
        "base_ref": data.get("baseRefName"),
        "head_ref": data.get("headRefName"),
        "base_sha": data.get("baseRefOid"),
        "head_sha": pr_head,
        "exact_head": exact_head,
        "current_ci_available": exact_success,
        "checks": checks,
        "metadata": {key: data.get(key) for key in ("title", "mergeStateStatus")},
        "issue_reference_candidates": sorted(
            set(re.findall(r"(?:#[0-9]+|[A-Z][A-Z0-9]+-[0-9]+)", str(data.get("body") or ""), flags=re.IGNORECASE)),
            key=str.lower,
        ),
    }, blocked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--mode", choices=("pr", "range", "unstaged", "staged", "all-local", "dir"), required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--pr")
    parser.add_argument("--dir")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    git_check = run(repo, "git", "rev-parse", "--git-dir")
    if git_check["status"] != "ok":
        parser.error("--repo must be inside a git repository")
    if args.mode in ("pr", "range") and (not args.base or not args.head):
        parser.error("--base and --head are required for pr/range")
    if args.mode == "pr" and not args.pr:
        parser.error("--pr is required for pr mode")
    if args.mode == "dir" and not args.dir:
        parser.error("--dir is required for dir mode")

    snapshot_data, snapshot_errors = snapshot(repo, args)
    if args.mode == "dir":
        manifest, manifest_errors = directory_manifest(repo, args.dir)
    else:
        manifest, manifest_errors = manifest_from_diff(repo, args)
    all_files, file_errors = discover_files(repo)
    packages = package_metadata(repo, all_files)
    local_issue_refs = issue_references(repo, args)
    signals = signal_evidence(repo, manifest)
    github, github_errors = github_evidence(repo, args, snapshot_data.get("head_sha"))
    blocked = snapshot_errors + manifest_errors + file_errors + github_errors
    tools = {name: shutil.which(name) for name in ("git", "gh", "rg")}
    ci = {
        "requested": args.mode == "pr",
        "current_head_sha": snapshot_data.get("head_sha"),
        "exact_head": github.get("exact_head", False),
        "current_ci_available": github.get("current_ci_available", False),
        "checks": github.get("checks", []),
        "fallback_required": args.mode == "pr" and not github.get("current_ci_available", False),
    }
    result = {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "repository": {
            "root": snapshot_data.get("repository_root"),
            "git_dir": snapshot_data.get("git_dir"),
            "tools": tools,
        },
        "snapshot": snapshot_data,
        "coverage_manifest": manifest,
        "files_changed": len(manifest),
        "total_additions": sum(item["additions"] or 0 for item in manifest),
        "total_deletions": sum(item["deletions"] or 0 for item in manifest),
        "total_lines_changed": sum(item["lines_changed"] or 0 for item in manifest),
        "top_level_packages": sorted({path.split("/", 1)[0] for path in (item["path"] for item in manifest) if path}),
        "repository_capabilities": packages,
        "issue_reference_candidates": sorted(
            set(local_issue_refs + github.get("issue_reference_candidates", [])),
            key=str.lower,
        ),
        "ci": ci,
        "github": github,
        "signals": signals,
        "evidence": {
            "availability": {
                "git": tools["git"] is not None,
                "rg": tools["rg"] is not None,
                "gh": tools["gh"] is not None if args.mode == "pr" else None,
            },
            "blocked_commands": blocked,
            "complete": not blocked,
        },
        "pr_state": {
            "reviewable": bool(snapshot_data.get("head_sha")),
            "github_metadata_covered": bool(github.get("available")),
            "local_fallback": args.mode == "pr" and not github.get("available", False),
            "head_sha": snapshot_data.get("head_sha"),
            "pr_head_sha": github.get("head_sha"),
            "head_matches": github.get("exact_head", False),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
