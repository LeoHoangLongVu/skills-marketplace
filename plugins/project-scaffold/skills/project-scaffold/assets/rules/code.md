---
paths:
  - "src/**/*"
  - "tests/**/*"
---

# Code conventions

## Layout

- One unit per folder: `src/{{apps|services|libraries|tools}}/{{name}}/`, each with its own build file. The root build file holds only workspace/solution-level configuration.
- Python: each unit has its own `pyproject.toml` with a `src/`-layout package inside it (`src/libraries/{{name}}/src/{{package}}/`); the root `pyproject.toml` carries only ruff, pytest and mypy config. Units are linked as a {{uv workspace | editable installs}}.
- .NET: `{{Project}}.sln` at the root; one `.csproj` per unit at `src/{{kind}}/{{Company.Project.Name}}/`; test projects at `tests/{{level}}/{{Company.Project.Name}}.Tests/`.
- A unit that is more than a thin wrapper has a design doc at `design/components/{{name}}.md` listing the REQ IDs it satisfies. Create or update it with the first implementation, not after.

## Tests

- Mirror the source path under each level: `src/libraries/{{name}}/…` is tested by `tests/unit/{{name}}/…`, `tests/integration/{{name}}/…`, and so on.
- Unit tests touch no network, filesystem, clock, or randomness except through injected fakes. Integration tests get real dependencies from `infra/docker/`.
- Tag each test with the requirement it verifies so the RTM can be generated: {{`@pytest.mark.req("REQ-SW-0012")` | `[Trait("REQ", "REQ-SW-0012")]`}}.
- Everyday test output (reports, coverage, screenshots) is gitignored. Only release sign-off artifacts go in `tests/evidence/{{version}}/`.

## Style and quality

- Formatter/linter: {{ruff | dotnet format + analyzers}}, clean before every commit. Types: {{mypy --strict | nullable enabled, warnings as errors}}.
- Public APIs are documented: {{Google-style docstrings | XML doc comments}}.
- Logging via {{library}}; configuration via {{mechanism}}; secrets only from the environment or {{secret manager}} — never from files in the repo.
- No `TODO` without an ISS or REQ ID. No commented-out code. No new dependency without an ADR if it shapes the architecture, or a line in `CHANGELOG.md` if it doesn't.
- Done means: tests pass, lint and types clean, `rtm.md` updated, design doc and `CHANGELOG.md` updated where behaviour changed.

## Boundaries

- `src/` never imports from `research/`, `tests/`, or `archive/`.
- `libraries/` never imports from `apps/` or `services/`; `apps/` and `services/` never import each other — shared code goes into `libraries/`.
- `tools/` may depend on `libraries/` but nothing depends on `tools/`.
