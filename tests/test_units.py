import pytest

from ai_tool_audit import jsonc
from ai_tool_audit.checks import _is_pinned, _package_arg, versions
from ai_tool_audit.model import toml_line_of
from ai_tool_audit.redact import display_path, is_literal_secret, mask


def test_jsonc_comments_and_lines():
    text = '{\n  // 주석\n  "a": {\n    "b": [1, 2,],\n  },\n  /* 블록 */ "c": "x//y",\n}\n'
    val, lines = jsonc.loads(text)
    assert val == {"a": {"b": [1, 2]}, "c": "x//y"}
    assert lines["/a"] == 3 and lines["/a/b"] == 4 and lines["/c"] == 6


def test_jsonc_error_has_line():
    with pytest.raises(jsonc.JsoncError) as e:
        jsonc.loads('{\n "a": 1\n "b": 2}')
    assert e.value.line == 3


def test_toml_line_lookup():
    text = 'a = 1\n[mcp_servers.db]\ncommand = "uvx"\n\n[mcp_servers.db.env]\nDB_PASSWORD = "x"\n[projects."/a/b"]\ntrust_level = "trusted"\n'
    assert toml_line_of(text, "/a") == 1
    assert toml_line_of(text, "/mcp_servers/db/command") == 3
    assert toml_line_of(text, "/mcp_servers/db/env/DB_PASSWORD") == 6


@pytest.mark.parametrize("a,b,lt", [("2.1.100", "2.1.257", True), ("2.1.331", "2.1.257", False),
                                    ("0.39.0-alpha", "0.39.0", True), ("1.10.0", "1.9.9", False)])
def test_versions(a, b, lt):
    assert versions.lt(a, b) is lt


@pytest.mark.parametrize("cmd,args,pinned", [
    ("npx", ["-y", "@scope/pkg"], False),
    ("npx", ["-y", "@scope/pkg@1.2.3"], True),
    ("npx", ["pkg@latest"], False),
    ("npx", ["pkg@^1.2.0"], False),
    ("uvx", ["mcp-x==1.0.0"], True),
    ("uvx", ["mcp-x"], False),
    ("uvx", ["--from", "mcp-x==2.0", "mcp-x"], True),
    ("pnpm", ["dlx", "pkg"], False),
])
def test_pinning(cmd, args, pinned):
    pkg, eco = _package_arg(cmd, args)
    assert pkg and _is_pinned(pkg, eco) is pinned


def test_non_runner_ignored():
    assert _package_arg("node", ["server.js"])[0] is None


@pytest.mark.parametrize("name,value,secret", [
    ("API_KEY", "abcdefgh12345", True),
    ("API_KEY", "${API_KEY}", False),
    ("Authorization", "Bearer ${TOKEN}", False),
    ("Authorization", "Bearer abcdefgh12345", True),
    ("LOG_LEVEL", "debug-verbose-mode", False),
    ("TOKEN", "short", False),
])
def test_literal_secret(name, value, secret):
    assert is_literal_secret(name, value) is secret


def test_mask_and_path(tmp_path):
    assert mask("sk-abcdef123") == "sk-a…(가림)"
    assert display_path(tmp_path / "x/y", tmp_path) == "~/x/y"


def test_redact_args_and_url():
    from ai_tool_audit.redact import redact_args, redact_url
    args = ["-y", "pkg@1.0.0", "--api-key", "abcd1234efgh", "--token=zzzz9999yyyy", "--root", "/home/x",
            "Q2xhdWRlQ29kZVNlY3JldFRva2VuMTIzNDU2"]
    out = " ".join(redact_args(args))
    assert "abcd1234efgh" not in out and "zzzz9999yyyy" not in out and "Q2xhdWRl" not in out
    assert "pkg@1.0.0" in out and "/home/x" in out
    u = redact_url("https://user:pw@mcp.example.com/sse?api_key=SECRET12345&v=2")
    assert "pw" not in u and "SECRET12345" not in u and "v=2" in u


def test_extension_version_platform_suffix(tmp_path):
    from ai_tool_audit.discover.common import extension_dirs
    from ai_tool_audit.model import Context
    (tmp_path / "anthropic.claude-code-2.1.330-darwin-arm64").mkdir()
    (tmp_path / "github.copilot-chat-0.30.0").mkdir()
    ctx = Context(home=tmp_path, env={}, os="macos", isolated=True)
    got = {i: v for i, v, _ in extension_dirs(ctx, tmp_path)}
    assert got == {"anthropic.claude-code": "2.1.330", "github.copilot-chat": "0.30.0"}


@pytest.mark.parametrize("pkg,pinned", [
    ("git+https://github.com/prag-ai/ai-tool-audit@v0.2.0", True),
    ("git+https://github.com/prag-ai/ai-tool-audit@" + "a" * 40, True),
    ("git+https://github.com/prag-ai/ai-tool-audit", False),
])
def test_pinning_git(pkg, pinned):
    assert _is_pinned(pkg, "pypi") is pinned
