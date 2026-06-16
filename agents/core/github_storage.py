"""
GitHub-backed artifact storage.

Reads from env:
  GITHUB_TOKEN   — PAT with repo write access
  ARTIFACTS_PATH — https://github.com/{owner}/{repo}/{prefix}
                   e.g. https://github.com/bibhu2020/media/stockadvisor
"""
import base64
import os
import re
from pathlib import Path

import requests

_SESSION = requests.Session()


def _cfg() -> tuple[str, str, str]:
    """Return (owner, repo, prefix) parsed from ARTIFACTS_PATH."""
    url = os.getenv("ARTIFACTS_PATH", "")
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/?(.*)", url)
    if not m:
        raise ValueError(f"Cannot parse ARTIFACTS_PATH={url!r}. "
                         "Expected https://github.com/<owner>/<repo>/<path>")
    owner  = m.group(1)
    repo   = m.group(2)
    prefix = m.group(3).strip("/")
    return owner, repo, prefix


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN env var is not set")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _api_url(owner: str, repo: str, remote_path: str) -> str:
    return f"https://api.github.com/repos/{owner}/{repo}/contents/{remote_path}"


def upload(local_path: str | Path, subpath: str, branch: str = "main") -> str:
    """
    Upload local_path to GitHub at <prefix>/<subpath>.
    Returns the raw.githubusercontent.com URL.

    subpath examples:
      "reports/2026-06-16-analyst.pdf"
      "retrospectives/2026-06-retrospective.pdf"
    """
    owner, repo, prefix = _cfg()
    remote_path = f"{prefix}/{subpath}".lstrip("/")
    api = _api_url(owner, repo, remote_path)
    hdrs = _headers()

    content_b64 = base64.b64encode(Path(local_path).read_bytes()).decode()

    # Fetch current sha if the file already exists (needed for update)
    sha: str | None = None
    r = _SESSION.get(api, headers=hdrs, timeout=15)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload: dict = {
        "message": f"artifact: {subpath}",
        "content": content_b64,
        "branch":  branch,
    }
    if sha:
        payload["sha"] = sha

    r = _SESSION.put(api, headers=hdrs, json=payload, timeout=60)
    r.raise_for_status()

    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{remote_path}"
    print(f"[github_storage] uploaded → {raw}")
    return raw


def raw_url(subpath: str, branch: str = "main") -> str:
    """Return the raw URL for a subpath without uploading."""
    owner, repo, prefix = _cfg()
    remote_path = f"{prefix}/{subpath}".lstrip("/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{remote_path}"


def is_configured() -> bool:
    """True when both env vars are present."""
    return bool(os.getenv("GITHUB_TOKEN")) and bool(os.getenv("ARTIFACTS_PATH"))
