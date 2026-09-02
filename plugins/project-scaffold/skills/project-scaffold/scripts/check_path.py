#!/usr/bin/env python3
"""Check that a file path obeys the project structure contract in CLAUDE.md.

The map in CLAUDE.md says where every kind of artifact lives. This script turns
the mechanical half of that map — which folders exist, how records are named,
where IDs come from — into something checkable, so those decisions never rest on
recall. The judgement half (which of three plausible homes is right) stays with
whoever is writing the file; `references/placement.md` in this skill works
through it.

Modes:
    check <path> [<path>...]   validate proposed paths (default)
    --audit [--root DIR]       walk an existing repo and check every file
    --next-id PREFIX           print the next free ID for a register
    --hook                     read a Claude Code PreToolUse event on stdin

Exit codes: 0 clean or warnings only, 1 at least one error, 2 hook block.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

# Windows consoles default to cp1252. Findings are meant to be ASCII, but a path
# or filename echoed back may not be, and a checker that dies on an unusual
# character is worse than one that prints a question mark.
for _stream in (sys.stdout, sys.stderr):
    _reconfigure = getattr(_stream, "reconfigure", None)
    if _reconfigure is not None:
        try:
            _reconfigure(encoding="utf-8", errors="replace")
        except ValueError:  # already detached, or redirected to a raw pipe
            pass

# --------------------------------------------------------------------------
# The map, transcribed from CLAUDE.md. `dirs` are the folders the map names at
# the second level; `files` are documents the map names directly. A top level
# whose `dirs` is None takes any path below it (archive/ mirrors originals,
# .claude/ is tool configuration rather than a project artifact).
# --------------------------------------------------------------------------
MAP = {
    "project": {"dirs": ["charter", "scope", "stakeholders", "glossary", "decisions"]},
    "management": {"dirs": ["wbs", "schedule", "resources", "estimates", "risks",
                            "issues", "changes", "reports"]},
    "research": {"dirs": ["studies", "experiments", "prototypes", "benchmarks", "references"]},
    "requirements": {"dirs": ["business", "system", "software", "interfaces",
                              "non-functional", "traceability"]},
    "architecture": {"dirs": ["context", "system", "software", "data", "infrastructure",
                              "security", "interfaces", "diagrams", "adr"]},
    "design": {"dirs": ["components", "database", "interfaces", "algorithms", "specifications"]},
    "src": {"dirs": ["apps", "services", "libraries", "tools"]},
    "tests": {"dirs": ["unit", "integration", "system", "performance", "security",
                       "acceptance", "evidence"]},
    "data": {"dirs": ["schemas", "metadata", "samples", "synthetic", "manifests"]},
    "resources": {"dirs": ["configuration", "templates", "models", "third-party"]},
    "infra": {"dirs": ["docker", "terraform", "kubernetes", "environments"]},
    "ops": {"dirs": ["deployment", "monitoring", "runbooks", "backup", "disaster-recovery"]},
    "quality": {"dirs": ["metrics"],
                "files": ["coding-standards.md", "review-checklist.md",
                          "definition-of-done.md"]},
    "security": {"dirs": ["assessments", "incidents"],
                 "files": ["policy.md", "secure-development.md"]},
    "compliance": {"dirs": ["audits"],
                   "files": ["applicability.md", "control-matrix.md"]},
    "external": {"dirs": ["customer", "suppliers", "standards"]},
    "docs": {"dirs": ["manuals", "onboarding", "training", "presentations"]},
    "archive": {"dirs": None},
    ".claude": {"dirs": None},
}

ROOT_FILES = {
    "CLAUDE.md", "CLAUDE.local.md", "README.md", "CHANGELOG.md", "LICENSE",
    ".gitignore", ".editorconfig", ".gitattributes", "pyproject.toml", "uv.lock",
    "poetry.lock", "Directory.Build.props", "Directory.Packages.props",
    "global.json", "NuGet.config", ".dockerignore", "Makefile", "justfile",
}
ROOT_FILE_PATTERNS = [r".*\.sln$", r"\.gitlab-ci\.yml$"]

# Tool-owned trees. CI definitions go where the tool requires and are described
# in ops/deployment/, so they are legal without being in the artifact map.
TOOL_DIRS = {".git", ".github", ".gitlab", ".vscode", ".idea", ".venv", "venv",
             "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
             ".ruff_cache", "bin", "obj", ".vs"}

REGISTERS = {
    "requirements/business": "REQ-BUS",
    "requirements/system": "REQ-SYS",
    "requirements/software": "REQ-SW",
    "requirements/interfaces": "REQ-IF",
    "requirements/non-functional": "REQ-NF",
    "architecture/adr": "ADR",
    "project/decisions": "DEC",
    "management/risks": "RISK",
    "management/issues": "ISS",
    "management/changes": "CR",
}

# Records here are ordered by when they happened, so the date leads the name.
DATED_DIRS = ["management/reports", "research/experiments", "docs/presentations"]

# kebab-case is a documentation rule. Code trees follow their language instead:
# a Python package is snake_case and a .NET project is PascalCase, and forcing
# kebab there would break the build.
KEBAB_TREES = ["project", "management", "requirements", "architecture", "design",
               "ops", "quality", "security", "compliance", "docs"]
KEBAB_EXEMPT = ["research/experiments", "research/prototypes", "architecture/diagrams",
                "external", "archive"]

READ_ONLY = ["external", "archive"]

SECRET_NAMES = [r"^\.env$", r"^\.env\.(?!example|template|sample).+", r".*\.pem$",
                r".*\.key$", r".*\.pfx$", r".*\.p12$", r"^id_rsa$", r"^id_ed25519$",
                r"^credentials(\.json|\.yml|\.yaml)?$", r"^\.npmrc$", r"^\.pypirc$"]

ID_RE = re.compile(r"^([A-Z]+(?:-[A-Z]+)?)-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")


def to_kebab(name):
    """Suggest a kebab-case name, splitting camelCase rather than flattening it."""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", stem)
    stem = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "-", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "-", stem).strip("-").lower()
    stem = re.sub(r"-{2,}", "-", stem)
    return stem + ("." + ext.lower() if ext else "")


class Finding:
    def __init__(self, level, path, message, fix=None):
        self.level = level          # "error" or "warn"
        self.path = path
        self.message = message
        self.fix = fix

    def render(self):
        tag = "ERROR" if self.level == "error" else "warn "
        out = "  [" + tag + "] " + self.path + "\n           " + self.message
        if self.fix:
            out += "\n           -> " + self.fix
        return out


def find_root(start):
    """Walk up from `start` to the directory holding CLAUDE.md."""
    here = Path(start).resolve()
    for candidate in [here] + list(here.parents):
        if (candidate / "CLAUDE.md").is_file():
            return candidate
    return None


def relative_parts(path, root):
    """Return the repo-relative POSIX parts of `path`, or None if outside root."""
    p = Path(str(path).replace("\\", "/"))
    if root and p.is_absolute():
        try:
            p = p.resolve().relative_to(root)
        except ValueError:
            return None
    elif p.is_absolute():
        return None
    return PurePosixPath(p.as_posix()).parts


def under(parts, prefixes):
    joined = "/".join(parts)
    return any(joined == pre or joined.startswith(pre + "/") for pre in prefixes)


def check(path, root=None, existing=None):
    """Validate one repo-relative or absolute path. Returns a list of Findings."""
    parts = relative_parts(path, root)
    display = str(path).replace("\\", "/")
    out = []
    if parts is None:
        return [Finding("warn", display, "outside the project root; not checked here.")]
    parts = tuple(p for p in parts if p not in (".", ""))
    if not parts:
        return out
    name = parts[-1]
    top = parts[0]

    # --- secrets ---------------------------------------------------------
    for pattern in SECRET_NAMES:
        if re.match(pattern, name):
            out.append(Finding(
                "error", display,
                "this looks like a secret, and rule 6 keeps secrets out of the repo "
                "entirely.",
                "store the value in the secret manager and reference it by name "
                "(${DB_PASSWORD}); commit only a redacted template at "
                "resources/configuration/.env.example.",
            ))
            return out

    if top in TOOL_DIRS:
        return out

    # --- root files ------------------------------------------------------
    if len(parts) == 1:
        if name in ROOT_FILES or any(re.match(p, name) for p in ROOT_FILE_PATTERNS):
            return out
        out.append(Finding(
            "error", display,
            "the root holds only the workspace files the map names; a loose file here "
            "has no home and no owner.",
            "move it under the top-level folder the map gives it, or add it to the "
            "root list in CLAUDE.md if it really is a workspace file.",
        ))
        return out

    # --- top level -------------------------------------------------------
    if top not in MAP:
        out.append(Finding(
            "error", display,
            "'" + top + "/' is not a top-level folder in the map, and rule 1 forbids "
            "creating new ones: a new top level means an artifact class nobody has "
            "agreed on.",
            "pick from: " + ", ".join(sorted(MAP)) + ". If none fits, ask rather "
            "than guess.",
        ))
        return out

    spec = MAP[top]
    if spec["dirs"] is None:
        return out

    # --- second level ----------------------------------------------------
    second = parts[1]
    is_leaf = len(parts) == 2
    if is_leaf and "." in second:
        if second in spec.get("files", []):
            return out
        if spec.get("files"):
            out.append(Finding(
                "warn", display,
                "the map names " + ", ".join(spec["files"]) + " directly under " + top
                + "/; anything else here is unplaced.",
                "confirm this belongs at the top of " + top + "/ rather than in "
                + ", ".join(spec["dirs"]) + "/.",
            ))
        else:
            out.append(Finding(
                "warn", display,
                top + "/ is organised into subfolders, so a file sitting directly in "
                "it belongs to none of them.",
                "move it into one of: " + ", ".join(spec["dirs"]) + ".",
            ))
        return out

    if second not in spec["dirs"]:
        out.append(Finding(
            "error", display,
            "'" + second + "/' is not one of the folders the map defines under "
            + top + "/.",
            "use one of: " + ", ".join(spec["dirs"]) + ". Sibling concepts that look "
            "alike are resolved by the look-alike table in CLAUDE.md.",
        ))
        return out

    two = top + "/" + second

    # --- read-only trees -------------------------------------------------
    if under(parts, READ_ONLY):
        where = parts[0]
        out.append(Finding(
            "warn", display,
            where + "/ is read-only: things are moved in, never edited there.",
            "if this is new work, write it in its lifecycle folder instead. If you "
            "are superseding a document, move the old file here unchanged and set "
            "status: superseded on it.",
        ))

    # --- register records ------------------------------------------------
    if two in REGISTERS:
        prefix = REGISTERS[two]
        if name != "index.md":
            m = ID_RE.match(name)
            if not m:
                out.append(Finding(
                    "error", display,
                    "records in " + two + "/ are named " + prefix
                    + "-nnnn-kebab-title.md; the ID in the filename is how every "
                    "cross-reference and the RTM find this document.",
                    "rename it, taking the next free ID from " + two + "/index.md "
                    "(check_path.py --next-id " + prefix + ").",
                ))
            elif m.group(1) != prefix:
                out.append(Finding(
                    "error", display,
                    "prefix '" + m.group(1) + "' does not belong in " + two
                    + "/, which holds " + prefix + " records.",
                    "either rename with the " + prefix + " prefix, or file it in the "
                    "register that owns " + m.group(1) + ".",
                ))
            elif existing is not None:
                clash = existing.get(prefix + "-" + m.group(2))
                if clash and clash != name:
                    out.append(Finding(
                        "error", display,
                        "ID " + prefix + "-" + m.group(2) + " is already taken by "
                        + clash + "; IDs are never reused.",
                        "take the next free ID: check_path.py --next-id " + prefix + ".",
                    ))

    # --- dated records ---------------------------------------------------
    if under(parts, DATED_DIRS) and not DATE_RE.match(parts[2] if len(parts) > 2 else name):
        target = parts[2] if len(parts) > 2 else name
        out.append(Finding(
            "warn", display,
            "records under " + two + "/ are read in time order, so the name starts "
            "with the date: YYYY-MM-DD-...",
            "rename '" + target + "' with a YYYY-MM-DD- prefix.",
        ))

    # --- naming ----------------------------------------------------------
    if top in KEBAB_TREES and not under(parts, KEBAB_EXEMPT):
        for segment in parts[2:]:
            base = segment
            if base == name and "." in base:
                base = base.rsplit(".", 1)[0]
            if two in REGISTERS and ID_RE.match(name) and segment == name:
                continue
            if DATE_RE.match(base):
                base = base[11:]
            if base and not KEBAB_RE.match(base):
                out.append(Finding(
                    "warn", display,
                    "'" + segment + "' is not kebab-case ASCII; document paths are "
                    "typed into links by hand and appear in URLs.",
                    "rename to " + to_kebab(segment) + ".",
                ))
                break

    # --- tests mirror src ------------------------------------------------
    if top == "tests" and second != "evidence" and len(parts) > 2 and root:
        unit = parts[2]
        src_root = root / "src"
        if src_root.is_dir():
            known = {d.name for kind in src_root.iterdir() if kind.is_dir()
                     for d in kind.iterdir() if d.is_dir()}
            if known and unit not in known:
                out.append(Finding(
                    "warn", display,
                    "'" + unit + "' does not match any unit under src/; tests mirror "
                    "the source path so the RTM can line them up.",
                    "expected one of: " + ", ".join(sorted(known)) + ".",
                ))

    return out


def scan_ids(root, prefix=None):
    """Map every allocated ID to its filename, from filenames and index tables."""
    found = {}
    for two, pre in REGISTERS.items():
        if prefix and pre != prefix:
            continue
        folder = root / two
        if not folder.is_dir():
            continue
        for f in folder.glob("*.md"):
            m = ID_RE.match(f.name)
            if m and m.group(1) == pre:
                found[pre + "-" + m.group(2)] = f.name
        index = folder / "index.md"
        if index.is_file():
            for row in re.findall(r"^\|\s*`?(" + re.escape(pre) + r"-\d{4})`?\s*\|",
                                  index.read_text(encoding="utf-8", errors="replace"),
                                  re.MULTILINE):
                found.setdefault(row, "(listed in index.md)")
    return found


def next_id(root, prefix):
    if prefix not in REGISTERS.values():
        return None, "unknown prefix. Known: " + ", ".join(sorted(set(REGISTERS.values())))
    used = scan_ids(root, prefix)
    highest = max((int(k.rsplit("-", 1)[1]) for k in used), default=0)
    return prefix + "-" + str(highest + 1).zfill(4), None


def report(findings, quiet=False):
    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]
    if not findings:
        if not quiet:
            print("OK - every path matches the map in CLAUDE.md.")
        return 0
    for f in errors + warns:
        print(f.render())
    print("\n" + str(len(errors)) + " error(s), " + str(len(warns)) + " warning(s).")
    if errors:
        print("Errors are placements the map does not allow. The look-alike table in "
              "CLAUDE.md resolves the near-misses; ask rather than guess.")
    return 1 if errors else 0


def run_hook():
    """PreToolUse hook: block a write whose path the map does not allow.

    Any internal failure exits 0. A checker that crashes must not be able to
    stop legitimate work.
    """
    try:
        event = json.load(sys.stdin)
        tool_input = event.get("tool_input") or {}
        target = (tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if not target:
            return 0
        root = find_root(Path(target).parent if Path(target).is_absolute() else Path.cwd())
        if root is None:
            return 0
        findings = check(target, root, scan_ids(root))
        errors = [f for f in findings if f.level == "error"]
        if not errors:
            return 0
        lines = ["This path is not allowed by the structure contract in CLAUDE.md:"]
        for f in errors:
            lines.append("  " + f.message)
            if f.fix:
                lines.append("  -> " + f.fix)
        lines.append("Place the file where the map puts it, then write it again.")
        print("\n".join(lines), file=sys.stderr)
        return 2
    except Exception:
        return 0


def main(argv):
    p = argparse.ArgumentParser(description="Check paths against the structure contract.")
    p.add_argument("paths", nargs="*", help="paths to validate")
    p.add_argument("--root", default=".", help="project root (default: search for CLAUDE.md)")
    p.add_argument("--audit", action="store_true", help="check every file in the repo")
    p.add_argument("--next-id", metavar="PREFIX", help="print the next free ID for a register")
    p.add_argument("--hook", action="store_true", help="run as a PreToolUse hook")
    p.add_argument("--quiet", action="store_true", help="print nothing when clean")
    a = p.parse_args(argv)

    if a.hook:
        return run_hook()

    root = find_root(a.root) or Path(a.root).resolve()

    if a.next_id:
        value, err = next_id(root, a.next_id)
        if err:
            print("error: " + err, file=sys.stderr)
            return 1
        print(value)
        return 0

    if not (root / "CLAUDE.md").is_file() and (a.audit or not a.paths):
        print("error: no CLAUDE.md found from " + str(root)
              + " — is this a project built from the contract?", file=sys.stderr)
        return 1

    existing = scan_ids(root)

    if a.audit:
        findings = []
        for f in sorted(root.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(root)
            if set(rel.parts) & TOOL_DIRS:
                continue
            findings += check(rel, root, existing)
        return report(findings, a.quiet)

    if not a.paths:
        p.error("give one or more paths, or use --audit")

    findings = []
    for path in a.paths:
        findings += check(path, root, existing)
    return report(findings, a.quiet)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
