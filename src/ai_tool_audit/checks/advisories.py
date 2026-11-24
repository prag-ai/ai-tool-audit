"""설치 버전 ↔ 공개 보안 권고(GitHub Advisory Database, 도구에 포함된 사본) 대조."""
from __future__ import annotations

import json
import re
from importlib import resources

from . import versions

TOOL_PACKAGE = {"claude-code": "@anthropic-ai/claude-code", "codex": "@openai/codex", "gemini": "@google/gemini-cli"}
SEV = {"critical": "높음", "high": "높음", "moderate": "중간", "medium": "중간", "low": "낮음"}
SEV_ORDER = ["critical", "high", "moderate", "medium", "low", None]


def load() -> dict:
    text = resources.files("ai_tool_audit.data").joinpath("advisories.json").read_text(encoding="utf-8")
    return json.loads(text)


def matching(package: str, version: str, data: dict | None = None) -> list[dict]:
    data = data or load()
    return [a for a in data["advisories"] if a["package"] == package and versions.in_range(version, a["vulnerable"])]


def summarize(hits: list[dict]) -> tuple[str, str | None, list[str]]:
    """(심각도, 올려야 할 최소 버전, 대표 권고 ID 목록)"""
    worst = min(hits, key=lambda a: SEV_ORDER.index(a["severity"]) if a["severity"] in SEV_ORDER else 9)["severity"]
    patched = [a["patched"] for a in hits if a.get("patched")]
    target = max(patched, key=versions.parse) if patched else None
    ids = []
    for a in sorted(hits, key=lambda a: SEV_ORDER.index(a["severity"]) if a["severity"] in SEV_ORDER else 9):
        ids.append(a.get("cve") or a["ghsa"])
    return SEV.get(worst, "중간"), target, ids


NPM_PINNED = re.compile(r"^(@?[^@\s]+)@(\d+\.\d+\.\d+[^\s]*)$")
