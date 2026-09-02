<!--
TEMPLATE SETUP — delete this comment when done. (Block comments are stripped from
Claude's context, so leaving it in costs nothing but tidiness.)
1. Replace every {{placeholder}}; keep only the command block for this stack.
2. Do NOT scaffold empty folders. The map is the contract; a directory is created
   when its first artifact lands.
3. Per-area conventions live in .claude/rules/*.md, path-scoped so they load only
   when Claude touches matching files. Keep this file under ~200 lines.
4. Run /init once — with a CLAUDE.md present it proposes additions, not a rewrite.
   If /doctor offers to trim the directory map, decline: the map is prescriptive,
   not something Claude can derive from an empty repo.
-->

# {{PROJECT_NAME}}

{{One paragraph: what the system does, for whom, and the current phase.}}

- **Stack:** {{languages, frameworks, runtimes and versions}}
- **Phase:** {{discovery | requirements | design | build | verification | operations}}
- **Issue tracker:** {{URL — or "management/issues/" if there is none}}
- **Secrets:** live in {{secret manager}}; nothing secret is ever committed

## Commands

Run from the repo root. Keep this current — Claude uses it instead of guessing.

```bash
# Python
{{uv sync}}                          # install / sync environment
{{pytest tests/unit}}                # fast tests — run before every commit
{{pytest}}                           # full suite
{{ruff check . && ruff format .}}    # lint + format
{{mypy src}}                         # type check

# .NET
{{dotnet build}}                     # build
{{dotnet test tests/unit}}           # fast tests — run before every commit
{{dotnet test}}                      # full suite
{{dotnet format}}                    # format
```

## Rules that always apply

1. Every artifact has exactly one home: find it in the map, then in the look-alike table. Still unsure → ask. Never guess, and never create a new top-level directory.
2. Create a directory only when its first artifact exists.
3. Don't implement behaviour that has no requirement, and don't invent requirements — ask.
4. Non-trivial technical choices (framework, storage, protocol, pattern) get an ADR before the code.
5. `research/prototypes/` is never imported by `src/`. `archive/` and `external/` are read-only: move things in, never edit them there.
6. No secrets, credentials, or personal data in the repo. Reference secrets by name (`${DB_PASSWORD}`).
7. Edit diagram sources, not exports. New domain terms go into `project/glossary/glossary.md`.
8. `requirements/traceability/rtm.md` is updated in the same change as any REQ, design doc, code path, or test it links.
9. Detailed conventions: `.claude/rules/documents.md` (all lifecycle documents) and `.claude/rules/code.md` (`src/`, `tests/`).

## Directory map

```text
{{project-name}}/
├── CLAUDE.md  README.md  CHANGELOG.md  LICENSE  .gitignore  .editorconfig
├── {{pyproject.toml | Project.sln}}  # workspace / solution file — always at root
├── .claude/                 # settings.json, rules/ (path-scoped conventions), skills/
│
├── project/                 # WHY — definition; changes rarely
│   ├── charter/             # charter, vision, objectives, success criteria
│   ├── scope/               # in/out of scope, deliverables, assumptions, constraints
│   ├── stakeholders/        # stakeholder register, RACI, communication plan
│   ├── glossary/            # glossary.md — single source for domain terms and acronyms
│   └── decisions/           # DEC-nnnn business/scope/process decisions (technical → adr/)
├── management/              # HOW it is run — execution and control; changes often
│   ├── wbs/                 # work breakdown structure
│   ├── schedule/            # milestones, roadmap, iteration plans
│   ├── resources/           # people, roles, allocation, budget (assets → /resources)
│   ├── estimates/           # effort and cost estimates with their basis
│   ├── risks/               # RISK-nnnn register
│   ├── issues/              # ISS-nnnn project-level issues (code defects → tracker)
│   ├── changes/             # CR-nnnn change requests with impact analysis
│   └── reports/             # status reports, meeting notes — YYYY-MM-DD- prefixed
├── research/                # exploration — nothing here is production
│   ├── studies/             # feasibility and trade studies
│   ├── experiments/         # YYYY-MM-DD-topic/ notebooks, logs, results
│   ├── prototypes/          # disposable code, never imported by src/
│   ├── benchmarks/          # benchmark setup + results
│   └── references/          # bibliography.md — papers, articles, links
├── requirements/            # WHAT it must do — REQ-* records, one requirement per heading
│   ├── business/            # REQ-BUS goals, user needs, use cases
│   ├── system/              # REQ-SYS whole solution, black box
│   ├── software/            # REQ-SW derived from SYS, cites its parent ID
│   ├── interfaces/          # REQ-IF what external interfaces must support
│   ├── non-functional/      # REQ-NF performance, security, usability, compliance targets
│   └── traceability/        # rtm.md — REQ ↔ ADR/design ↔ src ↔ test ↔ evidence
├── architecture/            # HOW it is structured — system level
│   ├── context/             # C4 L1 system boundary, external actors and systems
│   ├── system/              # C4 L2 containers/subsystems and responsibilities
│   ├── software/            # C4 L3 modules, layering, dependencies inside a container
│   ├── data/                # conceptual/logical data model, flows, ownership, retention
│   ├── infrastructure/      # deployment topology, environments, networking
│   ├── security/            # threat model, trust boundaries, auth/authz, crypto choices
│   ├── interfaces/          # interface inventory: what talks to what, protocol, owner
│   ├── diagrams/            # diagram sources (.drawio, .puml, .mmd) + exports
│   └── adr/                 # ADR-nnnn technical decisions
├── design/                  # HOW each part works — detail before code
│   ├── components/          # one design doc per src component, cites REQ IDs
│   ├── database/            # physical schema, indexes, partitioning, migration strategy, ERDs
│   ├── interfaces/          # contracts to implement: OpenAPI, .proto, message schemas, errors
│   ├── algorithms/          # descriptions, pseudocode, complexity
│   └── specifications/      # state machines, file formats, anything else detailed
├── src/                     # production code only — see .claude/rules/code.md
│   ├── apps/                # deployable entry points: UIs, CLIs, desktop apps
│   ├── services/            # long-running services, APIs, workers
│   ├── libraries/           # reusable packages consumed by apps and services
│   └── tools/               # maintained internal tooling and dev automation
├── tests/                   # mirrors src/ paths inside each level
│   ├── unit/                # fast, isolated, no I/O
│   ├── integration/         # component interactions, real dependencies in containers
│   ├── system/              # end-to-end on a deployed system
│   ├── performance/         # load, stress, benchmark tests
│   ├── security/            # scan configs, DAST scripts, abuse-case tests
│   ├── acceptance/          # customer-facing tests keyed to REQ-BUS/SYS
│   └── evidence/            # per-release sign-off artifacts only
├── data/                    # definitions and small datasets; large data lives elsewhere
│   ├── schemas/             # machine-readable, versioned: JSON Schema, .proto, Avro, DDL
│   ├── metadata/            # data dictionaries, lineage, classification
│   ├── samples/             # small anonymised real samples (< {{1 MB}} each)
│   ├── synthetic/           # generated data + generator config
│   └── manifests/           # what each dataset is, where the full copy lives, checksums
├── resources/               # non-code assets used at build or run time
│   ├── configuration/       # config defaults and templates (env values → infra/environments)
│   ├── templates/           # document, report, code templates
│   ├── models/              # {{ML/trained}} models if small; otherwise model card + manifest
│   └── third-party/         # vendored assets, each with its LICENSE
├── infra/                   # infrastructure as code — declarative
│   ├── docker/              # Dockerfiles, compose files
│   ├── terraform/           # cloud resources
│   ├── kubernetes/          # manifests, Helm charts
│   └── environments/        # dev/ staging/ prod/ values — no secrets
├── ops/                     # operating the deployed system — procedural
│   ├── deployment/          # release procedures, checklists, rollout/rollback, CI description
│   ├── monitoring/          # dashboards, alerts, SLOs
│   ├── runbooks/            # step-by-step operational procedures
│   ├── backup/              # backup policy and procedures
│   └── disaster-recovery/   # DR plan, RTO/RPO, restore test records
├── quality/                 # coding-standards.md, review-checklist.md, definition-of-done.md, metrics/
├── security/                # policy.md, secure-development.md, assessments/, incidents/ — never secrets
├── compliance/              # applicability.md, control-matrix.md (control → implementation → evidence), audits/
├── external/                # material from or for outside parties — read-only inputs
│   ├── customer/            # customer-provided inputs and feedback (contracts stay in {{DMS}})
│   ├── suppliers/           # supplier docs, SLAs, vendor evaluations
│   └── standards/           # applicable standards: title, version, clauses used (no licensed text)
├── docs/                    # delivered, audience-facing documentation
│   ├── manuals/             # user, admin, API manuals
│   ├── onboarding/          # new team member guide
│   ├── training/            # training materials
│   └── presentations/       # YYYY-MM-DD-title decks
└── archive/                 # superseded documents, at the same path as their original location
```

## Look-alike folders

| It is… | So it goes in… |
|---|---|
| A "shall" statement about an interface | `requirements/interfaces/` |
| Which interfaces exist between which parts, protocol, owner | `architecture/interfaces/` |
| The exact contract to implement (OpenAPI, `.proto`, message schema, error codes) | `design/interfaces/` |
| A requirement on the whole solution (hardware, people, procedures, software) | `requirements/system/` — the software-only part derived from it → `requirements/software/` |
| Deployable containers / subsystems | `architecture/system/` — modules inside one container → `architecture/software/` |
| A decision a developer needs to build correctly | `architecture/adr/` (ADR) — a decision a sponsor/PM needs (scope, budget, vendor, process) → `project/decisions/` (DEC) |
| Threat model, trust boundaries, auth model | `architecture/security/` — executable scans/tests → `tests/security/` — policy, assessments, incidents → `security/` |
| Conceptual/logical data model, flows, ownership | `architecture/data/` — physical tables, indexes, ERDs → `design/database/` — machine-readable schemas → `data/schemas/` — migrations → `src/` beside the owning service |
| Config defaults/templates shipped with the software | `resources/configuration/` — per-environment values → `infra/environments/{{env}}/` — config-loading code → `src/` |
| Literature the team learned from | `research/references/` — normative documents to conform to (standards, RFCs, regulations, customer specs) → `external/standards/` |
| Maintained, tested tooling | `src/tools/` — disposable experiment → `research/prototypes/` (promote via a `design/components/` doc plus tests) |
| People, roles, allocation, budget | `management/resources/` — project assets → `resources/` |
| Delivered, audience-facing documentation | `docs/` — engineering documents stay in their lifecycle folder; `docs/` links to them, never duplicates |
| A CI/CD pipeline definition | Where the tool requires it (`.github/workflows/`, `.gitlab-ci.yml`) — described in `ops/deployment/` |
| Release sign-off artifacts (test report, coverage, RTM snapshot) | `tests/evidence/{{version}}/` — everyday test output is gitignored |
| A superseded document | `archive/` at the same relative path, with `status: superseded` and `superseded-by:` set — superseded code is handled by git history, not `archive/` |

## Naming and IDs

- Files and folders: `kebab-case`, ASCII. Dated records: `YYYY-MM-DD-` prefix. Identified records: `ID-kebab-title.md`, e.g. `ADR-0007-use-postgresql.md`.
- IDs: four digits, zero-padded, per prefix; never reused or renumbered. Each register folder keeps an `index.md` (ID, title, status, owner, updated); next ID = highest in the index + 1.

| Prefix | Register | Prefix | Register |
|---|---|---|---|
| `REQ-BUS-nnnn` | `requirements/business/` | `ADR-nnnn` | `architecture/adr/` |
| `REQ-SYS-nnnn` | `requirements/system/` | `DEC-nnnn` | `project/decisions/` |
| `REQ-SW-nnnn` | `requirements/software/` | `RISK-nnnn` | `management/risks/` |
| `REQ-IF-nnnn` | `requirements/interfaces/` | `ISS-nnnn` | `management/issues/` |
| `REQ-NF-nnnn` | `requirements/non-functional/` | `CR-nnnn` | `management/changes/` |

## Change workflow

1. Feature: confirm or create the REQ → ADR if a choice is involved → `design/components/` doc if a new component → code → tests → `rtm.md` → `CHANGELOG.md`.
2. Requirement change: `CR-nnnn` with impact analysis → update the REQ (status, history) → propagate to design, code, tests, RTM.
3. Release: `tests/evidence/{{version}}/` → `CHANGELOG.md` → `ops/deployment/` checklist.

## Git

- Branches: `feature/{{ID}}-short-desc`, `fix/{{ID}}-short-desc`, `docs/{{ID}}-short-desc`.
- Commits: Conventional Commits, scope = top-level folder, IDs in the body — `feat(src): add csv importer (REQ-SW-0012)`.
- Never commit: secrets, `.env` (keep `.env.example` in `resources/configuration/`), build output, virtual envs, datasets over {{1 MB}}, everyday test output, personal IDE settings, `CLAUDE.local.md`.
