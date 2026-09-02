#!/usr/bin/env python3
"""Create a new project root governed by the structure contract in assets/CLAUDE.md.

Writes the contract files (CLAUDE.md, .claude/rules/*, README, CHANGELOG,
.gitignore, .editorconfig, build file) and the ID registers, and nothing else.
Empty directories are deliberately not created: the map inside CLAUDE.md is the
contract, and a directory earns its existence when its first artifact lands.

Run with --dry-run first to see the file list without touching the disk.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# --------------------------------------------------------------------------
# Stack profiles. Each supplies the Commands block for CLAUDE.md and the
# language-specific answers that .claude/rules/code.md asks for.
# --------------------------------------------------------------------------
STACKS = {
    "python": {
        "build_file": "pyproject.toml",
        "commands": (
            "uv sync                          # install / sync environment\n"
            "pytest tests/unit                # fast tests — run before every commit\n"
            "pytest                           # full suite\n"
            "ruff check . && ruff format .    # lint + format\n"
            "mypy src                         # type check"
        ),
        "formatter": "ruff",
        "typecheck": "mypy --strict",
        "doc_style": "Google-style docstrings",
        "test_tag": '`@pytest.mark.req("REQ-SW-0012")`',
        "workspace_link": "uv workspace",
        "log_lib": "structlog",
        "config_mech": "pydantic-settings reading the environment",
        "drop_bullet": ".NET:",
    },
    "dotnet": {
        "build_file": "{solution}.sln",
        "commands": (
            "dotnet build                     # build\n"
            "dotnet test tests/unit           # fast tests — run before every commit\n"
            "dotnet test                      # full suite\n"
            "dotnet format                    # format"
        ),
        "formatter": "dotnet format + analyzers",
        "typecheck": "nullable enabled, warnings as errors",
        "doc_style": "XML doc comments",
        "test_tag": '`[Trait("REQ", "REQ-SW-0012")]`',
        "workspace_link": "projects referenced from the solution",
        "log_lib": "Microsoft.Extensions.Logging",
        "config_mech": "IConfiguration bound to typed options",
        "drop_bullet": "Python:",
    },
    "other": {
        "build_file": None,          # --build-file required
        "commands": None,            # --commands required
        "formatter": None,
        "typecheck": None,
        "doc_style": None,
        "test_tag": None,
        "workspace_link": None,
        "log_lib": None,
        "config_mech": None,
        "drop_bullet": "both",
    },
}

GITIGNORE_COMMON = """\
# Secrets. Reference them by name (${DB_PASSWORD}); keep the template at
# resources/configuration/.env.example.
.env
.env.local
.env.*.local
*.pem
*.key
*.pfx
*.p12
secrets/

# Personal IDE and OS settings
.vscode/
.idea/
.DS_Store
Thumbs.db

# Local Claude overrides
CLAUDE.local.md
.claude/settings.local.json

# Everyday test output. Only release sign-off artifacts are committed, under
# tests/evidence/<version>/.
.coverage
coverage.*
htmlcov/
test-results/
TestResults/
tests/**/output/
!tests/evidence/
!tests/evidence/**

# Bulk data. The repo holds definitions and small samples only (< __DATA_CAP__).
# Record where the full copy lives, plus checksums, in data/manifests/.
data/**/*.parquet
data/**/*.avro
data/**/*.db
data/**/*.sqlite*
data/**/*.zip
data/**/*.tar.gz

# Diagram scratch files. Sources and their exports in architecture/diagrams/
# are committed; editor lock files are not.
*.drawio.bkp
.~lock.*
"""

GITIGNORE_STACK = {
    "python": """
# Python
__pycache__/
*.py[cod]
.venv/
venv/
build/
dist/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
""",
    "dotnet": """
# .NET
bin/
obj/
.vs/
*.user
*.suo
artifacts/
""",
    "other": "",
}

EDITORCONFIG = """\
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

# Two trailing spaces are a hard line break in Markdown, so they are kept.
[*.{md,markdown}]
indent_size = 2
trim_trailing_whitespace = false

[*.{yml,yaml,json,jsonc,toml}]
indent_size = 2

[*.{tf,tfvars,hcl}]
indent_size = 2

[*.{cs,csproj,props,targets}]
indent_size = 4

[*.sln]
indent_style = tab
end_of_line = crlf

[Makefile]
indent_style = tab
"""

SETTINGS_BASE = {
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "permissions": {
        "deny": [
            "Read(./.env)",
            "Read(./.env.local)",
            "Read(./**/*.pem)",
            "Read(./**/*.key)",
            "Read(./**/*.pfx)",
            "Read(./**/*.p12)",
        ]
    },
}

HOOK_BLOCK = {
    "PreToolUse": [
        {
            "matcher": "Write|Edit|NotebookEdit",
            "hooks": [
                {
                    "type": "command",
                    "command": 'python "$CLAUDE_PROJECT_DIR/.claude/scripts/check_path.py" --hook',
                }
            ],
        }
    ]
}

# Registers are seeded so ID allocation and traceability work from the very
# first document. Each index.md is that register's ledger; next ID = max + 1.
REGISTERS = [
    ("requirements/business", "REQ-BUS", "Business requirements"),
    ("requirements/system", "REQ-SYS", "System requirements"),
    ("requirements/software", "REQ-SW", "Software requirements"),
    ("requirements/interfaces", "REQ-IF", "Interface requirements"),
    ("requirements/non-functional", "REQ-NF", "Non-functional requirements"),
    ("architecture/adr", "ADR", "Architecture decision records"),
    ("project/decisions", "DEC", "Business, scope and process decisions"),
    ("management/risks", "RISK", "Risk register"),
    ("management/issues", "ISS", "Project issue register"),
    ("management/changes", "CR", "Change requests"),
]


def slugify(text):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", s) or "project"


def sub_all(text, pairs):
    for pattern, value in pairs:
        text = re.sub(pattern, lambda _m, v=value: v, text)
    return text


def render_claude_md(a, profile):
    text = (ASSETS / "CLAUDE.md").read_text(encoding="utf-8")

    # The setup comment is instructions for whoever fills the template in; it
    # has served its purpose by the time the file lands in a project.
    text = re.sub(r"\A<!--.*?-->\s*\n", "", text, flags=re.DOTALL)

    # Keep only the command block for this stack. Claude reads this instead of
    # guessing how to build and test, so a stale or two-stack block is worse
    # than none at all.
    commands = a.commands or profile["commands"]
    text = re.sub(
        r"```bash\n.*?\n```",
        lambda _m: "```bash\n" + commands.rstrip() + "\n```",
        text,
        count=1,
        flags=re.DOTALL,
    )

    return sub_all(
        text,
        [
            (r"\{\{PROJECT_NAME\}\}", a.name),
            (r"\{\{One paragraph[^}]*\}\}", a.summary),
            (r"\{\{languages, frameworks[^}]*\}\}", a.stack_desc),
            (r"\{\{discovery \| requirements[^}]*\}\}", a.phase),
            (r"\{\{URL[^}]*\}\}", a.tracker),
            (r"\{\{secret manager\}\}", a.secrets),
            (r"\{\{pyproject\.toml \| Project\.sln\}\}", a.build_file),
            (r"\{\{project-name\}\}", a.slug),
            (r"\{\{1 MB\}\}", a.data_cap),
            (r"\{\{ML/trained\}\}", a.model_kind),
            (r"\{\{DMS\}\}", a.dms),
            (r"\{\{env\}\}", "<env>"),
            (r"\{\{version\}\}", "<version>"),
            (r"\{\{ID\}\}", "<ID>"),
        ],
    )


def render_documents_rules(a):
    text = (ASSETS / "rules" / "documents.md").read_text(encoding="utf-8")
    text = text.replace("created: 2026-09-02", "created: " + a.today)
    text = text.replace("updated: 2026-09-02", "updated: " + a.today)
    return sub_all(
        text,
        [
            (r"\{\{name\}\}", a.owner),
            (r"\{\{must \| should \| could\}\}", "must | should | could"),
            (r"\{\{type\}\}", "<type>"),
            (r"\{\{topic\}\}", "<topic>"),
        ],
    )


def render_code_rules(a, profile):
    text = (ASSETS / "rules" / "code.md").read_text(encoding="utf-8")

    # Drop the layout bullet for the language this project does not use. A rule
    # about a stack that is not present is noise Claude filters on every read.
    drop = profile["drop_bullet"]
    keep = []
    for line in text.split("\n"):
        stripped = line.lstrip("- ")
        if drop == "both" and (stripped.startswith("Python:") or stripped.startswith(".NET:")):
            continue
        if drop != "both" and stripped.startswith(drop):
            continue
        keep.append(line)
    text = "\n".join(keep)

    return sub_all(
        text,
        [
            (r"\{\{apps\|services\|libraries\|tools\}\}", "<apps|services|libraries|tools>"),
            (r"\{\{package\}\}", "<package>"),
            (r"\{\{Company\.Project\.Name\}\}", a.namespace),
            (r"\{\{Project\}\}", a.solution),
            (r"\{\{uv workspace \| editable installs\}\}", a.workspace_link),
            (r"\{\{ruff \| dotnet format \+ analyzers\}\}", a.formatter),
            (r"\{\{mypy --strict \| nullable enabled, warnings as errors\}\}", a.typecheck),
            (r"\{\{Google-style docstrings \| XML doc comments\}\}", a.doc_style),
            (r"\{\{`@pytest[^}]*\}\}", a.test_tag),
            (r"\{\{library\}\}", a.log_lib),
            (r"\{\{mechanism\}\}", a.config_mech),
            (r"\{\{secret manager\}\}", a.secrets),
            (r"\{\{name\}\}", "<name>"),
            (r"\{\{kind\}\}", "<kind>"),
            (r"\{\{level\}\}", "<level>"),
            (r"\{\{version\}\}", "<version>"),
        ],
    )


def render_readme(a):
    first_command = a.commands.splitlines()[0] if a.commands else ""
    return (
        "# " + a.name + "\n\n"
        + a.summary + "\n\n"
        "- **Stack:** " + a.stack_desc + "\n"
        "- **Phase:** " + a.phase + "\n"
        "- **Issue tracker:** " + a.tracker + "\n\n"
        "## Getting started\n\n"
        "```bash\n" + first_command + "\n```\n\n"
        "## Where things live\n\n"
        "`CLAUDE.md` holds the directory map, the look-alike table that resolves the\n"
        "folders people confuse, the ID scheme, and the change workflow. It is the\n"
        "contract for this repository — read it before adding a file, and put every\n"
        "new artifact at the path the map gives it.\n\n"
        "Detailed conventions sit in `.claude/rules/documents.md` (every lifecycle\n"
        "document) and `.claude/rules/code.md` (`src/` and `tests/`).\n\n"
        "Directories are created when their first artifact lands, so the tree on disk\n"
        "is smaller than the map. That is intended: an empty folder claims work that\n"
        "does not exist yet.\n\n"
        "## Requirements and traceability\n\n"
        "Requirements live under `requirements/`, one per `##` heading, each carrying\n"
        "its own ID. `requirements/traceability/rtm.md` links every requirement to the\n"
        "decision, design, code and test that satisfy it, and is updated in the same\n"
        "change as whatever it points at.\n"
    )


def render_changelog(a):
    return (
        "# Changelog\n\n"
        "All notable changes to this project are recorded here, following\n"
        "[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and\n"
        "[Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
        "Entries cite the IDs behind the change (`REQ-*`, `ADR-*`, `CR-*`) so a reader\n"
        "can get from a released behaviour back to the requirement that asked for it.\n\n"
        "## [Unreleased]\n\n"
        "### Added\n\n"
        "- Repository initialised from the project structure contract (" + a.today + ").\n"
    )


def render_index(prefix, title, a):
    return (
        "---\n"
        "title: " + title + " register\n"
        "status: draft\n"
        "owner: " + a.owner + "\n"
        "created: " + a.today + "\n"
        "updated: " + a.today + "\n"
        "---\n\n"
        "# " + title + " register\n\n"
        "Every `" + prefix + "-nnnn` record in this folder has a row here. IDs are four\n"
        "digits, zero-padded, never reused and never renumbered — the next ID is the\n"
        "highest in this table plus one. Add the row in the same change that adds the\n"
        "file, or the next author allocates an ID that is already taken.\n\n"
        "Files are named `" + prefix + "-nnnn-kebab-title.md`.\n\n"
        "| ID | Title | Status | Owner | Updated |\n"
        "|---|---|---|---|---|\n"
    )


def render_rtm(a):
    return (
        "---\n"
        "title: Requirements traceability matrix\n"
        "status: draft\n"
        "owner: " + a.owner + "\n"
        "created: " + a.today + "\n"
        "updated: " + a.today + "\n"
        "---\n\n"
        "# Requirements traceability matrix\n\n"
        "One row per requirement, from `REQ-BUS` down through `REQ-SYS`, `REQ-SW`,\n"
        "`REQ-IF` and `REQ-NF`. This table is what makes it possible to answer \"is this\n"
        "requirement actually built, and actually verified\" without reading the whole\n"
        "repository, so it is updated in the same change as any requirement, decision,\n"
        "design document, source path or test it names — never as a later clean-up pass.\n\n"
        "| REQ | Parent | ADR / design doc | Source path | Test path | Evidence | Status |\n"
        "|---|---|---|---|---|---|---|\n"
    )


def render_pyproject(a):
    desc = a.summary.splitlines()[0][:180] if a.summary else a.name
    desc = desc.replace('"', "'")
    return (
        "[project]\n"
        'name = "' + a.slug + '"\n'
        'version = "0.1.0"\n'
        'description = "' + desc + '"\n'
        'requires-python = ">=' + a.python_version + '"\n'
        "dependencies = []\n\n"
        "# Units live at src/<kind>/<name>/, each with its own pyproject.toml. This root\n"
        "# file carries only workspace and tool configuration — see .claude/rules/code.md.\n\n"
        "[tool.ruff]\n"
        "line-length = 100\n"
        'src = ["src"]\n\n'
        "[tool.ruff.lint]\n"
        'select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]\n\n'
        "[tool.mypy]\n"
        "strict = true\n"
        'python_version = "' + a.python_version + '"\n\n'
        "[tool.pytest.ini_options]\n"
        'testpaths = ["tests"]\n'
        "markers = [\n"
        "    \"req(id): the requirement this test verifies, e.g. req('REQ-SW-0012')\",\n"
        "]\n"
    )


def render_sln():
    # A minimal solution file. Projects are added with `dotnet sln add` as each
    # unit is created under src/<kind>/ or tests/<level>/.
    return (
        "﻿\r\n"
        "Microsoft Visual Studio Solution File, Format Version 12.00\r\n"
        "# Visual Studio Version 17\r\n"
        "Global\r\n"
        "\tGlobalSection(SolutionProperties) = preSolution\r\n"
        "\t\tHideSolutionNode = FALSE\r\n"
        "\tEndGlobalSection\r\n"
        "EndGlobal\r\n"
    )


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Scaffold a project root from the structure contract."
    )
    p.add_argument("--path", required=True, help="directory to create the project in")
    p.add_argument("--name", required=True, help='human title, e.g. "Falcon Telemetry"')
    p.add_argument("--summary", required=True, help="one paragraph: what it does, for whom")
    p.add_argument("--stack", required=True, choices=sorted(STACKS), help="python | dotnet | other")
    p.add_argument("--stack-desc", required=True, help='e.g. "Python 3.12, FastAPI, PostgreSQL 16"')
    p.add_argument("--today", required=True, help="today's date, YYYY-MM-DD")
    p.add_argument("--owner", default="TBD", help="default document owner")
    p.add_argument(
        "--phase",
        default="discovery",
        choices=["discovery", "requirements", "design", "build", "verification", "operations"],
    )
    p.add_argument("--tracker", default="management/issues/", help="issue tracker URL or path")
    p.add_argument("--secrets", default="the environment", help="secret manager name")
    p.add_argument("--data-cap", default="1 MB", help="largest committed sample dataset")
    p.add_argument("--model-kind", default="ML/trained", help="what resources/models/ holds")
    p.add_argument("--dms", default="the contract system", help="where contracts live")
    p.add_argument("--slug", default=None, help="folder-safe name (default: from --name)")
    p.add_argument("--python-version", default="3.12")
    p.add_argument("--solution", default=None, help=".NET solution name, e.g. Contoso.Falcon")
    p.add_argument("--namespace", default=None, help=".NET project naming root")
    p.add_argument("--license", default="none", help="MIT | Apache-2.0 | proprietary | none")
    p.add_argument("--build-file", default=None, help="root build file name (required for other)")
    p.add_argument("--commands", default=None, help="Commands block body (required for other)")
    p.add_argument("--formatter", default=None)
    p.add_argument("--typecheck", default=None)
    p.add_argument("--doc-style", default=None)
    p.add_argument("--test-tag", default=None)
    p.add_argument("--workspace-link", default=None)
    p.add_argument("--log-lib", default=None)
    p.add_argument("--config-mech", default=None)
    p.add_argument(
        "--enforce-hook",
        action="store_true",
        help="also install a PreToolUse hook that blocks writes to illegal paths",
    )
    p.add_argument("--force", action="store_true", help="write into a non-empty directory")
    p.add_argument("--dry-run", action="store_true", help="list the files without writing")
    a = p.parse_args(argv)

    profile = STACKS[a.stack]
    a.slug = a.slug or slugify(a.name)
    a.solution = a.solution or "".join(w.capitalize() for w in a.slug.split("-"))
    a.namespace = a.namespace or (a.solution + ".Name")

    # Fall back to the stack profile for anything not given explicitly.
    for key in (
        "formatter", "typecheck", "doc_style", "test_tag",
        "workspace_link", "log_lib", "config_mech", "commands",
    ):
        if getattr(a, key) is None:
            setattr(a, key, profile[key])
    if a.build_file is None:
        bf = profile["build_file"]
        a.build_file = bf.format(solution=a.solution) if bf else None

    missing = [
        "--" + k.replace("_", "-")
        for k in ("build_file", "commands", "formatter", "typecheck",
                  "doc_style", "test_tag", "workspace_link", "log_lib", "config_mech")
        if not getattr(a, k)
    ]
    if missing:
        p.error(
            "--stack other needs these answers, which the template asks for and "
            "cannot invent: " + ", ".join(missing)
        )
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.today):
        p.error("--today must be YYYY-MM-DD")
    return a


def main(argv):
    a = parse_args(argv)
    profile = STACKS[a.stack]
    root = Path(a.path).expanduser().resolve()

    if root.exists() and any(root.iterdir()) and not a.force:
        print("error: " + str(root) + " exists and is not empty (use --force)", file=sys.stderr)
        return 1

    files = {
        "CLAUDE.md": render_claude_md(a, profile),
        ".claude/rules/documents.md": render_documents_rules(a),
        ".claude/rules/code.md": render_code_rules(a, profile),
        "README.md": render_readme(a),
        "CHANGELOG.md": render_changelog(a),
        ".gitignore": GITIGNORE_COMMON.replace("__DATA_CAP__", a.data_cap)
        + GITIGNORE_STACK[a.stack],
        ".editorconfig": EDITORCONFIG,
        "requirements/traceability/rtm.md": render_rtm(a),
    }
    for folder, prefix, title in REGISTERS:
        files[folder + "/index.md"] = render_index(prefix, title, a)

    if a.stack == "python":
        files["pyproject.toml"] = render_pyproject(a)
    elif a.stack == "dotnet":
        files[a.build_file] = render_sln()

    settings = json.loads(json.dumps(SETTINGS_BASE))
    if a.enforce_hook:
        settings["hooks"] = HOOK_BLOCK
        files[".claude/scripts/check_path.py"] = (
            Path(__file__).resolve().parent / "check_path.py"
        ).read_text(encoding="utf-8")
    files[".claude/settings.json"] = json.dumps(settings, indent=2) + "\n"

    # Nothing may reach a project with an unfilled slot in it. A stray
    # {{placeholder}} in CLAUDE.md reads as an instruction and quietly corrupts
    # every later placement decision, so fail loudly rather than ship it.
    for name, body in files.items():
        if name.endswith((".md", ".toml")) and "{{" in body:
            leftover = re.findall(r"\{\{[^}]*\}\}", body)
            print("error: unfilled placeholders in " + name + ": " + repr(leftover),
                  file=sys.stderr)
            return 1

    if a.dry_run:
        print("would create " + str(len(files)) + " files under " + str(root) + ":")
        for name in sorted(files):
            print("  " + name)
        return 0

    for name, body in sorted(files.items()):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        newline = "" if name.endswith(".sln") else "\n"
        target.write_text(body, encoding="utf-8", newline=newline)

    print("created " + str(len(files)) + " files under " + str(root))
    for name in sorted(files):
        print("  " + name)
    if a.license != "none":
        print("\nnote: --license " + a.license + " chosen; add LICENSE at the root yourself.")
    print(
        "\nNo other directories were created. The map in CLAUDE.md is the contract;\n"
        "each remaining folder appears when its first artifact lands."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
