# Postmortem: Cascading Crash-Loop During Rolling Deployment

**Severity:** SEV-2
**Duration:** 38 minutes (partial degradation), 12 minutes (full outage)
**Services affected:** checkout-api (all regions)

## Summary

A routine rolling deployment of the `checkout-api` service triggered a
cascading crash-loop across all replicas, taking the service fully down
for 12 minutes and degraded for another 26 minutes while the rollback
propagated.

## Impact

- All checkout requests failed with 503s for 12 minutes
- Elevated latency and intermittent 5xx errors for a further 26 minutes
  during rollback
- No data loss; in-flight transactions were retried successfully by the
  client once service recovered

## Timeline (all times UTC)

- **14:02** — Deployment of `checkout-api` v2.14.0 begins via rolling
  update (maxSurge=1, maxUnavailable=0)
- **14:03** — New pods enter `Running` but fail readiness checks
  repeatedly; deployment controller keeps replacing them because old
  pods are being scaled down on schedule regardless of new pod
  readiness
- **14:05** — Readiness probe failures escalate: the new pods depend on
  a downstream connection pool that takes ~45s to warm up, but the
  readiness probe's `initialDelaySeconds` was left at the old default
  of 5s
- **14:07** — Enough old, healthy pods have been terminated that
  remaining capacity can't handle traffic; the service starts returning
  503s
- **14:14** — On-call is paged, confirms crash-loop pattern, begins
  manual rollback via `kubectl rollout undo`
- **14:19** — Old ReplicaSet fully restored; error rate begins dropping
- **14:40** — Latency and error rate fully back to baseline

## Root Cause

The readiness probe's `initialDelaySeconds` (5s) did not account for a
new connection-pool warm-up step added in v2.14.0 that takes ~45
seconds under normal load. Because the deployment strategy used
`maxUnavailable=0`, Kubernetes kept the total pod count constant by
terminating an old (healthy) pod for every new pod it created —  but
since the new pods never passed their readiness check within a
reasonable window, the deployment slowly bled off healthy capacity
without ever having a working replacement ready to take traffic.

## Detection

Detected by external synthetic monitoring (checkout flow probe) 5
minutes after the crash-loop began — internal alerting on readiness
probe failure rate existed but was not wired to page on-call, only to
a low-priority Slack channel that went unnoticed during a shift
handoff.

## Resolution

Manual rollback via `kubectl rollout undo`. Root cause was fixed
by raising `initialDelaySeconds` to 60s and adding a `startupProbe`
with a longer failure threshold, so slow-starting pods get more grace
before being counted against deployment health — without also relaxing
the readiness probe's steady-state sensitivity.

## Action Items

- [x] Add `startupProbe` to `checkout-api` with 90s total grace period
- [x] Wire readiness-probe-failure-rate alert to the on-call pager, not
      just Slack
- [ ] Add a pre-deploy checklist item: "does this change any startup
      dependency timing? If so, review probe config."
- [ ] Evaluate `maxUnavailable=1` for this service to avoid fully
      bleeding capacity during a bad rollout
