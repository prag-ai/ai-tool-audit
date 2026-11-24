"""Markdown 보고서(한국어·영어). HTML 보고서는 ledger.py."""
from __future__ import annotations

from datetime import datetime

from .. import __version__
from ..checks import mcp_servers
from ..i18n import pick
from ..model import SEVERITIES, Context, Finding
from ..redact import display_path
from . import _sorted, itext, rtext, scrub, server_how, sev, tool_name

M = {
    "ko": {"title": "AI 도구 설정 점검 보고서", "when": "점검 시각", "how": "방식: 설정 파일을 읽기만 했습니다. 아무것도 바꾸거나 밖으로 보내지 않았습니다.",
           "sum": "요약", "review": "확인 필요", "first": "먼저 고칠 것", "tools": "찾은 AI 도구", "tool": "도구", "ver": "버전",
           "where": "위치", "inactive": " (실행되지 않는 다른 설치)", "mcp": "등록된 MCP 서버 ({n}개)", "name": "이름", "cfg": "설정 파일",
           "cmd": "실행·주소", "rule": "규칙", "found": "내용", "note": "참고", "why": "왜 위험한가", "fix": "고치는 법", "inc": "근거 사건",
           "doc": "문서", "findings": "발견 항목", "review_h": "확인이 필요한 설정",
           "review_p": "공식 문서로 확정하지 못한 규칙입니다. 위험으로 단정하지 않고 확인을 권합니다.", "read": "이 점검이 읽은 파일",
           "foot1": "대화 기록·셸 히스토리·프로젝트 소스는 읽지 않았습니다. 비밀값은 앞 4글자만 표시했습니다.",
           "foot2": "이 보고서에는 PC의 약점 위치가 들어 있습니다. 필요한 사람만 볼 수 있게 보관하세요."},
    "en": {"title": "AI Tool Configuration Audit", "when": "Scanned at", "how": "Method: configuration files were only read. Nothing was changed or sent anywhere.",
           "sum": "Summary", "review": "Needs review", "first": "Fix these first", "tools": "AI tools found", "tool": "Tool", "ver": "Version",
           "where": "Location", "inactive": " (another install, not on PATH)", "mcp": "MCP servers registered ({n})", "name": "Name",
           "cfg": "Config file", "cmd": "Command / URL", "rule": "Rule", "found": "Found", "note": "Note", "why": "Why it matters",
           "fix": "How to fix", "inc": "Incident", "doc": "Docs", "findings": "Findings", "review_h": "Settings that need review",
           "review_p": "These rules could not be confirmed against official documentation, so they are not reported as risks. Please review them.",
           "read": "Files read by this scan",
           "foot1": "Chat logs, shell history and project source were not read. Secrets show only their first 4 characters.",
           "foot2": "This report lists where the machine is weak. Keep it where only the people who need it can see it."},
}


def _loc(f: Finding, ctx: Context) -> str:
    if f.path is None:
        return f.pointer or "-"
    return display_path(f.path, ctx.home) + (f":{f.line}" if f.line else "")


def _top(findings, n=5):
    order = {s: i for i, s in enumerate(SEVERITIES)}
    seen, out = set(), []
    for f in sorted([f for f in findings if f.status == "확정"], key=lambda f: order[f.severity]):
        if f.rule in seen or f.severity == "정보":
            continue
        seen.add(f.rule)
        out.append(f)
        if len(out) == n:
            break
    return out


def markdown(ctx: Context, findings: list[Finding], rules: dict, incidents: dict, lang: str = "ko") -> str:
    t = M[lang]
    title = lambda f: rtext(rules.get(f.rule, {}), "title", lang) or f.title
    conf = [f for f in findings if f.status == "확정"]
    review = [f for f in findings if f.status != "확정"]
    cnt = {s: sum(1 for f in conf if f.severity == s) for s in SEVERITIES}
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    L = [f"# {t['title']}", "", f"- {t['when']}: {now}  ·  ai-tool-audit {__version__}", f"- {t['how']}", "",
         f"## {t['sum']}", "",
         "| " + " | ".join(sev(s, lang) for s in SEVERITIES) + f" | {t['review']} |", "|---|---|---|---|---|",
         "| " + " | ".join(str(cnt[s]) for s in SEVERITIES) + f" | {len(review)} |", ""]
    top = _top(findings)
    if top:
        L += [f"**{t['first']}**", ""]
        L += [f"{i}. [{sev(f.severity, lang)}] {title(f)} — `{_loc(f, ctx)}`" for i, f in enumerate(top, 1)]
        L.append("")
    L += [f"## {t['tools']}", "", f"| {t['tool']} | {t['ver']} | {t['where']} |", "|---|---|---|"]
    for x in ctx.tools:
        L.append(f"| {pick(x.name, lang)}{t['inactive'] if not x.active else ''} | {x.version or '-'} | `{display_path(x.source, ctx.home)}` |")
    servers = list(mcp_servers(ctx))
    if servers:
        L += ["", f"## {t['mcp'].format(n=len(servers))}", "", f"| {t['name']} | {t['tool']} | {t['cfg']} | {t['cmd']} |", "|---|---|---|---|"]
        L += [f"| {n} | {tool_name(d.tool, lang)} | `{display_path(d.path, ctx.home)}` | `{server_how(s, ctx, 80)}` |" for d, n, s, _ in servers]

    def block(f: Finding):
        r = rules.get(f.rule, {})
        L.extend(["", f"### [{sev(f.severity, lang)}] {title(f)}", "",
                  f"- {t['rule']}: `{f.rule}`  ·  {t['tool']}: {tool_name(f.tool, lang)}", f"- {t['where']}: `{_loc(f, ctx)}`"])
        if f.evidence:
            L.append(f"- {t['found']}: `{pick(f.evidence, lang)}`")
        if f.note:
            L.append(f"- {t['note']}: {pick(f.note, lang)}")
        L.append(f"- {t['why']}: {rtext(r, 'why', lang)}")
        L.append(f"- {t['fix']}: {rtext(r, 'fix', lang)}")
        for iid in r.get("incidents", []):
            inc = incidents.get(iid)
            if inc:
                L.append(f"- {t['inc']}: {inc['date']} [{itext(inc, 'title', lang)}]({inc['url']}) — {itext(inc, 'summary', lang)}")
        for u in r.get("refs", []):
            L.append(f"- {t['doc']}: <{u}>")

    if conf:
        L += ["", f"## {t['findings']}"]
        for f in _sorted(conf):
            block(f)
    if review:
        L += ["", f"## {t['review_h']}", "", t["review_p"]]
        for f in _sorted(review):
            block(f)
    L += ["", f"## {t['read']}", ""]
    L += [f"- `{display_path(p, ctx.home)}`" for p in sorted(set(ctx.read_files), key=str)]
    L += ["", t["foot1"], t["foot2"], ""]
    return scrub("\n".join(L), ctx)
