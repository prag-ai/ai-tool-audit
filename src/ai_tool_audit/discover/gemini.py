"""Google Gemini CLI 설정 파일 찾기.

근거: docs/research/01 4절 (github.com/google-gemini/gemini-cli docs/reference/configuration.md 등)
"""
from __future__ import annotations

from pathlib import Path

from ..model import Context, Tool
from .common import npm_package_installs

TOOL = "gemini"
MCP = ["/mcpServers/*"]


def system_dir(ctx: Context) -> Path:
    return ctx.sys({"macos": "/Library/Application Support/GeminiCli",
                    "windows": "C:/ProgramData/gemini-cli"}.get(ctx.os, "/etc/gemini-cli"))


def candidate_files(ctx: Context):
    g, sd = ctx.home / ".gemini", system_dir(ctx)
    sys_settings = Path(ctx.env["GEMINI_CLI_SYSTEM_SETTINGS_PATH"]) if ctx.env.get("GEMINI_CLI_SYSTEM_SETTINGS_PATH") else sd / "settings.json"
    sys_defaults = Path(ctx.env["GEMINI_CLI_SYSTEM_DEFAULTS_PATH"]) if ctx.env.get("GEMINI_CLI_SYSTEM_DEFAULTS_PATH") else sd / "system-defaults.json"
    out = [
        ("settings", "user", g / "settings.json", None),
        ("settings", "system", sys_settings, None),
        ("settings", "system-defaults", sys_defaults, None),
        ("trusted", "user", g / "trustedFolders.json", None),
    ]
    for repo in ctx.repos:
        out.append(("settings", "project", repo / ".gemini/settings.json", repo))
    return out


def discover(ctx: Context) -> None:
    for kind, layer, path, repo in candidate_files(ctx):
        ctx.load(TOOL, kind, layer, path, "json", repo=repo, mcp=MCP if kind == "settings" else None)
    for repo in ctx.repos:   # 저장소의 .gemini/.env (패턴 일치만)
        ctx.load(TOOL, "dotenv", "project", repo / ".gemini/.env", "text", repo=repo)
    installs = npm_package_installs(ctx, "@google/gemini-cli")
    for ver, src, active in installs:
        ctx.tools.append(Tool(TOOL, "Gemini CLI", ver, src, active))
    if not installs:
        for base in (ctx.sys("/opt/homebrew/Cellar/gemini-cli"), ctx.sys("/usr/local/Cellar/gemini-cli")):
            vers = sorted(p.name for p in base.iterdir()) if base.is_dir() else []
            if vers:
                ctx.tools.append(Tool(TOOL, "Gemini CLI", vers[-1], base / vers[-1]))
                return
        if (ctx.home / ".gemini/settings.json").exists():
            ctx.tools.append(Tool(TOOL, "Gemini CLI", None, ctx.home / ".gemini"))
