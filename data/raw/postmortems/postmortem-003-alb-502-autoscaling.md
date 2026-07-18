# Postmortem: 502 Errors During Auto-Scaling Event

**Severity:** SEV-2
**Duration:** 22 minutes
**Services affected:** public-api (behind ALB)

## Summary

A traffic spike triggered horizontal auto-scaling on `public-api`, but
newly launched instances began receiving traffic from the load balancer
before their application process had finished starting, causing a wave
of 502 Bad Gateway errors.

## Impact

- ~9% of requests returned 502 during the 22-minute window
- No data loss; all failed requests were safe-to-retry GETs
- Elevated error-rate alerts paged on-call twice (once for the initial
  spike, once for a smaller recurrence during scale-in)

## Timeline (all times UTC)

- **18:02** — Traffic increases ~3x over 4 minutes (marketing campaign
  went live); target tracking scaling policy triggers scale-out from 4
  to 10 instances
- **18:04** — New EC2 instances pass EC2 status checks and are
  registered with the ALB target group
- **18:04** — ALB begins routing traffic to new instances within
  seconds of registration, per the target group's default health check
  settings (`HealthCheckIntervalSeconds=30`, `HealthyThresholdCount=2`,
  `UnhealthyThresholdCount=2` — but crucially, targets are eligible to
  receive traffic once they pass their *first* passing health check,
  not before)
- **18:04–18:06** — Application process on new instances takes ~35
  seconds to fully initialize (loading a large in-memory lookup table
  on startup) — during this window the process isn't listening on the
  health check port yet, so the *first* health check correctly fails,
  but by the time the second check passes, the app has only been ready
  for a few seconds and is still working through a connection backlog
- **18:06** — 502 rate climbs as new targets, freshly marked healthy,
  get flooded with more concurrent connections than the still-warming
  process can handle
- **18:24** — Backlog clears naturally as instances fully stabilize;
  error rate returns to baseline

## Root Cause

The ALB health check was checking process liveness (a lightweight
`/health` endpoint that responded immediately, before the large
lookup-table load completed) rather than true readiness to serve
production traffic. This meant instances were marked "healthy" and
given full traffic weight well before they could actually handle
production load, causing a thundering-herd effect against
still-warming instances.

## Detection

Detected via ALB 5xx CloudWatch alarm 2 minutes after the scale-out
event began.

## Resolution

No manual intervention required — the system self-recovered once
instances finished warming up. Root cause was fixed by changing the
`/health` endpoint to only return 200 once the lookup table is fully
loaded (true readiness, not just liveness), and separately adding an
ALB connection-draining-style ramp using weighted target groups for
future scale-out events.

## Action Items

- [x] Change `/health` endpoint to reflect true application readiness,
      not just process liveness
- [x] Increase `HealthyThresholdCount` from 2 to 3 to add a small
      additional buffer before new targets take full traffic
- [ ] Evaluate AWS's target group "slow start" feature to ramp traffic
      to new targets gradually instead of immediately at full weight
- [ ] Load-test the lookup-table initialization path to reduce the
      35s startup window itself
