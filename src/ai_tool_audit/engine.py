"""규칙 실행기 — rules.json의 규칙을 읽어 들인 설정에 적용한다."""
from __future__ import annotations

import json
import re
import stat
from importlib import resources
from pathlib import Path

from .discover import claude_code, codex
from .jsonc import escape_pointer_token
from .model import ConfigDoc, Context, Finding
from .redact import mask
from .i18n import L


def load_rules() -> list[dict]:
    text = resources.files("ai_tool_audit.data").joinpath("rules.json").read_text(encoding="utf-8")
    return json.loads(text)["rules"]


def load_incidents() -> dict[str, dict]:
    text = resources.files("ai_tool_audit.data").joinpath("incidents.json").read_text(encoding="utf-8")
    return {i["id"]: i for i in json.loads(text)["incidents"]}


# ── 포인터 ────────────────────────────────────────
def resolve(data, pointer: str) -> list[tuple[str, object]]:
    """'/a/*/b' 같은 포인터(*는 모든 키·항목)에 맞는 (실제 포인터, 값) 목록."""
    parts = [p for p in pointer.split("/")[1:]] if pointer else []
    results = [("", data)]
    for raw in parts:
        tok = raw.replace("~1", "/").replace("~0", "~")
        nxt = []
        for ptr, val in results:
            if tok == "*":
                if isinstance(val, dict):
                    nxt += [(f"{ptr}/{escape_pointer_token(k)}", v) for k, v in val.items()]
                elif isinstance(val, list):
                    nxt += [(f"{ptr}/{i}", v) for i, v in enumerate(val)]
            elif isinstance(val, dict) and tok in val:
                nxt.append((f"{ptr}/{raw}", val[tok]))
            elif isinstance(val, list) and tok.isdigit() and int(tok) < len(val):
                nxt.append((f"{ptr}/{tok}", val[int(tok)]))
        results = nxt
    return results


def _last(ptr: str) -> str:
    return ptr.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")


def short(value, limit: int = 80) -> str:
    from .i18n import Msg
    if isinstance(value, Msg):
        return Msg(short(str(value), limit), short(value.en, limit))
    s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ── 경로 틀 ───────────────────────────────────────
def expand(ctx: Context, template: str) -> Path:
    return Path(template.format(home=ctx.home, claude_dir=claude_code.config_dir(ctx),
                                codex_home=codex.codex_home(ctx)))


# ── 실행 ──────────────────────────────────────────
def applies(rule: dict, ctx: Context) -> bool:
    if rule.get("enterprise") and not ctx.enterprise:
        return False
    if rule.get("os") and ctx.os not in rule["os"]:
        return False
    return True


def target_docs(rule: dict, ctx: Context) -> list[ConfigDoc]:
    sel = rule.get("docs", {})
    out = []
    tools = rule.get("tools") or [rule["tool"]]
    for d in ctx.docs:
        if d.tool not in tools or d.data is None:
            continue
        if sel.get("kind") and d.kind not in sel["kind"]:
            continue
        if sel.get("layer") and d.layer not in sel["layer"]:
            continue
        out.append(d)
    return out


def finding(rule: dict, **kw) -> Finding:
    return Finding(rule=rule["id"], severity=kw.pop("severity", rule["severity"]),
                   status=kw.pop("status", rule.get("status", "확정")), tool=kw.pop("tool", rule["tool"]),
                   title=rule["title"], **kw)


def run_rule(rule: dict, ctx: Context) -> list[Finding]:
    if not applies(rule, ctx):
        return []
    det = rule["detect"]
    t = det["type"]
    out: list[Finding] = []

    if t in ("equals", "present", "list_match"):
        pointers = det.get("pointers") or [det["pointer"]]
        for doc in target_docs(rule, ctx):
            for ptr, val in [hit for pt in pointers for hit in resolve(doc.data, pt)]:
                if t == "equals" and val in det["values"]:
                    out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(ptr), pointer=ptr,
                                       evidence=f"{_last(ptr)} = {short(val)}"))
                elif t == "present" and val not in (None, "", [], {}):
                    ev = L(f"{_last(ptr)} 설정됨", f"{_last(ptr)} is set")
                    out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(ptr), pointer=ptr, evidence=ev))
                elif t == "list_match" and isinstance(val, list):
                    for i, item in enumerate(val):
                        if not isinstance(item, str):
                            continue
                        if item in det.get("equals", []) or any(re.fullmatch(rx, item) for rx in det.get("regex", [])):
                            p = f"{ptr}/{i}"
                            out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                                               evidence=f'"{item}"'))

    elif t == "file_mode":
        if ctx.os == "windows":
            return []
        for tpl in det["paths"]:
            p = expand(ctx, tpl)
            try:
                mode = stat.S_IMODE(p.stat().st_mode)
            except OSError:
                continue
            if mode & 0o077:
                out.append(finding(rule, path=p, evidence=L(f"권한 {oct(mode)[2:]} (권장 600)", f"mode {oct(mode)[2:]} (recommended 600)")))

    elif t == "file_exists":
        for tpl in det["paths"]:
            p = expand(ctx, tpl)
            if p.exists():
                out.append(finding(rule, path=p, evidence=L("파일 있음", "file exists")))

    elif t == "shell_regex":
        rx = re.compile(det["regex"])
        for path, text in ctx.shell_files:
            for n, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                m = rx.search(line)
                if m:
                    ev = det.get("evidence") or m.group(0)
                    if det.get("secret"):
                        mk = mask(m.group('value'))
                        ev = L(f"{m.group('name')}={mk}", f"{m.group('name')}={mk.en}")
                    out.append(finding(rule, path=path, line=n, evidence=short(ev)))

    elif t == "check":
        from .checks import CHECKS
        out += CHECKS[det["name"]](rule, ctx)

    else:
        raise ValueError(f"알 수 없는 detect.type: {t}")
    return out


def run_all(ctx: Context, rules: list[dict] | None = None) -> list[Finding]:
    rules = rules if rules is not None else load_rules()
    findings: list[Finding] = []
    for r in rules:
        findings += run_rule(r, ctx)
    # 알려진 토큰 형식 규칙(ALL-SEC-003)은 다른 비밀값 규칙이 이미 잡은 줄이면 뺀다
    secret_lines = {(str(f.path), f.line) for f in findings if f.rule != "ALL-SEC-003" and "가림" in (f.evidence or "")}
    findings = [f for f in findings if not (f.rule == "ALL-SEC-003" and (str(f.path), f.line) in secret_lines)]
    # 같은 위치·같은 규칙 중복 제거
    seen, uniq = set(), []
    for f in findings:
        key = (f.rule, str(f.path), f.pointer, f.line, f.evidence)
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return uniq
