# Postmortem: Terraform Apply Destroyed a Production RDS Read Replica

**Severity:** SEV-1
**Duration:** 4 hours 20 minutes (read-replica capacity loss)
**Services affected:** reporting-service (read-heavy queries)

## Summary

A `terraform apply` intended to add tags to an RDS instance instead
destroyed and attempted to recreate a production read replica, because
the replica had drifted out of Terraform's state after a manual console
change made during an earlier incident.

## Impact

- Production read replica for `reporting-db` was destroyed
- All read-heavy reporting queries fell back to the primary DB,
  increasing primary CPU load by ~60%
- No customer-facing outage, but reporting dashboards were
  significantly slower for the duration
- Replica recreation + resync took 4h20m due to database size

## Timeline (all times UTC)

- **09:14** — Engineer runs `terraform plan` to add cost-allocation
  tags to several RDS resources; plan output shows only tag changes
  for `reporting-db-replica`, as expected
- **09:16** — `terraform apply` executed; Terraform's actual plan for
  `reporting-db-replica` includes an in-place tag update, but a
  *separate* resource in the same apply — the parameter group
  associated with the replica — shows as "must be replaced" due to an
  immutable field change that wasn't visible in the truncated plan
  output the engineer reviewed
- **09:16** — Replacing the parameter group forces replacement of the
  RDS instance that references it (this dependency wasn't obvious from
  the resource names)
- **09:17** — Terraform destroys `reporting-db-replica` and begins
  creating a replacement
- **09:22** — Reporting dashboard alerts fire for elevated query
  latency; on-call begins investigating
- **09:40** — Root cause identified: replica is gone, primary is
  absorbing all read traffic
- **13:40** — New replica finishes initial sync and is promoted back
  into rotation; latency returns to baseline

## Root Cause

Three weeks earlier, during an unrelated incident, an engineer had
manually modified the RDS parameter group via the AWS console as a
fast mitigation, without updating the corresponding Terraform
resource. This created drift: Terraform's state no longer matched
reality. When the tagging change was applied, Terraform's plan
correctly detected that the *live* parameter group didn't match what
Terraform expected, and — because the field that had drifted was one
that forces replacement — planned to replace it, which cascaded into
replacing the RDS instance depending on it.

The plan output did show this, but it was buried lower in a long
plan (47 resources, multi-page terminal output) and the reviewing
engineer scrolled past it, having grepped only for the resource name
they intended to change.

## Detection

Caught by automated latency alerting on the reporting service 6
minutes after the apply, not by any Terraform-side safety check.

## Resolution

New replica created and resynced. Going forward, any manual
console changes made during an incident are now required to be
reconciled back into Terraform state (via `terraform import` or a
follow-up PR) within 24 hours, tracked as a mandatory post-incident
action item.

## Action Items

- [x] Add `terraform plan -detailed-exitcode` to CI so any apply with
      unreviewed destroy/replace actions requires explicit sign-off,
      not just a passing plan
- [x] Document and enforce: manual console changes during incidents
      must be reconciled into Terraform within 24h
- [ ] Investigate `terraform plan` output tooling that surfaces
      destroy/replace actions more prominently (e.g. plan summary
      bots in PR comments) instead of relying on manual review of raw
      CLI output
- [ ] Enable RDS deletion protection on all production replicas
