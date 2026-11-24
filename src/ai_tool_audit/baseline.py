"""MCP 서버 설정 기준선 — 저장해 두고 다음 점검 때 새로 생긴·바뀐 서버를 찾는다.

서버를 실행하지 않는다. 해시 대상은 실행 명령·인자·주소와 env·headers의 '이름'뿐이다(값은 넣지 않는다).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .checks import mcp_servers, server_url
from .redact import display_path, redact_args, redact_url


def default_path(ctx) -> Path:
    return ctx.home / ".ai-tool-audit" / "baseline.json"


def snapshot(ctx) -> dict[str, dict]:
    out = {}
    for doc, name, srv, ptr in mcp_servers(ctx):
        key = f"{doc.tool}|{display_path(doc.path, ctx.home)}|{ptr}"
        _, url = server_url(srv)
        shape = {
            "command": srv.get("command"),
            "args": [str(a) for a in (srv.get("args") or [])],
            "url": url,
            "env_names": sorted((srv.get("env") or {}).keys()) if isinstance(srv.get("env"), dict) else [],
            "header_names": sorted(k for f in ("headers", "http_headers") if isinstance(srv.get(f), dict) for k in srv[f]),
        }
        digest = hashlib.sha256(json.dumps(shape, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        from .report import server_how
        out[key] = {"tool": doc.tool, "name": name, "file": display_path(doc.path, ctx.home), "sha256": digest,
                    "how": server_how(srv, ctx, 120)}
    return out


def save(ctx, path: Path | None = None) -> Path:
    path = path or default_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"schema": "ai-tool-audit/baseline/v1", "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
           "servers": snapshot(ctx)}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def load(ctx, path: Path | None = None) -> dict | None:
    path = path or default_path(ctx)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def diff(ctx, base: dict) -> dict[str, list[dict]]:
    now = snapshot(ctx)
    old = base.get("servers", {})
    return {
        "added": [now[k] for k in now if k not in old],
        "changed": [now[k] | {"before": old[k]["how"]} for k in now if k in old and old[k]["sha256"] != now[k]["sha256"]],
        "removed": [old[k] for k in old if k not in now],
    }
