"""MCP 서버(stdio) — Claude Code·Cursor 같은 AI 도구 안에서 점검기를 부른다.

외부 패키지 없이 표준 라이브러리로 MCP의 stdio 전송(줄 단위 JSON-RPC 2.0)을 구현한다.
점검기와 같은 원칙을 지킨다: 네트워크를 쓰지 않고, 다른 프로그램을 실행하지 않고, 비밀값을 내보내지 않는다.
표준 출력은 프로토콜 전용이다. 사람이 읽을 기록은 표준 오류로만 쓴다.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

from . import __version__
from . import baseline as bl
from .discover import discover_all
from .engine import load_incidents, load_rules, run_all
from .model import Context
from .report import terminal

SUPPORTED = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

INSTRUCTIONS = (
    "ai-tool-audit checks the AI coding tools on this machine (Claude Code, Codex CLI, Gemini CLI, Claude Desktop, "
    "VS Code, Cursor and their MCP servers) for risky settings, plaintext secrets and versions with known advisories. "
    "It only reads configuration files and never sends anything over the network. Secrets in results are masked to "
    "their first 4 characters; never ask the user to reveal the full value. "
    "Start with the `scan` tool. Use `explain_rule` for one rule's details and `list_files` to show what will be read."
)

LANG = {"type": "string", "enum": ["auto", "ko", "en"], "default": "auto",
        "description": "Output language. auto follows the system language. / 출력 언어"}
REPOS = {"type": "array", "items": {"type": "string"},
         "description": "Repository folders to include (their .claude, .vscode, .cursor, .mcp.json etc.). / 함께 점검할 저장소 폴더"}

TOOLS = [
    {"name": "scan",
     "title": "Audit AI tool settings",
     "description": "Audit this machine's AI coding tools and MCP servers. Returns findings with location, why it "
                    "matters, how to fix, and the public incident behind each rule. Read-only, no network.",
     "inputSchema": {"type": "object", "properties": {
         "repos": REPOS,
         "enterprise": {"type": "boolean", "default": False, "description": "Also check managed-policy rules. / 기업 관리 정책 규칙도 점검"},
         "lang": LANG}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "explain_rule",
     "title": "Explain a rule",
     "description": "Explain one rule by ID (e.g. CC-PERM-001): why it is risky, how to fix it, related incidents and docs. "
                    "Without an ID, list all rules.",
     "inputSchema": {"type": "object", "properties": {
         "rule_id": {"type": "string", "description": "Rule ID. Omit to list all rules. / 규칙 ID"},
         "lang": LANG}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "list_files",
     "title": "List files that would be read",
     "description": "List the configuration files a scan would read, without opening any of them.",
     "inputSchema": {"type": "object", "properties": {"repos": REPOS, "lang": LANG}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "baseline_diff",
     "title": "Find changed MCP servers",
     "description": "Compare the registered MCP servers with the saved baseline and report servers that were added, "
                    "changed or removed since then (e.g. a server slipped in by a malicious package).",
     "inputSchema": {"type": "object", "properties": {"repos": REPOS, "lang": LANG}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "baseline_save",
     "title": "Save MCP server baseline",
     "description": "Save the current MCP server list as the baseline (~/.ai-tool-audit/baseline.json). Only command, "
                    "arguments, URL and env/header NAMES are hashed; secret values are not stored. Ask the user first.",
     "inputSchema": {"type": "object", "properties": {"repos": REPOS, "lang": LANG}},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},
]


def _repos(args: dict) -> list[str]:
    r = args.get("repos") or []
    if isinstance(r, str):
        r = [r]
    if not isinstance(r, list) or not all(isinstance(x, str) for x in r):
        raise ValueError("repos must be a list of folder paths")
    return [str(Path(x).expanduser()) for x in r]


def _lang(args: dict) -> str:
    v = args.get("lang", "auto")
    if v not in ("auto", "ko", "en"):
        raise ValueError("lang must be auto, ko or en")
    return v


def _cli_text(fn, **ns) -> str:
    """CLI 명령 함수를 불러 표준 출력 대신 문자열로 받는다(프로토콜 출력과 섞이지 않게)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fn(argparse.Namespace(**ns))
    text = buf.getvalue().rstrip()
    if code == 2 and fn.__name__ == "cmd_rules":
        raise ValueError(f"unknown rule: {ns.get('id')}")
    return text


def call_tool(name: str, args: dict) -> str:
    from . import cli
    args = args or {}
    if name == "scan":
        lang = _lang(args)
        ctx = Context.current(repos=_repos(args), enterprise=bool(args.get("enterprise")))
        discover_all(ctx)
        rules = load_rules()
        findings = run_all(ctx, rules)
        lang = cli._lang(argparse.Namespace(lang=lang), ctx)
        return terminal(ctx, findings, {r["id"]: r for r in rules}, load_incidents(), lang=lang)
    if name == "explain_rule":
        rid = args.get("rule_id")
        if rid is not None and not isinstance(rid, str):
            raise ValueError("rule_id must be a string")
        return _cli_text(cli.cmd_rules, id=rid or None, lang=_lang(args))
    if name == "list_files":
        return _cli_text(cli.cmd_files, repo=_repos(args), enterprise=False, lang=_lang(args))
    if name in ("baseline_diff", "baseline_save"):
        action = "diff" if name == "baseline_diff" else "save"
        return _cli_text(cli.cmd_baseline, action=action, file=None, repo=_repos(args), lang=_lang(args))
    raise LookupError(name)


def _result(id_, result=None, error=None) -> dict:
    msg = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    return msg


def handle(msg) -> dict | None:
    """요청 하나를 처리해 응답을 돌려준다. 알림(id 없음)에는 None."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _result(msg.get("id") if isinstance(msg, dict) else None,
                       error={"code": -32600, "message": "Invalid Request"})
    method, id_, params = msg["method"], msg.get("id"), msg.get("params") or {}
    if "id" not in msg:
        return None                                  # notifications/initialized 등
    if method == "initialize":
        want = params.get("protocolVersion")
        return _result(id_, {
            "protocolVersion": want if want in SUPPORTED else SUPPORTED[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "ai-tool-audit", "title": "AI Tool Audit", "version": __version__},
            "instructions": INSTRUCTIONS})
    if method == "ping":
        return _result(id_, {})
    if method == "tools/list":
        return _result(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        try:
            text = call_tool(name, params.get("arguments") or {})
            return _result(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        except LookupError:
            return _result(id_, error={"code": -32602, "message": f"Unknown tool: {name}"})
        except ValueError as e:
            return _result(id_, {"content": [{"type": "text", "text": f"Invalid arguments: {e}"}], "isError": True})
        except Exception as e:                       # 점검 중 예외는 도구 오류로 돌려준다
            return _result(id_, {"content": [{"type": "text", "text": f"Scan failed: {type(e).__name__}"}], "isError": True})
    return _result(id_, error={"code": -32601, "message": f"Method not found: {method}"})


def serve(stdin=None, stdout=None) -> int:
    stdin = stdin or io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    stdout = stdout or io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    print(f"ai-tool-audit {__version__} MCP server (stdio) ready", file=sys.stderr)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply = _result(None, error={"code": -32700, "message": "Parse error"})
        else:
            if isinstance(msg, list):                # 묶음 요청(구버전 규격)
                replies = [r for r in (handle(m) for m in msg) if r is not None]
                reply = replies or None
            else:
                reply = handle(msg)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
