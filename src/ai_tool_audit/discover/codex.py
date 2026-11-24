"""OpenAI Codex CLI 설정 파일 찾기.

근거: docs/research/01 3절 (learn.chatgpt.com/docs/config-file/*, hooks, auth, enterprise)
"""
from __future__ import annotations

from pathlib import Path

from ..model import Context, Tool
from .common import npm_package_installs

TOOL = "codex"


def codex_home(ctx: Context) -> Path:
    d = ctx.env.get("CODEX_HOME")
    return Path(d).expanduser() if d else ctx.home / ".codex"


def system_dir(ctx: Context) -> Path:
    if ctx.os == "windows":
        return ctx.sys(Path(ctx.env.get("ProgramData", "C:/ProgramData")) / "OpenAI/Codex")
    return ctx.sys("/etc/codex")


def candidate_files(ctx: Context) -> list[tuple[str, str, Path, Path | None, str]]:
    ch, sd = codex_home(ctx), system_dir(ctx)
    out = [
        ("config", "user", ch / "config.toml", None, "toml"),
        ("hooks", "user", ch / "hooks.json", None, "json"),
        ("config", "system", sd / "config.toml", None, "toml"),
        ("requirements", "managed", sd / "requirements.toml", None, "toml"),
        ("config", "managed", sd / "managed_config.toml", None, "toml"),
        ("hooks", "managed", sd / "hooks.json", None, "json"),
    ]
    if ctx.os == "windows":
        out.append(("config", "managed-user", ch / "managed_config.toml", None, "toml"))
    if ch.is_dir():
        out += [("config", "profile", p, None, "toml") for p in sorted(ch.glob("*.config.toml"))]
    for repo in ctx.repos:
        out += [
            ("config", "project", repo / ".codex/config.toml", repo, "toml"),
            ("hooks", "project", repo / ".codex/hooks.json", repo, "json"),
        ]
    return out


def discover(ctx: Context) -> None:
    for kind, layer, path, repo, fmt in candidate_files(ctx):
        ctx.load(TOOL, kind, layer, path, fmt, repo=repo,
                 mcp=["/mcp_servers/*", "/profiles/*/mcp_servers/*"] if kind == "config" else None)
    _inventory(ctx)


def _inventory(ctx: Context) -> None:
    installs = npm_package_installs(ctx, "@openai/codex")
    for ver, src, active in installs:
        ctx.tools.append(Tool(TOOL, "Codex CLI", ver, src, active))
    if installs:
        return
    version, source = None, None
    if version is None:
        for base in (ctx.sys("/opt/homebrew/Caskroom/codex"), ctx.sys("/usr/local/Caskroom/codex")):
            if base.is_dir():
                vers = sorted(p.name for p in base.iterdir() if p.is_dir())
                if vers:
                    version, source = vers[-1], base / vers[-1]
                    break
    standalone = ctx.home / ".local/bin" / ("codex.exe" if ctx.os == "windows" else "codex")
    installed = version is not None or standalone.exists() or codex_home(ctx).is_dir()
    if installed:
        ctx.tools.append(Tool(TOOL, "Codex CLI", version, source or (standalone if standalone.exists() else None)))
