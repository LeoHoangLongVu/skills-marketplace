---
id: 
title: <component name>
status: draft
owner: <name>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
relates-to: [REQ-SW-nnnn, ADR-nnnn]
---

# <component name>

Design for `src/<kind>/<name>/`. Written with the first implementation, not
after it: a design doc that documents code already written records what was
done, not what was decided.

## Requirements satisfied

| REQ | How this component satisfies it |
|---|---|
| <REQ-SW-nnnn> | <...> |

## Responsibilities

<What this component owns. Just as usefully: what it deliberately does not.>

## Interfaces

<What it exposes and what it consumes. The executable contract itself lives in
`design/interfaces/`; link it rather than restating it.>

## Structure

<Modules, key types, and how data moves through them.>

## Design decisions

<Choices local to this component. Anything that shapes the architecture is an
ADR instead.>

## Testing

<How the requirements above are verified, and at which test level.>
