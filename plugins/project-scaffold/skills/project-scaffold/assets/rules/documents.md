---
paths:
  - "{project,management,research,requirements,architecture,design,ops,quality,security,compliance,external,docs}/**/*.md"
---

# Document conventions

Every Markdown document starts with this frontmatter:

```yaml
---
id: ADR-0007                 # omit for documents without an ID
title: Use PostgreSQL as the primary store
status: draft                # draft | review | approved | superseded | deprecated
owner: {{name}}
created: 2026-09-02
updated: 2026-09-02
supersedes:                  # optional ID
superseded-by:               # optional ID
relates-to: [REQ-SW-0012, REQ-NF-0003]
---
```

## Lifecycle

- New documents start as `draft`. Only a human moves a document to `approved` — never set it yourself.
- Approved documents are not edited in place: raise a `CR-nnnn` in `management/changes/`, then update the document, bump `updated`, and add a line under a `## History` heading at the end (date, CR, what changed).
- Superseding: move the old file to `archive/` at the same relative path, set `status: superseded` and `superseded-by:` on it; set `supersedes:` on the new file; update the register's `index.md`.

## Requirements (`requirements/**`)

- One requirement per `##` heading, titled with its ID: `## REQ-SW-0012 — Import CSV files`.
- Body, in order: the "The system shall …" statement; **Rationale**; **Source** (parent REQ, DEC, or the `external/` input it came from); **Verification** (test | analysis | inspection | demonstration); **Priority** ({{must | should | could}}).
- `REQ-SW` cites its parent `REQ-SYS`; `REQ-SYS` cites its `REQ-BUS`. No orphans, no duplicates — search the register before adding.
- `requirements/traceability/rtm.md` columns: REQ | Parent | ADR / design doc | Source path | Test path | Evidence | Status. Update it in the same change as the requirement.

## ADRs (`architecture/adr/**`)

- Sections in order: Context and problem · Decision drivers · Options considered (pros/cons each) · Decision · Consequences · Related (REQ / DEC / ADR IDs).
- Never delete or rewrite an accepted ADR — supersede it with a new one.

## Registers (`index.md` in each ID folder)

- One table: ID | Title | Status | Owner | Updated, sorted by ID, kept in sync with the files in the folder.

## Reports and notes (`management/reports/**`)

- File name `YYYY-MM-DD-{{type}}-{{topic}}.md`. Decisions taken in a meeting are extracted into a DEC or ADR and linked; the notes are not the record of the decision.

## Links and assets

- Relative links only. Reference other artifacts by ID and path, e.g. `[REQ-SW-0012](../../requirements/software/REQ-SW-0012-import-csv-files.md)`.
- Diagrams: edit the source in `architecture/diagrams/`, export beside it, embed the export. Never hand-edit an exported image.
- `external/` content is quoted or summarised, never modified. Licensed standard texts are not copied into the repo.
