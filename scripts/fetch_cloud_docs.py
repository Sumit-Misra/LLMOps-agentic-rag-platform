"""
Downloads a curated set of public Kubernetes documentation pages
(Markdown, straight from the official kubernetes/website GitHub repo,
CC BY 4.0 licensed) into data/raw/cloud_docs/.

This is a one-time/occasional script, not part of the runtime app --
run it manually whenever you want to (re)populate the raw doc corpus.
"""

import sys
import time
from pathlib import Path

import requests

RAW_BASE = "https://raw.githubusercontent.com/kubernetes/website/main/"

# (output filename, path within the kubernetes/website repo)
PAGES = [
    ("pod-lifecycle.md", "content/en/docs/concepts/workloads/pods/pod-lifecycle.md"),
    ("probes.md", "content/en/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes.md"),
    ("deployments.md", "content/en/docs/concepts/workloads/controllers/deployment.md"),
    ("services.md", "content/en/docs/concepts/services-networking/service.md"),
    ("resource-limits.md", "content/en/docs/concepts/configuration/manage-resources-containers.md"),
    ("horizontal-pod-autoscaling.md", "content/en/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough.md"),
    ("configmaps.md", "content/en/docs/concepts/configuration/configmap.md"),
    ("init-containers.md", "content/en/docs/concepts/workloads/pods/init-containers.md"),
    ("nodes.md", "content/en/docs/concepts/architecture/nodes.md"),
    ("pod-priority-preemption.md", "content/en/docs/concepts/scheduling-eviction/pod-priority-preemption.md"),
]

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "cloud_docs"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, []

    for filename, repo_path in PAGES:
        url = RAW_BASE + repo_path
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"FAILED  {filename}  ({e})")
            failed.append(filename)
            continue

        out_path = OUT_DIR / filename
        out_path.write_text(resp.text, encoding="utf-8")
        print(f"OK      {filename}  ({len(resp.text):,} chars)")
        ok += 1
        time.sleep(0.3)  # be polite to GitHub's raw CDN

    print(f"\n{ok}/{len(PAGES)} pages downloaded to {OUT_DIR}")
    if failed:
        print(f"Failed: {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()