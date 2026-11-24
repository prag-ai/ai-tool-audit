"""MCP 서버(stdio) 시험 — 프로토콜, 도구 호출, 원칙(네트워크·실행·비밀값)."""
import io
import json
import re
import socket
import subprocess

import pytest

from ai_tool_audit import mcp_server
from ai_tool_audit.model import Context
from conftest import AWS_KEY, GH_TOKEN, make_risky


@pytest.fixture
def env(tmp_path, monkeypatch):
    home, repo = make_risky(tmp_path)
    ctx_of = lambda repos=None, enterprise=False: Context(home=home, env={}, os="linux", repos=[repo] + [p for p in (repos or [])],
                                                         enterprise=enterprise, isolated=True)
    monkeypatch.setattr(Context, "current", classmethod(lambda cls, repos=None, enterprise=False: ctx_of(repos, enterprise)))
    return home, repo


def rpc(*msgs):
    inp = io.StringIO("".join(json.dumps(m) + "\n" for m in msgs))
    out = io.StringIO()
    mcp_server.serve(inp, out)
    return [json.loads(l) for l in out.getvalue().splitlines()]


def call(name, args=None, i=9):
    return rpc({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args or {}}})[0]


def test_handshake_and_list():
    r = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "ping"})
    assert [m["id"] for m in r] == [1, 2, 3]                       # 알림에는 응답하지 않는다
    assert r[0]["result"]["protocolVersion"] == "2025-06-18"
    assert r[0]["result"]["capabilities"] == {"tools": {"listChanged": False}}
    names = {t["name"] for t in r[1]["result"]["tools"]}
    assert names == {"scan", "explain_rule", "list_files", "baseline_diff", "baseline_save"}
    assert r[2]["result"] == {}


def test_unknown_version_falls_back():
    r = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999-01-01"}})
    assert r[0]["result"]["protocolVersion"] == mcp_server.SUPPORTED[0]


def test_errors():
    r = rpc({"jsonrpc": "2.0", "id": 1, "method": "nope"})
    assert r[0]["error"]["code"] == -32601
    out = io.StringIO()
    mcp_server.serve(io.StringIO("{not json\n"), out)
    assert json.loads(out.getvalue())["error"]["code"] == -32700
    assert call("nope")["error"]["code"] == -32602
    assert call("scan", {"lang": "fr"})["result"]["isError"] is True


def test_scan_masks_secrets(env):
    home, _ = env
    res = call("scan", {"lang": "en"})["result"]
    text = res["content"][0]["text"]
    assert res["isError"] is False and "CC-PERM" in text
    assert GH_TOKEN not in text and AWS_KEY not in text and str(home) not in text
    assert not re.search(r"[가-힣]", text)                          # 영어 출력에 한국어가 섞이지 않는다


def test_explain_and_files(env):
    t = call("explain_rule", {"rule_id": "cc-perm-001", "lang": "ko"})["result"]["content"][0]["text"]
    assert t.startswith("CC-PERM-001") and "이유" in t
    assert call("explain_rule", {"rule_id": "XX-1"})["result"]["isError"] is True
    assert "rules" in call("explain_rule", {"lang": "en"})["result"]["content"][0]["text"]
    assert "~/.claude/settings.json" in call("list_files", {"lang": "en"})["result"]["content"][0]["text"]


def test_baseline_tools(env):
    home, _ = env
    assert "No saved baseline" in call("baseline_diff", {"lang": "en"})["result"]["content"][0]["text"]
    assert "Saved a baseline" in call("baseline_save", {"lang": "en"})["result"]["content"][0]["text"]
    assert (home / ".ai-tool-audit/baseline.json").exists()
    assert "No MCP server has changed" in call("baseline_diff", {"lang": "en"})["result"]["content"][0]["text"]


def test_no_network_no_subprocess(env, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("forbidden")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    assert call("scan", {"lang": "en"})["result"]["isError"] is False
