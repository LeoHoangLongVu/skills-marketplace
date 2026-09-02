# Incident Postmortem — Checkout 503s (2026-05-14)

**Severity:** SEV-2 · **Duration:** 47 minutes (14:02–14:49 UTC) · **Author:** Platform team

## Impact
- ~9,400 checkout attempts failed with HTTP 503 during the window.
- Estimated ~$78k in delayed/abandoned orders (most recovered on retry).
- No data loss; no security impact.

## Timeline (UTC)
- **14:00** — Routine deploy of `payments-api` v3.8.0 begins (rolling, 3 of 9 pods).
- **14:02** — First 503s on `/checkout`. Error rate climbs to 60% within 2 minutes.
- **14:06** — On-call paged by latency alert (p99 > 2s on payments-api).
- **14:11** — Dashboards show payments-api connection pool saturated; DB CPU at 95%.
- **14:23** — Deploy identified as the trigger; rollback to v3.7.4 started.
- **14:38** — Rollback complete across all pods; error rate begins dropping.
- **14:49** — Error rate back to baseline (<0.1%). Incident resolved.

## Root cause
v3.8.0 changed the DB client to open a **new connection per request** instead of using the
shared pool (a refactor removed the pool injection by mistake). Under checkout load this
exhausted Postgres's `max_connections` (200), so new connections were refused and requests
failed with 503. The connection-per-request path was never exercised in staging because
staging load is far below the connection ceiling.

## Resolution
Rolled back to v3.7.4, which uses the shared pool. Postgres recovered within seconds once
connection churn stopped.

## Prevention / action items
- Restore the pool injection and add a unit test asserting the pool is reused (DONE).
- Add a connection-count alert at 70% of `max_connections` (DONE).
- Add a staging load test that drives connection usage to the ceiling before release (planned).
- Make connection-per-request impossible by construction: the client constructor now requires
  a pool argument (planned).
