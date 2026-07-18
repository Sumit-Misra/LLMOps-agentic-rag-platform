"""
Loaders for the two source document sets:
  1. Public cloud/infra docs (currently: Kubernetes docs pulled via
     scripts/fetch_cloud_docs.py)
  2. Self-authored incident postmortems

Both just read whatever's sitting in data/raw/ -- fetching/authoring the
content itself happened in a separate step, not here.
"""

from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

# Maps a downloaded filename back to its public kubernetes.io URL, so
# retrieved chunks can cite a real, clickable source instead of just a
# local filename. Derived from the same repo paths used in
# scripts/fetch_cloud_docs.py (content/en/docs/X.md -> kubernetes.io/docs/X/).
_K8S_DOC_URLS = {
    "pod-lifecycle.md": "https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/",
    "probes.md": "https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/",
    "deployments.md": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
    "services.md": "https://kubernetes.io/docs/concepts/services-networking/service/",
    "resource-limits.md": "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    "horizontal-pod-autoscaling.md": "https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/",
    "configmaps.md": "https://kubernetes.io/docs/concepts/configuration/configmap/",
    "init-containers.md": "https://kubernetes.io/docs/concepts/workloads/pods/init-containers/",
    "nodes.md": "https://kubernetes.io/docs/concepts/architecture/nodes/",
    "pod-priority-preemption.md": "https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/",
}


@dataclass
class RawDocument:
    source_type: str  # "cloud_docs" | "postmortem"
    source_name: str
    source_url: str | None
    content: str


def load_cloud_docs() -> list[RawDocument]:
    docs = []
    for path in sorted((DATA_DIR / "cloud_docs").glob("*.md")):
        docs.append(
            RawDocument(
                source_type="cloud_docs",
                source_name=path.name,
                source_url=_K8S_DOC_URLS.get(path.name),
                content=path.read_text(encoding="utf-8"),
            )
        )
    return docs


def load_postmortems() -> list[RawDocument]:
    docs = []
    for path in sorted((DATA_DIR / "postmortems").glob("*.md")):
        docs.append(
            RawDocument(
                source_type="postmortem",
                source_name=path.name,
                source_url=None,
                content=path.read_text(encoding="utf-8"),
            )
        )
    return docs


def load_all_documents() -> list[RawDocument]:
    return load_cloud_docs() + load_postmortems()