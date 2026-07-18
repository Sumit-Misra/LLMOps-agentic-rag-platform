# Postmortem: Missing Environment Variable Deployed a Broken Config to Production

**Severity:** SEV-2
**Duration:** 17 minutes
**Services affected:** notification-service

## Summary

A GitHub Actions workflow change reorganized how environment-specific
secrets were injected during deploy. A required environment variable
was correctly set for the staging environment but missed for
production, causing `notification-service` to start up with a null
downstream API endpoint and immediately fail all outbound
notifications.

## Impact

- 100% of outbound notifications (email + push) failed for 17 minutes
- No data loss — failed notification jobs were retried automatically
  once the fix deployed, per the service's existing retry queue design
- No impact to any other service; `notification-service` degraded
  independently

## Timeline (all times UTC)

- **16:50** — PR merges reorganizing the GitHub Actions deploy workflow
  to pull secrets from environment-scoped GitHub Environments instead
  of repo-level secrets, as part of a broader secrets-hygiene effort
- **16:52** — Deploy workflow runs for `notification-service`; the
  `NOTIFY_GATEWAY_URL` variable was added to the `staging` GitHub
  Environment during testing but the corresponding entry for the
  `production` GitHub Environment was never created — the workflow
  change itself was correct, only the environment's variable
  configuration was incomplete
- **16:53** — Deploy to production completes without error (the
  variable being empty is valid YAML/config, not a syntax error, so
  nothing fails at deploy time)
- **16:53** — Application starts, reads `NOTIFY_GATEWAY_URL` as an
  empty string, and every outbound notification attempt fails
  immediately with a connection error to an empty host
- **16:55** — Error-rate alert fires on `notification-service`;
  on-call begins investigating
- **17:04** — Root cause identified by comparing staging vs. production
  GitHub Environment variable lists
- **17:07** — Missing variable added to the production GitHub
  Environment; service redeployed
- **17:10** — Notifications resume; retry queue drains backlog within
  a few minutes

## Root Cause

The deploy workflow change was functionally correct, but the migration
from repo-level secrets to environment-scoped variables was done
manually per environment, and production was missed. There was no
automated check comparing required variables across environments, and
no startup-time validation in the application itself — it silently
accepted an empty URL rather than failing fast with a clear error.

## Detection

Detected via error-rate alerting 2 minutes after the bad deploy, not by
any pre-deploy validation.

## Resolution

Missing environment variable added; service redeployed. Longer-term
fix added startup-time config validation so the application refuses to
start (with a clear error) if required variables are missing or empty,
rather than starting successfully and failing on first use.

## Action Items

- [x] Add startup-time validation: `notification-service` now exits
      immediately with a descriptive error if `NOTIFY_GATEWAY_URL` (or
      any other required config) is unset or empty
- [x] Add a CI check that diffs required variable names across all
      GitHub Environments for a given workflow, failing the PR if
      production is missing something staging has
- [ ] Extend startup-time config validation pattern to other services
      as a standard template, not a one-off fix
- [ ] Consider a canary/smoke-test step post-deploy that exercises one
      real notification send before considering a deploy successful
