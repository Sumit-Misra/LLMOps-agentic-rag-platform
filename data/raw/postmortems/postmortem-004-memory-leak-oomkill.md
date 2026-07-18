# Postmortem: Undetected Memory Leak Leading to Recurring OOMKills

**Severity:** SEV-3
**Duration:** ~9 days (gradual degradation before detection)
**Services affected:** event-processor

## Summary

A slow memory leak in `event-processor`, introduced by a caching change
two weeks prior, went undetected for 9 days because the existing memory
alert threshold was tuned for sudden spikes, not gradual creep — pods
were being OOMKilled and silently restarted by Kubernetes multiple
times a day without triggering any alert.

## Impact

- No customer-facing outage (Kubernetes restarted pods automatically,
  and the service is stateless and horizontally scaled)
- Elevated tail latency (p99) during the seconds around each restart,
  as in-flight events on the killed pod were redelivered
- Estimated 40-60 silent OOMKill-and-restart cycles across the fleet
  before detection

## Timeline (all times UTC, dates relative)

- **Day 0** — A caching layer is added to `event-processor` to reduce
  duplicate downstream API calls; code review approved, unit tests
  pass, canary deploy looks healthy
- **Day 0–8** — Memory usage per pod climbs slowly (~15MB/hour) because
  the new cache has no eviction policy or TTL — entries accumulate
  indefinitely
- **Day 2 onward** — Individual pods begin hitting their memory limit
  and getting OOMKilled roughly once every 18-30 hours (varies with
  traffic); Kubernetes restarts them automatically per the deployment's
  restart policy
- **Day 9, 11:40** — An engineer investigating unrelated p99 latency
  noise notices `kubectl get pods` shows unusually high restart counts
  on `event-processor` pods and starts digging
- **Day 9, 12:15** — `kubectl describe pod` confirms `OOMKilled` as the
  last termination reason across multiple pods; heap dumps taken from a
  pod nearing its limit show the cache growing unbounded

## Root Cause

The new caching layer stored results in an in-memory dictionary with no
maximum size, no TTL, and no eviction policy. Under production traffic
volume, this grew until it exceeded the pod's memory limit, triggering
the kernel OOM killer.

This went undetected because the existing memory alert was configured
as a static threshold ("alert if memory > 90% for 5 minutes"), which is
well-suited to sudden spikes but not to a slow creep that gets reset
every time Kubernetes restarts the pod — each individual pod's memory
usage looked "normal" again within seconds of restarting, so the
threshold-based alert never had a sustained 5-minute window to fire.
Pod restart-count itself had no alert wired to it at all.

## Detection

Not detected by any automated alert — found via manual investigation
into unrelated latency noise, 9 days after the leak was introduced.

## Resolution

Immediate mitigation: added an LRU eviction policy with a max entry
count and a 10-minute TTL to the cache, and rolled out via standard
deploy. Memory usage stabilized within one full restart cycle across
the fleet.

## Action Items

- [x] Add TTL + max-size eviction to the cache (immediate fix)
- [x] Add a dedicated alert on pod restart-count / OOMKill rate,
      independent of the point-in-time memory threshold alert
- [ ] Add a memory-growth-rate alert (e.g. "memory increased >20% over
      6 hours") to catch slow leaks specifically, not just absolute
      thresholds
- [ ] Add a checklist item to the code review template for any change
      that introduces new in-memory caching: "does this have bounded
      size and/or a TTL?"
