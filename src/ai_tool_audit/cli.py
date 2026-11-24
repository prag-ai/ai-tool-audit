"""명령 진입점: ai-tool-audit scan | baseline | files | rules | mcp  (한국어·영어)"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from . import baseline as bl
from .discover import DISCOVERERS, discover_all
from .discover.common import SHELL_FILES
from .engine import load_incidents, load_rules, run_all
from .i18n import detect_lang
from .model import SEVERITIES, Context
from .redact import display_path
from .report import itext, rtext, sev, terminal, to_json
from .report.document import markdown as to_md
from .report.ledger import html as to_html

S = {
    "ko": {"bl_saved": "MCP 서버 {n}개의 기준선을 저장했습니다: {p}",
           "bl_none": "저장된 기준선이 없습니다. 먼저 ai-tool-audit baseline save 를 실행하세요.",
           "bl_cmp": "기준선 {t} 와 비교", "added": "새로 생김", "changed": "바뀜", "removed": "사라짐", "before": "이전",
           "bl_same": "  달라진 MCP 서버가 없습니다.",
           "files_h": "점검할 때 읽는 파일(있는 경우에만 읽음):", "shell": "셸 시작 파일·패턴 일치만",
           "files_1": "이 밖에 설치 버전 확인용 package.json(npm 전역 폴더)과 설치 폴더 이름을 읽습니다.",
           "files_2": "읽지 않는 것: 대화·명령 기록, 셸 히스토리, 프로젝트 소스, 자격 증명 파일 내용(권한만 확인).",
           "no_rule": "규칙 없음: {id}", "why": "이유", "fix": "조치", "inc": "사건", "doc": "문서",
           "ent": " (기업)", "rev": " (확인 필요)", "n_rules": "규칙 {n}개", "확정": "확정", "검토필요": "검토필요"},
    "en": {"bl_saved": "Saved a baseline of {n} MCP servers: {p}",
           "bl_none": "No saved baseline. Run ai-tool-audit baseline save first.",
           "bl_cmp": "Compared with the baseline saved at {t}", "added": "added", "changed": "changed", "removed": "removed",
           "before": "before", "bl_same": "  No MCP server has changed.",
           "files_h": "Files read during a scan (only if they exist):", "shell": "shell startup file, pattern match only",
           "files_1": "It also reads package.json in global npm folders and install folder names, to determine versions.",
           "files_2": "Not read: chat/command logs, shell history, project source, credential file contents (permissions only).",
           "no_rule": "No such rule: {id}", "why": "Why", "fix": "Fix", "inc": "Incident", "doc": "Docs",
           "ent": " (enterprise)", "rev": " (needs review)", "n_rules": "{n} rules", "확정": "confirmed", "검토필요": "needs review"},
}


def _lang(a, ctx: Context | None = None) -> str:
    if getattr(a, "lang", "auto") != "auto":
        return a.lang
    ctx = ctx or Context.current()
    return detect_lang(ctx.env, ctx.home, ctx.os)


def cmd_scan(a) -> int:
    ctx = Context.current(repos=a.repo, enterprise=a.enterprise)
    ctx.baseline_path = Path(a.baseline).expanduser() if a.baseline else None
    discover_all(ctx)
    rules = load_rules()
    findings = run_all(ctx, rules)
    rmap, incs = {r["id"]: r for r in rules}, load_incidents()
    lang = _lang(a, ctx)
    for opt, fn in ((a.md, to_md), (a.html, to_html)):
        if opt:
            Path(opt).write_text(fn(ctx, findings, rmap, incs, lang=lang), encoding="utf-8")
    if a.json:
        out = to_json(ctx, findings)
        if a.json == "-":
            print(out)
        else:
            Path(a.json).write_text(out + "\n", encoding="utf-8")
    if a.json != "-":
        print(terminal(ctx, findings, rmap, incs, lang=lang))
    if a.fail_on:
        limit = SEVERITIES.index({"high": "높음", "medium": "중간", "low": "낮음"}.get(a.fail_on, a.fail_on))
        if any(f.status == "확정" and SEVERITIES.index(f.severity) <= limit for f in findings):
            return 1
    return 0


def cmd_baseline(a) -> int:
    ctx = Context.current(repos=a.repo)
    ctx.baseline_path = Path(a.file).expanduser() if a.file else None
    discover_all(ctx)
    t = S[_lang(a, ctx)]
    if a.action == "save":
        p = bl.save(ctx, ctx.baseline_path)
        print(t["bl_saved"].format(n=len(bl.snapshot(ctx)), p=display_path(p, ctx.home)))
        return 0
    base = bl.load(ctx, ctx.baseline_path)
    if not base:
        print(t["bl_none"])
        return 2
    d = bl.diff(ctx, base)
    print(t["bl_cmp"].format(t=base.get("saved_at", "?")))
    for kind in ("added", "changed", "removed"):
        for s in d[kind]:
            extra = f"  ← {t['before']}: {s['before']}" if kind == "changed" else ""
            print(f"  [{t[kind]}] {s['name']} ({s['file']}): {s['how']}{extra}")
    if not any(d.values()):
        print(t["bl_same"])
    return 1 if (d["added"] or d["changed"]) else 0


def cmd_files(a) -> int:
    """읽을 파일 목록만 보여 준다(아무 파일도 열지 않는다)."""
    ctx = Context.current(repos=a.repo, enterprise=a.enterprise)
    t = S[_lang(a, ctx)]
    h = lambda p: display_path(p, ctx.home)
    print(t["files_h"])
    for d in DISCOVERERS:
        for item in d.candidate_files(ctx):
            path = next(x for x in item if isinstance(x, Path))
            tool = getattr(d, "TOOL", None) or item[0]
            layer = item[2] if not hasattr(d, "TOOL") else item[1]
            print(f"  [{tool}/{layer}] {h(path)}")
    for n in SHELL_FILES:
        print(f"  [{t['shell']}] ~/{n}")
    print(t["files_1"])
    print(t["files_2"])
    return 0


def cmd_rules(a) -> int:
    lang = _lang(a)
    t = S[lang]
    rules = load_rules()
    incidents = load_incidents()
    if a.id:
        r = next((r for r in rules if r["id"] == a.id.upper()), None)
        if not r:
            print(t["no_rule"].format(id=a.id), file=sys.stderr)
            return 2
        print(f"{r['id']} [{sev(r['severity'], lang)}·{t[r['status']]}] {rtext(r, 'title', lang)}")
        print(f"{t['why']}: {rtext(r, 'why', lang)}")
        print(f"{t['fix']}: {rtext(r, 'fix', lang)}")
        for i in r.get("incidents", []):
            inc = incidents[i]
            print(f"{t['inc']}: {inc['date']} {itext(inc, 'title', lang)} — {itext(inc, 'summary', lang)} {inc['url']}")
        for u in r.get("refs", []):
            print(f"{t['doc']}: {u}")
        return 0
    for r in rules:
        flag = t["ent"] if r.get("enterprise") else ""
        st = "" if r["status"] == "확정" else t["rev"]
        print(f"{r['id']:13} {sev(r['severity'], lang):6} {rtext(r, 'title', lang)}{flag}{st}")
    print("\n" + t["n_rules"].format(n=len(rules)))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ai-tool-audit",
                                description="개발자 PC의 AI 도구 설정을 읽기 전용으로 점검합니다. / "
                                            "Read-only audit of AI coding tool settings on a developer machine.")
    p.add_argument("--version", action="version", version=f"ai-tool-audit {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--repo", action="append", default=[], metavar="PATH",
                        help="함께 점검할 저장소 폴더 / repository to include (repeatable)")
        sp.add_argument("--enterprise", action="store_true", help="기업 관리 정책 규칙도 켠다 / also check managed-policy rules")

    def lang_opt(sp):
        sp.add_argument("--lang", choices=["auto", "ko", "en"], default="auto",
                        help="출력 언어(auto: 시스템 언어) / output language (auto: system language)")

    s = sub.add_parser("scan", help="점검 / audit this machine")
    common(s)
    lang_opt(s)
    s.add_argument("--json", metavar="FILE", help="JSON 저장('-'이면 표준 출력) / write JSON ('-' for stdout)")
    s.add_argument("--md", metavar="FILE", help="Markdown 보고서 / Markdown report")
    s.add_argument("--html", metavar="FILE",
                   help="HTML 보고서(한·영 함께, 브라우저 언어로 표시) / HTML report (Korean + English, shown in the browser's language)")
    s.add_argument("--fail-on", choices=SEVERITIES[:3] + ["high", "medium", "low"],
                   help="이 심각도 이상이 있으면 종료 코드 1 / exit 1 at or above this severity")
    s.add_argument("--baseline", metavar="FILE", help="MCP 기준선 파일 / MCP baseline file (default ~/.ai-tool-audit/baseline.json)")
    s.set_defaults(fn=cmd_scan)

    b = sub.add_parser("baseline", help="MCP 서버 기준선 저장·비교 / save or diff the MCP server baseline")
    b.add_argument("action", choices=["save", "diff"])
    b.add_argument("--file", metavar="FILE", help="기준선 파일 / baseline file")
    b.add_argument("--repo", action="append", default=[], metavar="PATH")
    lang_opt(b)
    b.set_defaults(fn=cmd_baseline)

    f = sub.add_parser("files", help="읽게 될 파일 목록 / list files that would be read")
    common(f)
    lang_opt(f)
    f.set_defaults(fn=cmd_files)

    r = sub.add_parser("rules", help="규칙 목록·설명 / list or explain rules")
    r.add_argument("id", nargs="?", help="규칙 ID / rule ID (e.g. CC-PERM-001)")
    lang_opt(r)
    r.set_defaults(fn=cmd_rules)

    m = sub.add_parser("mcp", help="MCP 서버로 실행(stdio) / run as an MCP server over stdio")
    m.set_defaults(fn=lambda a: __import__("ai_tool_audit.mcp_server", fromlist=["serve"]).serve())

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
