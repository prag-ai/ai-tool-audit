"""B안 HTML 보고서 — '점검 기록지'. 발견 항목을 파일 단위로 묶는다(고치는 단위가 파일이므로).

외부 글꼴·스크립트를 불러오지 않는다(보고서를 여는 순간에도 외부 요청이 생기지 않게).
"""
from __future__ import annotations

import html as H
from collections import OrderedDict
from datetime import datetime

from .. import __version__
from ..checks import mcp_servers
from ..model import SEVERITIES, Context, Finding
from ..redact import display_path
from ..i18n import pick
from . import _sorted, itext, rtext, scrub, server_how, sev, tool_name

CSS = """
:root{
  --paper:#f6f6f4; --sheet:#ffffff; --ink:#15171a; --sub:#5d636c; --faint:#8a9098; --rule:#dcdedf; --rule2:#ecedee;
  --hi:#c23a22; --mid:#a8610a; --lo:#3d5b8a; --info:#7a8089;
  --mono: ui-monospace, "SF Mono", "D2Coding", Menlo, Consolas, monospace;
  --sans: Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", system-ui, sans-serif;
}
*{box-sizing:border-box} html{background:var(--paper)} body{margin:0;color:var(--ink);font:15px/1.6 var(--sans)}
.sheet{max-width:1120px;margin:28px auto;background:var(--sheet);border:1px solid var(--rule);padding:40px 44px 56px}
header{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;padding-bottom:20px;border-bottom:2px solid var(--ink)}
h1{font-size:28px;line-height:1.2;margin:0;font-weight:700;letter-spacing:-.01em}
.lead{margin:6px 0 0;color:var(--sub)}
.meta{font:12.5px/1.7 var(--mono);color:var(--sub);text-align:right;white-space:nowrap}
.strip{margin:22px 0 6px;display:flex;height:10px;border:1px solid var(--rule)}
.strip i{display:block;height:100%}
.legend{display:flex;gap:22px;flex-wrap:wrap;font-size:13.5px;color:var(--sub)}
.legend b{color:var(--ink);font-weight:700;margin-right:4px;font-variant-numeric:tabular-nums}
.sw{display:inline-block;width:9px;height:9px;margin-right:6px;vertical-align:1px}
h2{font-size:17px;margin:38px 0 12px;font-weight:700}
.first{margin:0;padding:0;list-style:none;counter-reset:n;border-top:1px solid var(--rule)}
.first li{counter-increment:n;display:grid;grid-template-columns:28px 70px 1fr;gap:10px;padding:10px 0;border-bottom:1px solid var(--rule2)}
.first li::before{content:counter(n);font:600 13px var(--mono);color:var(--faint);padding-top:2px}
.sev{font-weight:700;font-size:13.5px}
.s-hi{color:var(--hi)}.s-mid{color:var(--mid)}.s-lo{color:var(--lo)}.s-info{color:var(--info)}
.path{font:13px var(--mono);color:var(--sub);word-break:break-all}
.grid{display:grid;grid-template-columns:270px 1fr;gap:36px;margin-top:8px}
nav{position:sticky;top:16px;align-self:start;font-size:13.5px;max-height:calc(100vh - 32px);overflow:auto}
nav a{display:grid;grid-template-columns:1fr auto;gap:8px;padding:5px 0;color:var(--ink);text-decoration:none;border-bottom:1px solid var(--rule2)}
nav a:hover .f{text-decoration:underline}
nav .f{font:12.5px var(--mono);word-break:break-all}
nav .c{font:600 12.5px var(--mono)}
.file{margin:0 0 30px}
.file h3{font:600 14px var(--mono);margin:0;padding:8px 0;border-bottom:1px solid var(--ink);display:flex;justify-content:space-between;gap:12px;word-break:break-all}
.file h3 span{color:var(--sub);font-weight:400;white-space:nowrap}
.row{display:grid;grid-template-columns:52px 58px 1fr;gap:12px;padding:12px 0 10px;border-bottom:1px solid var(--rule2)}
.ln{font:12.5px var(--mono);color:var(--faint);text-align:right;padding-top:2px}
.t{font-weight:600}
.id{font:12px var(--mono);color:var(--faint);margin-left:8px;font-weight:400}
.ev{font:13px var(--mono);background:#f3f4f5;padding:2px 6px;display:inline-block;margin-top:4px;word-break:break-all}
.note{margin-top:6px;font-size:14px;color:var(--ink);border-left:2px solid var(--mid);padding-left:10px}
details{margin-top:6px;font-size:14px;color:var(--sub)}
summary{cursor:pointer;color:var(--sub);font-size:13px;list-style:none}
summary::before{content:"＋ ";font-family:var(--mono)} details[open] summary::before{content:"－ "}
details p{margin:6px 0}
details b{color:var(--ink);font-weight:600}
details a{color:var(--lo)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:7px 10px 7px 0;border-bottom:1px solid var(--rule2);vertical-align:top}
th{font-weight:600;color:var(--sub);border-bottom:1px solid var(--ink)}
td.m{font:12.5px var(--mono);color:var(--sub);word-break:break-all}
.review{color:var(--sub);font-size:14px}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--rule);font-size:13px;color:var(--sub)}
footer .m{font:12.5px var(--mono)}
a:focus-visible,summary:focus-visible,button:focus-visible{outline:2px solid var(--lo);outline-offset:2px}
[data-l]{display:none} html[data-lang=ko] [data-l=ko], html[data-lang=en] [data-l=en]{display:block}
.langbar{max-width:1120px;margin:16px auto -12px;display:flex;justify-content:flex-end;gap:2px}
.langbar button{font:13px var(--sans);background:transparent;border:1px solid var(--rule);color:var(--sub);padding:4px 12px;cursor:pointer}
html[data-lang=ko] .langbar [data-set=ko], html[data-lang=en] .langbar [data-set=en]{background:var(--ink);color:#fff;border-color:var(--ink)}
@media (max-width:820px){.sheet{margin:0;border:0;padding:24px 16px}.grid{grid-template-columns:1fr}nav{position:static;max-height:none}
  header{grid-template-columns:1fr}.meta{text-align:left}.row{grid-template-columns:44px 1fr}.row .ln{display:none}}
@media print{.langbar{display:none}html{background:#fff}.sheet{border:0;margin:0}details{display:block}nav{display:none}.grid{grid-template-columns:1fr}}
"""

SEVCLS = {"높음": "hi", "중간": "mid", "낮음": "lo", "정보": "info"}
COLOR = {"높음": "var(--hi)", "중간": "var(--mid)", "낮음": "var(--lo)", "정보": "var(--info)"}

T = {
    "ko": {"title": "AI 도구 설정 점검 기록", "found": "이 PC에서 찾은 AI 도구", "none": "없음", "ro": "읽기 전용 · 외부 전송 없음",
           "strip": "심각도 비율", "review_n": "확인 필요", "files_n": "개 파일", "first": "먼저 고칠 것", "byfile": "파일별 발견 항목",
           "filelist": "파일 목록", "count": "{n}건", "whyfix": "왜 위험한가 · 고치는 법", "why": "왜 위험한가", "fix": "고치는 법",
           "inc": "근거 사건", "doc": "문서", "review": "확인이 필요한 설정",
           "review_p": "공식 문서로 확정하지 못한 규칙입니다. 위험으로 단정하지 않고 확인을 권합니다.",
           "tools": "찾은 AI 도구", "tool": "도구", "ver": "버전", "where": "위치", "inactive": " (실행되지 않는 다른 설치)",
           "mcp": "등록된 MCP 서버 {n}개", "name": "이름", "cfg": "설정 파일", "how": "실행·주소", "whole": "설정 전체",
           "read": "읽은 파일", "foot": "대화 기록·셸 히스토리·프로젝트 소스는 읽지 않았습니다. 비밀값은 앞 4글자만 표시했습니다. "
                                      "이 기록에는 PC의 약점 위치가 들어 있으니 필요한 사람만 볼 수 있게 보관하세요."},
    "en": {"title": "AI Tool Configuration Audit", "found": "AI tools found on this machine", "none": "none",
           "ro": "read-only · nothing sent anywhere", "strip": "severity mix", "review_n": "needs review", "files_n": " files",
           "first": "Fix these first", "byfile": "Findings by file", "filelist": "File list", "count": "{n}",
           "whyfix": "Why it matters · how to fix", "why": "Why it matters", "fix": "How to fix", "inc": "Incident",
           "doc": "Docs", "review": "Settings that need review",
           "review_p": "These rules could not be confirmed against official documentation, so they are not reported as risks. Please review them.",
           "tools": "AI tools found", "tool": "Tool", "ver": "Version", "where": "Location", "inactive": " (another install, not on PATH)",
           "mcp": "{n} MCP servers registered", "name": "Name", "cfg": "Config file", "how": "Command / URL", "whole": "whole configuration",
           "read": "Files read", "foot": "Chat logs, shell history and project source were not read. Secrets show only their first 4 characters. "
                                       "This record lists where the machine is weak — keep it where only the people who need it can see it."},
}


SCRIPT = """<script>(function(){var d=document.documentElement,p=(navigator.languages&&navigator.languages[0])||navigator.language||'';
function set(l){d.setAttribute('data-lang',l);d.setAttribute('lang',l);}
set(/^ko/i.test(p)?'ko':'en');
document.querySelectorAll('.langbar button').forEach(function(b){b.addEventListener('click',function(){set(b.getAttribute('data-set'));});});})();</script>"""


def html(ctx: Context, findings: list[Finding], rules: dict, incidents: dict, lang: str = "ko") -> str:
    """두 언어를 한 파일에 담는다. 브라우저 언어가 한국어면 한국어, 아니면 영어. lang은 자바스크립트가 꺼졌을 때의 기본값."""
    head = (f"<!doctype html><html lang='{lang}' data-lang='{lang}'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{T['ko']['title']} · {T['en']['title']}</title><style>{CSS}</style></head><body>"
            "<div class='langbar' role='group' aria-label='Language'><button type='button' data-set='ko'>한국어</button>"
            "<button type='button' data-set='en'>English</button></div>")
    body = "".join(_sheet(ctx, findings, rules, incidents, l) for l in ("ko", "en"))
    return scrub(head + body + SCRIPT + "</body></html>", ctx)


def _sheet(ctx: Context, findings: list[Finding], rules: dict, incidents: dict, lang: str) -> str:
    e = H.escape
    t = T[lang]
    conf = [f for f in findings if f.status == "확정"]
    review = [f for f in findings if f.status != "확정"]
    cnt = {s: sum(1 for f in conf if f.severity == s) for s in SEVERITIES}
    total = max(1, sum(cnt.values()))
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    loc = lambda f: display_path(f.path, ctx.home) if f.path else (f.pointer or t["whole"])
    title = lambda f: rtext(rules.get(f.rule, {}), "title", lang) or f.title
    sp = "" if lang == "ko" else " "

    P = [f"<div class='sheet' data-l='{lang}' lang='{lang}'>"]
    tools = ", ".join(sorted({tool_name(x.tool, lang) for x in ctx.tools if "-ext:" not in x.tool}))
    P.append(f"<header><div><h1>{t['title']}</h1><p class='lead'>{t['found']}: {e(tools or t['none'])}</p></div>"
             f"<div class='meta'>{e(now)}<br>ai-tool-audit {e(__version__)}<br>{t['ro']}</div></header>")
    P.append(f"<div class='strip' role='img' aria-label='{t['strip']}'>" + "".join(
        f"<i style='width:{cnt[s]*100/total:.2f}%;background:{COLOR[s]}'></i>" for s in SEVERITIES if cnt[s]) + "</div>")
    P.append("<div class='legend'>" + "".join(
        f"<span><span class='sw' style='background:{COLOR[s]}'></span><b>{cnt[s]}</b>{sp}{sev(s, lang)}</span>" for s in SEVERITIES)
        + f"<span><b>{len(review)}</b>{sp}{t['review_n']}</span><span><b>{len({str(f.path) for f in conf})}</b>{t['files_n']}</span></div>")

    # 먼저 고칠 것: 규칙이 겹치지 않게 심각도 순 5개
    order = {s: i for i, s in enumerate(SEVERITIES)}
    seen, first = set(), []
    for f in sorted(conf, key=lambda f: order[f.severity]):
        if f.rule not in seen and f.severity != "정보":
            seen.add(f.rule); first.append(f)
        if len(first) == 5:
            break
    if first:
        P.append(f"<h2>{t['first']}</h2><ol class='first'>" + "".join(
            f"<li><span class='sev s-{SEVCLS[f.severity]}'>{sev(f.severity, lang)}</span><span><span class='t'>{e(title(f))}</span><br>"
            f"<span class='path'>{e(loc(f))}{':' + str(f.line) if f.line else ''}</span></span></li>" for f in first) + "</ol>")

    # 파일별 묶음
    groups: "OrderedDict[str, list[Finding]]" = OrderedDict()
    for f in _sorted(conf):
        groups.setdefault(loc(f), []).append(f)
    files = sorted(groups.items(), key=lambda kv: (min(order[f.severity] for f in kv[1]), -len(kv[1]), kv[0]))
    P.append(f"<h2>{t['byfile']}</h2><div class='grid'><nav aria-label='{t['filelist']}'>")
    for i, (path, fs) in enumerate(files):
        worst = min(fs, key=lambda f: order[f.severity]).severity
        P.append(f"<a href='#{lang}f{i}'><span class='f'>{e(path)}</span><span class='c s-{SEVCLS[worst]}'>{len(fs)}</span></a>")
    P.append("</nav><div>")

    def row(f: Finding) -> str:
        r = rules.get(f.rule, {})
        inc = "".join(f"<p><b>{t['inc']}</b> {e(incidents[i]['date'])} <a href='{e(incidents[i]['url'])}'>{e(itext(incidents[i], 'title', lang))}</a>"
                      f" — {e(itext(incidents[i], 'summary', lang))}</p>" for i in r.get("incidents", []) if i in incidents)
        refs = "".join(f"<p><b>{t['doc']}</b> <a href='{e(u)}'>{e(u)}</a></p>" for u in r.get("refs", []))
        note = f"<div class='note'>{e(pick(f.note, lang))}</div>" if f.note else ""
        ev = f"<div class='ev'>{e(pick(f.evidence, lang))}</div>" if f.evidence else ""
        return (f"<div class='row'><div class='ln'>{':' + str(f.line) if f.line else ''}</div>"
                f"<div class='sev s-{SEVCLS[f.severity]}'>{sev(f.severity, lang)}</div>"
                f"<div><span class='t'>{e(title(f))}</span><span class='id'>{e(f.rule)}</span><br>{ev}{note}"
                f"<details><summary>{t['whyfix']}</summary><p><b>{t['why']}</b> {e(rtext(r, 'why', lang))}</p>"
                f"<p><b>{t['fix']}</b> {e(rtext(r, 'fix', lang))}</p>{inc}{refs}</details></div></div>")

    for i, (path, fs) in enumerate(files):
        P.append(f"<section class='file' id='{lang}f{i}'><h3>{e(path)}<span>{t['count'].format(n=len(fs))}</span></h3>"
                 + "".join(row(f) for f in fs) + "</section>")
    P.append("</div></div>")

    if review:
        P.append(f"<h2>{t['review']}</h2><p class='review'>{t['review_p']}</p>" + "".join(row(f) for f in _sorted(review)))

    P.append(f"<h2>{t['tools']}</h2><table><tr><th>{t['tool']}</th><th>{t['ver']}</th><th>{t['where']}</th></tr>" + "".join(
        f"<tr><td>{e(pick(x.name, lang))}{t['inactive'] if not x.active else ''}</td><td class='m'>{e(x.version or '-')}</td>"
        f"<td class='m'>{e(display_path(x.source, ctx.home))}</td></tr>" for x in ctx.tools) + "</table>")
    servers = list(mcp_servers(ctx))
    if servers:
        P.append(f"<h2>{t['mcp'].format(n=len(servers))}</h2><table><tr><th>{t['name']}</th><th>{t['tool']}</th><th>{t['cfg']}</th>"
                 f"<th>{t['how']}</th></tr>" + "".join(
            f"<tr><td>{e(n)}</td><td>{e(tool_name(d.tool, lang))}</td><td class='m'>{e(display_path(d.path, ctx.home))}</td>"
            f"<td class='m'>{e(server_how(s, ctx))}</td></tr>" for d, n, s, _ in servers) + "</table>")
    P.append(f"<footer><p>{t['read']}: <span class='m'>" + e(", ".join(display_path(p, ctx.home) for p in sorted(set(ctx.read_files), key=str)))
             + f"</span></p><p>{t['foot']}</p></footer></div>")
    return "\n".join(P)
