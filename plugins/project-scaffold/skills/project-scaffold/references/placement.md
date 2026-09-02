# Deciding where a file goes

The directory map in `CLAUDE.md` names the folders. The look-alike table next to
it resolves the pairs people most often confuse. This file is for the step
before both: working out **what kind of artifact you are holding**, because once
that is settled the folder is usually obvious.

Read the relevant section, place the file, then confirm with:

```bash
python <skill>/scripts/check_path.py <proposed/path>
```

## Contents

- [The one question](#the-one-question)
- [The lifecycle ladder](#the-lifecycle-ladder)
- [Hard case: interfaces](#hard-case-interfaces)
- [Hard case: decisions](#hard-case-decisions)
- [Hard case: data](#hard-case-data)
- [Hard case: security](#hard-case-security)
- [Hard case: configuration](#hard-case-configuration)
- [Hard case: code that is not production code](#hard-case-code-that-is-not-production-code)
- [Hard case: documentation](#hard-case-documentation)
- [Choosing a requirement level](#choosing-a-requirement-level)
- [Choosing a test level](#choosing-a-test-level)
- [Worked examples](#worked-examples)
- [When you are genuinely unsure](#when-you-are-genuinely-unsure)

## The one question

> Which stage of the work does this artifact belong to, and who consumes it?

Almost every misfiling comes from answering "what is it about?" instead. A
document *about* the database could be an architectural data model, a physical
schema design, a machine-readable DDL, a migration, or a runbook for restoring
it — five different homes. The subject does not place the file; the stage does.

## The lifecycle ladder

The top-level folders are a ladder. Walk down until you reach the rung that
matches, and stop there.

| Rung | Folder | The artifact answers |
|---|---|---|
| Why are we doing this? | `project/` | purpose, scope, stakeholders, vocabulary |
| How is the work run? | `management/` | plan, risks, issues, changes, reports |
| What did we learn first? | `research/` | studies, experiments, throwaway prototypes |
| What must it do? | `requirements/` | testable "shall" statements with IDs |
| How is it structured? | `architecture/` | boundaries, containers, cross-cutting choices |
| How does each part work? | `design/` | the detail a developer builds from |
| The thing itself | `src/` | production code |
| Does it do what it must? | `tests/` | executable verification |
| What does it run on and with? | `data/` `resources/` `infra/` | inputs and environment |
| How do we operate it? | `ops/` | deployment, monitoring, runbooks, recovery |
| How do we know it is good? | `quality/` `security/` `compliance/` | policy, standards, evidence |
| Not ours, or no longer current | `external/` `archive/` | read-only |
| Delivered to an audience | `docs/` | manuals, onboarding, training, decks |

Two rungs are commonly skipped by mistake. Something that reads like a
requirement but has no ID and no verification method is usually still scope
(`project/scope/`). Something that reads like a design but decides a boundary
between components is architecture, not design.

## Hard case: interfaces

Four folders carry the word, and each holds a different artifact about the same
interface.

| You have | Folder |
|---|---|
| A "shall" statement about what an interface must support | `requirements/interfaces/` |
| An inventory: what talks to what, over which protocol, owned by whom | `architecture/interfaces/` |
| The contract to implement — OpenAPI, `.proto`, message schema, error codes | `design/interfaces/` |
| A machine-readable data shape reused beyond one interface | `data/schemas/` |
| The generated client or server code | `src/` |

The test that separates them: *what would a reader do with it?* Agree it
(requirements), draw it (architecture), implement it (design), import it (src).

## Hard case: decisions

| The decision | Folder | Prefix |
|---|---|---|
| A developer needs it to build correctly | `architecture/adr/` | `ADR` |
| A sponsor, PM or customer needs it — scope, budget, vendor, process, schedule | `project/decisions/` | `DEC` |
| It changes something already approved | `management/changes/` | `CR` |

"We will use PostgreSQL" is an ADR. "We will buy a managed database rather than
run our own" is a DEC — it is a commercial decision whose technical consequence
gets its own ADR. Both may exist, and they link to each other.

An accepted ADR is never rewritten. Superseding it means a new ADR that sets
`supersedes:`, and the old file moving to `archive/architecture/adr/` with
`status: superseded` and `superseded-by:` set.

## Hard case: data

| You have | Folder |
|---|---|
| Conceptual or logical model, data flows, ownership, retention | `architecture/data/` |
| Physical schema, indexes, partitioning, ERDs, migration strategy | `design/database/` |
| Versioned machine-readable schema — JSON Schema, `.proto`, Avro, DDL | `data/schemas/` |
| Data dictionary, lineage, classification | `data/metadata/` |
| A small anonymised real extract | `data/samples/` |
| Generated data and its generator config | `data/synthetic/` |
| A pointer to a full dataset held elsewhere, with checksums | `data/manifests/` |
| Executable migrations | `src/`, beside the service that owns the table |

Migrations are the one that trips people. They are code, they are versioned with
the service, and they must deploy with it — so they live with the service, not
in `design/database/`, which holds the *strategy* for migrating.

## Hard case: security

| You have | Folder |
|---|---|
| Threat model, trust boundaries, auth/authz model, crypto choices | `architecture/security/` |
| Policy, secure-development standard, assessments, incident records | `security/` |
| Scan configuration, DAST scripts, abuse-case tests | `tests/security/` |
| Which controls apply, and the evidence each one is met | `compliance/` |
| An actual secret | nowhere — the secret manager, referenced by name |

`architecture/security/` is how *this system* is secured. `security/` is how
*this team* works. `compliance/` is what an auditor is shown.

## Hard case: configuration

| You have | Folder |
|---|---|
| Defaults and templates shipped with the software, `.env.example` | `resources/configuration/` |
| Values for one environment | `infra/environments/<env>/` |
| The code that loads and validates configuration | `src/` |
| A real secret value | the secret manager — never a file in the repo |

## Hard case: code that is not production code

| You have | Folder | Rule |
|---|---|---|
| Maintained, tested internal tooling | `src/tools/` | may depend on `libraries/`; nothing depends on it |
| A disposable experiment | `research/prototypes/` | `src/` never imports it |
| A benchmark harness and its results | `research/benchmarks/` | |
| A dated experiment with notebooks and logs | `research/experiments/YYYY-MM-DD-topic/` | |

Promoting a prototype is not a move: it is a rewrite into `src/`, with a
`design/components/` doc and tests. The prototype stays where it is as the
record of what was tried.

## Hard case: documentation

`docs/` is for delivered, audience-facing material: manuals, onboarding,
training, decks. Engineering documents stay on their own rung of the ladder and
`docs/` links to them.

The failure this prevents is duplication. A copy of the architecture in `docs/`
does not stay in step with `architecture/`, and a reader has no way to tell
which of the two is current.

## Choosing a requirement level

| Prefix | Folder | Scope |
|---|---|---|
| `REQ-BUS` | `requirements/business/` | a goal, user need or use case |
| `REQ-SYS` | `requirements/system/` | the whole solution — hardware, people, procedures, software |
| `REQ-SW` | `requirements/software/` | the software part, derived from a `REQ-SYS` |
| `REQ-IF` | `requirements/interfaces/` | what an external interface must support |
| `REQ-NF` | `requirements/non-functional/` | performance, security, usability, compliance targets |

Every `REQ-SW` cites its parent `REQ-SYS`; every `REQ-SYS` cites its `REQ-BUS`.
An orphan is a defect: it means either the parent was never written, or the
requirement was invented rather than derived.

## Choosing a test level

| Level | What it exercises |
|---|---|
| `unit` | one unit, no network, filesystem, clock or randomness except through fakes |
| `integration` | components together, real dependencies from `infra/docker/` |
| `system` | end to end on a deployed system |
| `performance` | load, stress, benchmarks |
| `security` | scans, DAST, abuse cases |
| `acceptance` | customer-facing, keyed to `REQ-BUS` / `REQ-SYS` |
| `evidence` | per-release sign-off artifacts only, at `tests/evidence/<version>/` |

Inside each level, mirror the source path: `src/libraries/parser/` is tested by
`tests/unit/parser/`. Everyday test output is gitignored; only release sign-off
artifacts are committed, and only under `evidence/`.

## Worked examples

| The artifact | Path | Why |
|---|---|---|
| "The API shall accept CSV up to 50 MB" | `requirements/interfaces/REQ-IF-0004-csv-upload-limit.md` | a shall statement about an interface |
| The OpenAPI file for that API | `design/interfaces/telemetry-api.yaml` | the contract to implement |
| A diagram of which services call it | `architecture/interfaces/service-inventory.md` | what talks to what |
| "We chose Kafka over RabbitMQ" | `architecture/adr/ADR-0009-use-kafka.md` | a build-affecting technical choice |
| "We will not support IE11" | `project/decisions/DEC-0003-drop-ie11.md` | a scope decision |
| Notes from Tuesday's design review | `management/reports/2026-09-02-review-ingest.md` | dated record; decisions extracted to ADR/DEC |
| A script that reprocesses failed uploads | `src/tools/reprocess-uploads/` | maintained tooling |
| A notebook trying three parsers | `research/experiments/2026-09-02-parser-comparison/` | dated experiment |
| The step-by-step for a failed deploy | `ops/runbooks/rollback-ingest.md` | operating procedure |
| The rollout checklist itself | `ops/deployment/release-checklist.md` | release procedure |
| A customer's PDF specification | `external/customer/` | material from outside, read-only |
| ISO 27001 clause applicability | `compliance/applicability.md` | which controls apply |
| The 27001 standard text | nowhere — cite it in `external/standards/` | licensed text is not copied in |
| A superseded ADR | `archive/architecture/adr/ADR-0002-use-mysql.md` | same relative path under `archive/` |

## When you are genuinely unsure

Rule 1 says: find it in the map, then in the look-alike table, and if still
unsure, ask. That last clause is not politeness — it is the cheapest step in the
sequence. A misplaced document is found months later by someone who does not
know it exists, whereas a question costs one message.

What not to do instead:

- Do not invent a top-level folder. A new top level asserts a class of artifact
  the project has not agreed on.
- Do not put it in `docs/` because it is "documentation". Nearly everything here
  is documentation; `docs/` means *delivered to an audience*.
- Do not put it at the repository root. The root holds workspace files only.
- Do not create a folder speculatively. A directory exists once its first
  artifact lands, so an empty one is a claim about work that has not happened.
