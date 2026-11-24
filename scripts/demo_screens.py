"""README 스크린샷용 화면(HTML)을 만든다. 실제 PC가 아니라 시험용 가짜 설정(tests/conftest.py의 make_risky)을 점검한다.

  uv run python scripts/demo_screens.py <출력 폴더>
  → term_ko.html·term_en.html(scan 출력), baseline_ko.html·baseline_en.html(baseline diff 출력), report.html(HTML 보고서, 한·영)
  이 HTML을 브라우저로 열어 캡처해 docs/images/에 둔다.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from conftest import make_risky, scan  # noqa: E402
from ai_tool_audit import baseline  # noqa: E402
from ai_tool_audit.engine import load_incidents, load_rules  # noqa: E402
from ai_tool_audit.report import terminal  # noqa: E402
from ai_tool_audit.report.ledger import html as to_html  # noqa: E402

PAGE = """<!doctype html><meta charset=utf-8><style>
body{{margin:0;background:#e9ecf1;padding:24px;font-family:-apple-system,sans-serif}}
.win{{width:1040px;border-radius:12px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.25);background:#1e2430}}
.bar{{background:#2c3340;padding:10px 14px;display:flex;align-items:center;gap:8px}}
.dot{{width:12px;height:12px;border-radius:50%}}.t{{color:#aab3c2;font-size:13px;margin-left:10px}}
pre{{margin:0;padding:18px 20px;color:#dfe5ee;font:13.5px/1.55 'D2Coding',Menlo,monospace;white-space:pre-wrap;word-break:break-all}}
.cmd{{color:#8fd18f}}.hi{{color:#ff6b6b;font-weight:700}}.mid{{color:#f0a94b;font-weight:700}}.lo{{color:#7fb2ff}}.h{{color:#fff;font-weight:700}}
</style><div class=win><div class=bar><span class=dot style="background:#ff5f57"></span><span class=dot style="background:#febc2e"></span>
<span class=dot style="background:#28c840"></span><span class=t>{title}</span></div><pre><span class=cmd>$ {cmd}</span>
{body}</pre></div>"""


def page(cmd: str, text: str, title: str) -> str:
    b = html.escape(text)
    b = re.sub(r"\[(높음|새로 생김|바뀜|High|added|changed)\]", r'<span class="hi">[\1]</span>', b)
    b = re.sub(r"\[(중간|Medium)\]", r'<span class="mid">[\1]</span>', b)
    b = re.sub(r"\[(낮음|정보|Low|Info)\]", r'<span class="lo">[\1]</span>', b)
    b = re.sub(r"^(■ .*)$", r'<span class="h">\1</span>', b, flags=re.M)
    return PAGE.format(title=html.escape(title), cmd=html.escape(cmd), body=b)


def block(lines, rule):
    i = next(k for k, l in enumerate(lines) if l.startswith("[") and f"] {rule} " in l)
    j = i + 1
    while j < len(lines) and lines[j].startswith("  "):
        j += 1
    return [""] + lines[i:j]


def main(out: Path) -> None:
    work = out / "demo"
    shutil.rmtree(work, ignore_errors=True)
    home, repo = make_risky(work)
    proj = work / "my-project"
    repo.rename(proj)
    cfg = home / ".codex/config.toml"
    cfg.write_text(cfg.read_text().replace(repo.as_posix(), proj.as_posix()))

    ctx, findings = scan(home, proj)
    rules, incs = {r["id"]: r for r in load_rules()}, load_incidents()
    (out / "report.html").write_text(to_html(ctx, findings, rules, incs), encoding="utf-8")

    for lang, more, title in (("ko", "  …(이하 생략)", "터미널"), ("en", "  …(truncated)", "Terminal")):
        lines = terminal(ctx, findings, rules, incs, lang=lang).splitlines()
        head = lines[: next(i for i, l in enumerate(lines) if l.startswith("■ ")
                            and ("결과" in l or "Result" in l)) + 1]
        body = head + sum((block(lines, r) for r in ("ALL-VER-001", "CC-PERM-004", "VSC-TASK-002")), []) + ["", more]
        (out / f"term_{lang}.html").write_text(page(f"ai-tool-audit scan --repo ~/work/my-project --lang {lang}", "\n".join(body),
                                                    f"{title} — ai-tool-audit scan"), encoding="utf-8")

    # 기준선 저장 → 악성 MCP 서버 추가·기존 서버 바꿔치기(SANDWORM_MODE 방식) → 비교
    baseline.save(ctx)
    cj = home / ".claude.json"
    d = json.loads(cj.read_text())
    d["mcpServers"]["dev-utils"] = {"command": "node", "args": [str(home / ".dev-utils/server.js")]}
    d["mcpServers"]["fs"]["args"] = ["-y", "@evil/fs-helper"]
    cj.write_text(json.dumps(d, indent=2))
    ctx2, _ = scan(home, proj)
    base = baseline.load(ctx2)
    diff = baseline.diff(ctx2, base)
    from ai_tool_audit.cli import S
    for lang, title in (("ko", "터미널"), ("en", "Terminal")):
        t = S[lang]
        bl = [t["bl_cmp"].format(t=base["saved_at"])]
        for kind in ("added", "changed", "removed"):
            for s in diff[kind]:
                bl.append(f"  [{t[kind]}] {s['name']} ({s['file']}): {s['how']}" + (f"  ← {t['before']}: {s['before']}" if kind == "changed" else ""))
        (out / f"baseline_{lang}.html").write_text(page(f"ai-tool-audit baseline diff --lang {lang}", "\n".join(bl),
                                                        f"{title} — ai-tool-audit baseline diff"), encoding="utf-8")
    print(f"발견 {len(findings)}건 → {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
