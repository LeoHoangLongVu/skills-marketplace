---
id: CR-nnnn
title: <what is being changed>
status: draft
owner: <name>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
relates-to: [REQ-SW-nnnn]
---

# CR-nnnn - <what is being changed>

An approved document is not edited in place. The CR is the record of why it
changed, so that a reader six months later can tell a correction from a
reversal.

## Requested change

<What should become different, and who asked.>

## Reason

<What made the current state wrong or insufficient.>

## Impact analysis

| Area | Affected | Notes |
|---|---|---|
| Requirements | <IDs> | <...> |
| Architecture / ADRs | <IDs> | <...> |
| Design | <paths> | <...> |
| Code | <paths> | <...> |
| Tests | <paths> | <...> |
| Schedule / cost | <...> | <...> |

## Decision

<approved / rejected / deferred, by whom, on what date.>

## Propagation

Every item ticked here is done in the same change as the document update, not
afterwards - a half-propagated CR leaves the RTM asserting something untrue.

- [ ] Requirement updated (status, `## History` line)
- [ ] Design and ADRs updated
- [ ] Code and tests updated
- [ ] `requirements/traceability/rtm.md` updated
- [ ] `CHANGELOG.md` updated
- [ ] Register `index.md` updated
