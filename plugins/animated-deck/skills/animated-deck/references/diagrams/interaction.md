# Interaction diagrams — call-flow, request/response, fan-out / fan-in

Use for **who calls whom and what comes back**: a request/response exchange, a service
call-flow, a subagent dispatch (one caller fanning out to workers and gathering results).
The emphasis is on *direction and reciprocity* of messages, not on a processing pipeline.
Read `references/diagrams/geometry.md` first.

## Layout patterns

**1. Two-actor exchange (request/response).** Two boxes side by side. A **request** arrow
along the top (left→right) and a **response** arrow along the bottom (right→left). Each box
then has exactly one inbound arrow, the pair reads as a conversation, and both arrows are
straight horizontals at well-separated `y` (e.g. caller/​service at cy 150, request at
y 120, response at y 180). Label each: "request", "returns ~1k".

**2. Caller → subagent → resource (delegation).** A caller delegates to a worker that does
heavy work against a resource and returns a small result. Draw the worker's heavy work as
its *own* arrow to the resource box ("reads 20 files"), and the result as a separate arrow
back to the caller ("returns ~1k"). The caller therefore shows two directions — one out to
the worker, one back — and the resource is a distinct box, not hidden inside the worker.

**3. Fan-out / fan-in.** One hub dispatching to N workers (fan-out) and/or N workers
reporting to one collector (fan-in). Draw with an orthogonal **comb** (see `geometry.md`):
a shared trunk in the gap, one feeder from the hub, equal stubs to each worker. Never
collapse the N workers into a single wrapper box with one arrow — that erases which workers
exist. A request/response *pair* between the same two boxes is allowed (one arrow each way).

## Sequence diagram (lifelines)

For a multi-step exchange among several actors (an OAuth flow, a checkout saga), a sequence
diagram is clearer than a flat box graph: actor boxes across the top, a vertical **lifeline**
dropping from each, and horizontal **messages** between lifelines at *increasing* y down the
slide. Alternate solid (request) and dashed (reply) lines and number them 1, 2, 3 … so the
order is unambiguous. Keep each message strictly horizontal and well-spaced vertically.

Caveat: `check_diagram.js` models boxes, not lifelines, so message arrowheads landing on a
lifeline will be reported as floating `TIP`s and the actor boxes will not overlap-check
against the lifelines. For a sequence diagram, **rely on the screenshot**, not the checker's
TIP rule — or draw each lifeline as a 1–2px-wide tall rectangle so message tips land on a
real (thin) box border and the checker stays meaningful.

## Connector idioms

- **Request and response are two separate arrows**, opposite directions, at different `y`
  (top vs bottom of the actor boxes), so each actor has a single inbound arrow and the two
  never overlap.
- **Dispatch to N workers:** comb fan-out, one arrowhead per worker box.
- **Gather from N workers:** comb fan-in, stubs merge to a trunk, one arrowhead into the
  collector.
- **Self-contained heavy work** (a worker reading many files) → its own arrow to a resource
  box that sits *beside* the worker, conveying "this stays inside the worker".

## Worked skeleton (delegation + return)

```
PROMPT ──delegate query──▶ SEARCH SUBAGENT ──reads 20──▶ [files]
   ◀──── returns ~1k ──────────┘
```

- `PROMPT → SUBAGENT` request arrow (top).
- `SUBAGENT → files` its own arrow (the heavy work, contained).
- `SUBAGENT → PROMPT` response arrow (bottom), landing back on PROMPT.
- Three arrows, each box one inbound, all right-angle, captions in the clear gaps.

## Checklist

- `node scripts/check_diagram.js deck.html` → `OK`.
- Request/response are distinct opposite arrows, not one bidirectional line.
- Fans are combs (separate arrowheads), never a wrapper-with-one-arrow.
- Every tip on a border; captions clear of lines/elbows/boxes; professional register.
