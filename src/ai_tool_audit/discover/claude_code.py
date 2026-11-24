"""Claude Code·설정 파일 찾기.

근거: docs/research/01 1절 (code.claude.com/docs/en/settings, mcp, managed-settings, setup, authentication)
"""
from __future__ import annotations

import re
from pathlib import Path

from ..model import Context, Tool
from .common import npm_package_installs

TOOL = "claude-code"


def config_dir(ctx: Context) -> Path:
    d = ctx.env.get("CLAUDE_CONFIG_DIR")
    return Path(d).expanduser() if d else ctx.home / ".claude"


def managed_dir(ctx: Context) -> Path:
    return ctx.sys({
        "macos": "/Library/Application Support/ClaudeCode",
        "windows": "C:/Program Files/ClaudeCode",
    }.get(ctx.os, "/etc/claude-code"))


def candidate_files(ctx: Context) -> list[tuple[str, str, Path, Path | None]]:
    """(kind, layer, path, repo) 목록 — `files` 명령과 실제 읽기에 함께 쓴다."""
    cd = config_dir(ctx)
    out = [
        ("settings", "user", cd / "settings.json", None),
        ("state", "user", ctx.home / ".claude.json", None),
        ("settings", "managed", managed_dir(ctx) / "managed-settings.json", None),
        ("mcpjson", "managed", managed_dir(ctx) / "managed-mcp.json", None),
    ]
    md = managed_dir(ctx) / "managed-settings.d"
    if md.is_dir():
        out += [("settings", "managed", p, None) for p in sorted(md.glob("*.json"))]
    if ctx.os == "windows":
        out.append(("settings", "managed-legacy", ctx.sys("C:/ProgramData/ClaudeCode/managed-settings.json"), None))
    for repo in ctx.repos:
        out += [
            ("settings", "project", repo / ".claude/settings.json", repo),
            ("settings", "local", repo / ".claude/settings.local.json", repo),
            ("mcpjson", "project", repo / ".mcp.json", repo),
        ]
    return out


def discover(ctx: Context) -> None:
    mcp = {"state": ["/mcpServers/*", "/projects/*/mcpServers/*"], "mcpjson": ["/mcpServers/*"]}
    for kind, layer, path, repo in candidate_files(ctx):
        ctx.load(TOOL, kind, layer, path, "json", repo=repo, mcp=mcp.get(kind))
    _inventory(ctx)


def _ver_key(v: str):
    return [int(x) if x.isdigit() else x for x in re.split(r"[.\-]", v)]


def _inventory(ctx: Context) -> None:
    # 1) 네이티브 설치: ~/.local/bin/claude → ~/.local/share/claude/versions/<버전>
    link = ctx.home / ".local/bin" / ("claude.exe" if ctx.os == "windows" else "claude")
    vdir = ctx.home / ".local/share/claude/versions"
    version, source = None, None
    try:
        if link.is_symlink():
            target = link.resolve()
            if target.parent.name == "versions" or target.parent == vdir.resolve():
                version, source = target.name, target
    except OSError:
        pass
    if version is None and vdir.is_dir():
        vers = sorted((p.name for p in vdir.iterdir() if re.match(r"^\d+\.\d+", p.name)), key=_ver_key)
        if vers:
            version, source = vers[-1], vdir / vers[-1]
    # 2) npm 전역
    npm = npm_package_installs(ctx, "@anthropic-ai/claude-code")
    if version is None and npm:
        for ver, src, active in npm:
            ctx.tools.append(Tool(TOOL, "Claude Code", ver, src, active))
        return
    # 3) Homebrew cask
    if version is None:
        for base in (ctx.sys("/opt/homebrew/Caskroom/claude-code"), ctx.sys("/usr/local/Caskroom/claude-code")):
            if base.is_dir():
                vers = sorted((p.name for p in base.iterdir() if p.is_dir()), key=_ver_key)
                if vers:
                    version, source = vers[-1], base / vers[-1]
                    break
    installed = version is not None or link.exists() or config_dir(ctx).is_dir()
    if installed:
        ctx.tools.append(Tool(TOOL, "Claude Code", version, source))
