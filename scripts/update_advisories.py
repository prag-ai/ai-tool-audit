"""관리자 전용: GitHub Advisory Database에서 AI 도구·MCP 패키지의 보안 권고를 받아
src/ai_tool_audit/data/advisories.json 으로 저장한다. (배포되는 점검기는 네트워크를 쓰지 않는다.)

  uv run python scripts/update_advisories.py
  GITHUB_TOKEN 이 있으면 쓰고(호출 한도 완화), 없으면 인증 없이 부른다.
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/ai_tool_audit/data/advisories.json"

# 점검기가 버전을 아는 도구(tool ID → npm 패키지)와 MCP 서버로 흔히 쓰는 패키지
PACKAGES = {
    "@anthropic-ai/claude-code": "claude-code",
    "@openai/codex": "codex",
    "@google/gemini-cli": "gemini",
    "mcp-remote": None,
    "@modelcontextprotocol/inspector": None,
    "@modelcontextprotocol/server-filesystem": None,
    "@modelcontextprotocol/sdk": None,
    "postmark-mcp": None,
}


def fetch(package: str, kind: str) -> list[dict]:
    url = f"https://api.github.com/advisories?ecosystem=npm&affects={urllib.parse.quote(package)}&type={kind}&per_page=100"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "X-GitHub-Api-Version": "2022-11-28",
                                               "User-Agent": "ai-tool-audit-advisory-updater"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> None:
    import urllib.parse  # noqa: F401  (fetch에서 사용)
    out = []
    for pkg, tool in PACKAGES.items():
        seen = set()
        for kind in ("reviewed", "malware"):
            for a in fetch(pkg, kind):
                if a["ghsa_id"] in seen:
                    continue
                seen.add(a["ghsa_id"])
                for v in a.get("vulnerabilities") or []:
                    p = v.get("package") or {}
                    if p.get("ecosystem") != "npm" or p.get("name") != pkg:
                        continue
                    out.append({
                        "package": pkg,
                        "tool": tool,
                        "ghsa": a["ghsa_id"],
                        "cve": a.get("cve_id"),
                        "type": kind,
                        "severity": a.get("severity"),
                        "summary": a.get("summary"),
                        "published": (a.get("published_at") or "")[:10],
                        "vulnerable": v.get("vulnerable_version_range"),
                        "patched": v.get("first_patched_version"),
                        "url": a.get("html_url"),
                    })
        print(f"{pkg}: {len(seen)}건", file=sys.stderr)
    out.sort(key=lambda x: (x["package"], x["published"], x["ghsa"]))
    doc = {"source": "GitHub Advisory Database (https://github.com/advisories)",
           "updated": date.today().isoformat(), "advisories": out}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"권고 {len(out)}건 → {OUT}", file=sys.stderr)


if __name__ == "__main__":
    import urllib.parse
    main()
