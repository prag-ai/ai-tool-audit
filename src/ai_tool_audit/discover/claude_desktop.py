"""Claude Desktop 설정 파일 찾기.

근거: docs/research/01 2절 (modelcontextprotocol.io connect-local-servers, support.claude.com 기업 설정)
정책 파일 경로는 제3자(3P) 배포 문서에만 있어 관련 규칙은 '검토필요'로 둔다.
"""
from __future__ import annotations

from ..model import Context, Tool
from .common import mac_app_version

TOOL = "claude-desktop"


def config_dir(ctx: Context):
    return ctx.user_app_dir("Claude")


def candidate_files(ctx: Context):
    out = [("config", "user", config_dir(ctx) / "claude_desktop_config.json", None)]
    if ctx.os == "linux":
        out.append(("policy", "managed", ctx.sys("/etc/claude-desktop/managed-settings.json"), None))
    return out


def discover(ctx: Context) -> None:
    for kind, layer, path, repo in candidate_files(ctx):
        ctx.load(TOOL, kind, layer, path, "json", repo=repo, mcp=["/mcpServers/*"] if kind == "config" else None)
    if ctx.os == "macos":
        _load_mac_policy(ctx)
    hit = mac_app_version(ctx, "Claude.app") if ctx.os == "macos" else None
    if hit:
        ctx.tools.append(Tool(TOOL, "Claude Desktop", hit[0], hit[1]))
    elif config_dir(ctx).is_dir():
        ctx.tools.append(Tool(TOOL, "Claude Desktop", None, config_dir(ctx)))


def _load_mac_policy(ctx: Context) -> None:
    import plistlib
    from ..model import ConfigDoc
    p = ctx.sys("/Library/Managed Preferences/com.anthropic.claudefordesktop.plist")
    try:
        if p.is_file():
            with p.open("rb") as fh:
                data = plistlib.load(fh)
            ctx.read_files.append(p)
            ctx.docs.append(ConfigDoc(tool=TOOL, kind="policy", layer="managed", path=p, fmt="plist", data=data))
    except (OSError, ValueError, plistlib.InvalidFileException):
        pass
