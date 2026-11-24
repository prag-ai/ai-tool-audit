"""rules/*.yaml, data/incidents.yaml → src/ai_tool_audit/data/*.json

점검기 본체는 표준 라이브러리만 쓰므로, YAML은 개발할 때 JSON으로 바꿔 함께 배포한다.
  uv run python scripts/build_rules.py          # 만들기
  uv run python scripts/build_rules.py --check  # 최신인지 확인(시험에서 사용)
"""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/ai_tool_audit/data"
REQUIRED = ["id", "tool", "title", "severity", "detect", "why", "fix"]
SEVERITIES = {"높음", "중간", "낮음", "정보"}


def build() -> dict[str, str]:
    incidents = yaml.safe_load((ROOT / "data/incidents.yaml").read_text(encoding="utf-8"))["incidents"]
    inc_en = yaml.safe_load((ROOT / "data/incidents_en.yaml").read_text(encoding="utf-8"))["incidents"]
    rules_en = yaml.safe_load((ROOT / "rules/en.yaml").read_text(encoding="utf-8"))["rules"]
    for i in incidents:
        assert i["id"] in inc_en, f"data/incidents_en.yaml에 영어 문구 없음: {i['id']}"
        i["title_en"], i["summary_en"] = inc_en[i["id"]]["title"], inc_en[i["id"]]["summary"]
    inc_ids = {i["id"] for i in incidents}
    rules, ids = [], set()
    for f in sorted(p for p in (ROOT / "rules").glob("*.yaml") if p.name != "en.yaml"):
        for r in yaml.safe_load(f.read_text(encoding="utf-8"))["rules"]:
            missing = [k for k in REQUIRED if k not in r]
            assert not missing, f"{f.name} {r.get('id')}: 빠진 필드 {missing}"
            assert re.fullmatch(r"[A-Z]+-[A-Z]+-\d{3}", r["id"]), r["id"]
            assert r["id"] not in ids, f"중복 ID {r['id']}"
            assert r["severity"] in SEVERITIES, r["id"]
            for i in r.get("incidents", []):
                assert i in inc_ids, f"{r['id']}: 없는 사건 {i}"
            if r["detect"]["type"] == "shell_regex":
                re.compile(r["detect"]["regex"])
            r.setdefault("status", "확정")
            assert r["id"] in rules_en, f"rules/en.yaml에 영어 문구 없음: {r['id']}"
            for k in ("title", "why", "fix"):
                r[f"{k}_en"] = rules_en[r["id"]][k]
            r["source"] = f.name
            ids.add(r["id"])
            rules.append(r)
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"
    return {"rules.json": dump({"rules": rules}), "incidents.json": dump({"incidents": incidents}),
            "../../../docs/규칙목록.md": rules_doc(rules, {i["id"]: i for i in incidents})}


TOOL_TITLE = {"claude-code": "Claude Code", "codex": "OpenAI Codex CLI", "gemini": "Google Gemini CLI",
              "claude-desktop": "Claude Desktop", "vscode": "VS Code·Cursor", "cursor": "Cursor", "공통": "공통(MCP·셸 시작 파일·버전)"}


def rules_doc(rules, incidents) -> str:
    """docs/규칙목록.md — 규칙 파일에서 자동으로 만든다(손으로 고치지 않는다)."""
    L = ["# 규칙 목록", "", "> 이 문서는 `scripts/build_rules.py`가 `rules/*.yaml`에서 자동으로 만듭니다. 손으로 고치지 마세요.", "",
         f"규칙 {len(rules)}개. 심각도: **높음** 사람 승인 없이 코드가 돌거나 비밀값이 노출됨 · **중간** 공격 표면을 넓힘 · "
         "**낮음** 권장 미적용 · **정보** 목록. `검토필요`는 공식 문서로 확정하지 못한 규칙이라 \"확인 필요\"로만 보고합니다. "
         "`기업`은 `--enterprise`를 줄 때만 켜집니다.", ""]
    groups = {}
    for r in rules:
        groups.setdefault(r["tool"], []).append(r)
    for tool, rs in groups.items():
        L += [f"## {TOOL_TITLE.get(tool, tool)}", "", "| ID | 심각도 | 내용 | 근거 사건 |", "|---|---|---|---|"]
        for r in rs:
            flags = (" · 검토필요" if r["status"] != "확정" else "") + (" · 기업" if r.get("enterprise") else "")
            incs = ", ".join(f"[{incidents[i]['title']}]({incidents[i]['url']})" for i in r.get("incidents", []))
            L.append(f"| `{r['id']}` | {r['severity']}{flags} | {r['title']} | {incs or '-'} |")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    files = build()
    if "--check" in sys.argv:
        stale = [n for n, t in files.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        if stale:
            sys.exit(f"규칙 JSON이 오래됐습니다: {stale} → scripts/build_rules.py 실행")
        print("규칙 JSON 최신")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for n, t in files.items():
            (OUT / n).resolve().parent.mkdir(parents=True, exist_ok=True)
            (OUT / n).write_text(t, encoding="utf-8")
        print(f"규칙 {len(json.loads(files['rules.json'])['rules'])}개 → {OUT}")
