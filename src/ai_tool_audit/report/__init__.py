"""결과 출력: 터미널(한국어·영어), JSON(두 언어 모두 담음)."""
from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime

from .. import __version__
from ..checks import mcp_servers
from ..model import SEVERITIES, Context, Finding
from ..i18n import pick
from ..redact import display_path, redact_args, redact_url

TOOL_NAMES = {"claude-code": "Claude Code", "codex": "Codex CLI", "gemini": "Gemini CLI", "claude-desktop": "Claude Desktop",
              "vscode": "VS Code", "cursor": "Cursor", "공통": "공통"}
SEV_EN = {"높음": "High", "중간": "Medium", "낮음": "Low", "정보": "Info"}

UI = {
    "ko": {"head": "AI 도구 설정 점검 (읽기 전용, 외부 전송 없음)", "tools": "찾은 AI 도구", "none": "(없음)",
           "nover": "(버전 확인 안 됨)", "inactive": "(다른 설치, 실행되지 않음)", "mcp": "등록된 MCP 서버 {n}개",
           "unread": "읽지 못한 설정 파일", "result": "결과", "review_n": "확인 필요 {n}",
           "review": "확인이 필요한 설정 (공식 문서로 확정하지 못한 규칙)", "loc": "위치", "ev": "내용", "note": "참고",
           "why": "이유", "fix": "조치", "inc": "사건", "files_n": "읽은 파일 {n}개 — 전체 목록은 --json 결과의 read_files에 있습니다.",
           "foot": "대화 기록·셸 히스토리·프로젝트 소스는 읽지 않았습니다. 비밀값은 앞 4글자만 표시합니다.", "common": "공통"},
    "en": {"head": "AI tool configuration audit (read-only, nothing sent anywhere)", "tools": "AI tools found", "none": "(none)",
           "nover": "(version unknown)", "inactive": "(another install, not on PATH)", "mcp": "{n} MCP servers registered",
           "unread": "Config files that could not be parsed", "result": "Result", "review_n": "needs review {n}",
           "review": "Settings that need review (rules not confirmed by official docs)", "loc": "Where", "ev": "Found",
           "note": "Note", "why": "Why", "fix": "Fix", "inc": "Incident",
           "files_n": "Read {n} files — the full list is in read_files of the --json output.",
           "foot": "Chat logs, shell history and project source were not read. Secrets show only their first 4 characters.",
           "common": "Common"},
}


def ui(lang: str, key: str, **kw) -> str:
    return UI[lang][key].format(**kw)


def sev(s: str, lang: str) -> str:
    return SEV_EN.get(s, s) if lang == "en" else s


def rtext(rule: dict, field: str, lang: str) -> str:
    return (rule.get(f"{field}_en") if lang == "en" else None) or rule.get(field, "")


def itext(inc: dict, field: str, lang: str) -> str:
    return (inc.get(f"{field}_en") if lang == "en" else None) or inc.get(field, "")


def tool_name(t: str, lang: str = "ko") -> str:
    base = t.split("-ext:")[0]
    if base == "공통":
        return UI[lang]["common"]
    return TOOL_NAMES.get(base, t)


def server_how(srv: dict, ctx: Context, limit: int = 90) -> str:
    """MCP 서버 실행 방법(명령+인자 또는 주소). 비밀값·홈 경로를 먼저 가린 뒤 자른다."""
    from ..checks import server_url
    _, url = server_url(srv)
    how = redact_url(url) if url else " ".join([str(srv.get("command", ""))] + redact_args(srv.get("args"))[:4])
    how = scrub(how, ctx)
    return how if len(how) <= limit else how[: limit - 1] + "…"


def _sorted(findings):
    order = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda f: (f.status != "확정", order.get(f.severity, 9), f.rule, str(f.path), f.line or 0))


def fingerprint(f: Finding, ctx: Context) -> str:
    raw = f"{f.rule}|{display_path(f.path, ctx.home)}|{f.pointer or f.line}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def scrub(text: str, ctx: Context) -> str:
    """출력 마지막 단계: 홈 경로(실제 경로·심볼릭 링크 해석 경로 모두)를 ~로 바꾼다."""
    pairs = []
    for r in ctx.repos:   # 홈 밖 저장소는 저장소 이름부터 보인다
        for form in {str(r), str(r.resolve())}:
            if not form.startswith(str(ctx.home)) and not form.startswith(str(ctx.home.resolve())):
                pairs.append((form, r.name))
    for h in {str(ctx.home), str(ctx.home.resolve())}:
        pairs.append((h, "~"))
    for old, new in sorted(pairs, key=lambda x: len(x[0]), reverse=True):
        text = text.replace(old, new)
    return text


def terminal(ctx: Context, findings: list[Finding], rules: dict[str, dict], incidents: dict[str, dict],
             lang: str = "ko") -> str:
    h = lambda p: display_path(p, ctx.home)
    u = lambda k, **kw: ui(lang, k, **kw)
    L: list[str] = []
    L.append(f"ai-tool-audit {__version__} — {u('head')}")
    L.append("")
    L.append(f"■ {u('tools')}")
    if not ctx.tools:
        L.append(f"  {u('none')}")
    for t in ctx.tools:
        mark = "" if t.active else f"  {u('inactive')}"
        L.append(f"  - {pick(t.name, lang)} {t.version or u('nover')}  [{h(t.source)}]{mark}")
    servers = list(mcp_servers(ctx))
    if servers:
        L.append("")
        L.append(f"■ {u('mcp', n=len(servers))}")
        for doc, name, srv, _ in servers:
            L.append(f"  - {name} ({tool_name(doc.tool, lang)}, {h(doc.path)}): {server_how(srv, ctx, 70)}")
    errs = [d for d in ctx.docs if d.error]
    if errs:
        L.append("")
        L.append(f"■ {u('unread')}")
        for d in errs:
            L.append(f"  - {h(d.path)}: {d.error}")

    confirmed = [f for f in findings if f.status == "확정"]
    review = [f for f in findings if f.status != "확정"]
    counts = {s: sum(1 for f in confirmed if f.severity == s) for s in SEVERITIES}
    L.append("")
    L.append(f"■ {u('result')}: " + " · ".join(f"{sev(s, lang)} {counts[s]}" for s in SEVERITIES) + f" · {u('review_n', n=len(review))}")

    def block(f: Finding):
        r = rules.get(f.rule, {})
        loc = (h(f.path) + (f":{f.line}" if f.line else "")) if f.path else (f.pointer or "-")
        L.append("")
        L.append(f"[{sev(f.severity, lang)}] {f.rule} {rtext(r, 'title', lang) or f.title}")
        L.append(f"  {u('loc')}: {loc}")
        if f.evidence:
            L.append(f"  {u('ev')}: {pick(f.evidence, lang)}")
        if f.note:
            L.append(f"  {u('note')}: {pick(f.note, lang)}")
        L.append(f"  {u('why')}: {rtext(r, 'why', lang)}")
        L.append(f"  {u('fix')}: {rtext(r, 'fix', lang)}")
        for iid in r.get("incidents", []):
            inc = incidents.get(iid)
            if inc:
                L.append(f"  {u('inc')}: {inc['date']} {itext(inc, 'title', lang)} — {inc['url']}")

    for f in _sorted(confirmed):
        block(f)
    if review:
        L.append("")
        L.append(f"■ {u('review')}")
        for f in _sorted(review):
            block(f)

    L.append("")
    L.append(u("files_n", n=len(set(ctx.read_files))))
    L.append(u("foot"))
    return scrub("\n".join(L), ctx)


def to_json(ctx: Context, findings: list[Finding]) -> str:
    h = lambda p: display_path(p, ctx.home)
    host_raw = f"{platform.node()}|{ctx.home.name}"
    doc = {
        "schema": "ai-tool-audit/result/v1",
        "tool_version": __version__,
        "scanned_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": {"id": hashlib.sha256(host_raw.encode()).hexdigest()[:16], "os": ctx.os,
                 "os_version": platform.release()},
        "options": {"enterprise": ctx.enterprise, "repos": [h(r) for r in ctx.repos]},
        "inventory": [{"tool": t.tool, "name": str(t.name), "name_en": pick(t.name, "en"), "version": t.version,
                       "source": h(t.source), "active": t.active} for t in ctx.tools],
        "mcp_servers": [{"tool": d.tool, "name": n, "file": h(d.path),
                         "transport": "http" if s.get("url") else "stdio",
                         "how": server_how(s, ctx, 200)} for d, n, s, _ in mcp_servers(ctx)],
        "findings": [{"rule": f.rule, "severity": f.severity, "severity_en": SEV_EN.get(f.severity), "status": f.status,
                      "tool": f.tool, "title": f.title, "file": h(f.path) if f.path else f.pointer, "line": f.line,
                      "pointer": f.pointer, "evidence": pick(f.evidence, "ko"), "evidence_en": pick(f.evidence, "en"),
                      "note": pick(f.note, "ko"), "note_en": pick(f.note, "en"),
                      "fingerprint": fingerprint(f, ctx)} for f in _sorted(findings)],
        "unreadable": [{"file": h(d.path), "error": d.error} for d in ctx.docs if d.error],
        "read_files": sorted({h(p) for p in ctx.read_files}),
    }
    return scrub(json.dumps(doc, ensure_ascii=False, indent=2), ctx)
