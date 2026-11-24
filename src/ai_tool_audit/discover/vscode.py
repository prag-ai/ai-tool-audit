"""VS Code·Cursor(+AI 확장) 설정 파일 찾기. 두 편집기는 설정 키가 같아 한 모듈에서 다룬다.

근거: docs/research/02 1·2절 (code.visualstudio.com/docs/agents/*, cursor.com/docs/*)
Cursor 사용자 settings.json 경로는 공식 문서 미확인(커뮤니티 확인) — 관련 규칙은 검토필요로 둔다.
"""
from __future__ import annotations

from pathlib import Path

from ..model import Context, Tool
from .common import extension_dirs, mac_app_version

EDITORS = {
    # tool: (앱 설정 폴더 이름, 확장 폴더, 맥 앱 이름, 표시 이름)
    "vscode": ("Code", ".vscode/extensions", "Visual Studio Code.app", "VS Code"),
    "cursor": ("Cursor", ".cursor/extensions", "Cursor.app", "Cursor"),
}

# 설치 목록에 보여 줄 AI 확장(확장 ID 소문자)
AI_EXTENSIONS = {
    "github.copilot": "GitHub Copilot", "github.copilot-chat": "GitHub Copilot Chat",
    "saoudrizwan.claude-dev": "Cline", "rooveterinaryinc.roo-cline": "Roo Code",
    "continue.continue": "Continue", "anthropic.claude-code": "Claude Code 확장",
    "openai.chatgpt": "Codex(OpenAI) 확장", "amazonwebservices.amazon-q-vscode": "Amazon Q",
    "google.geminicodeassist": "Gemini Code Assist",
}


def user_dir(ctx: Context, tool: str) -> Path:
    return ctx.user_app_dir(EDITORS[tool][0]) / "User"


def candidate_files(ctx: Context):
    out = []
    for tool in EDITORS:
        ud = user_dir(ctx, tool)
        out.append((tool, "settings", "user", ud / "settings.json", None))
        if tool == "vscode":
            out.append((tool, "mcp", "user", ud / "mcp.json", None))
        prof = ud / "profiles"
        if prof.is_dir():
            out += [(tool, "settings", "profile", p, None) for p in sorted(prof.glob("*/settings.json"))]
    out += [
        ("vscode", "copilot-mcp", "user", Path(ctx.env.get("COPILOT_HOME") or ctx.home / ".copilot") / "mcp-config.json", None),
        ("cursor", "mcp", "user", ctx.home / ".cursor/mcp.json", None),
        ("cursor", "cli", "user", ctx.home / ".cursor/cli-config.json", None),
    ]
    if ctx.os == "linux":
        out.append(("vscode", "policy", "managed", ctx.sys("/etc/vscode/policy.json"), None))
        out.append(("cursor", "policy", "managed", ctx.home / ".cursor/policy.json", None))
    for repo in ctx.repos:
        out += [
            ("vscode", "settings", "workspace", repo / ".vscode/settings.json", repo),
            ("vscode", "mcp", "workspace", repo / ".vscode/mcp.json", repo),
            ("vscode", "tasks", "workspace", repo / ".vscode/tasks.json", repo),
            ("cursor", "mcp", "workspace", repo / ".cursor/mcp.json", repo),
            ("cursor", "cli", "workspace", repo / ".cursor/cli.json", repo),
            ("cursor", "permissions", "workspace", repo / ".cursor/permissions.json", repo),
            ("cursor", "sandbox", "workspace", repo / ".cursor/sandbox.json", repo),
        ]
    return out


MCP_PTRS = {"mcp": ["/servers/*", "/mcpServers/*"], "copilot-mcp": ["/mcpServers/*"]}


def discover(ctx: Context) -> None:
    for tool, kind, layer, path, repo in candidate_files(ctx):
        ctx.load(tool, kind, layer, path, "json", repo=repo, mcp=MCP_PTRS.get(kind))
    for tool, (_, ext_rel, app, name) in EDITORS.items():
        ver_src = mac_app_version(ctx, app) if ctx.os == "macos" else None
        exts = extension_dirs(ctx, ctx.home / ext_rel)
        installed = ver_src or user_dir(ctx, tool).is_dir() or exts
        if not installed:
            continue
        ctx.tools.append(Tool(tool, name, ver_src[0] if ver_src else None,
                              ver_src[1] if ver_src else user_dir(ctx, tool)))
        latest: dict[str, tuple[str, Path]] = {}
        for ext_id, ver, path in exts:
            if ext_id in AI_EXTENSIONS:
                from ..checks import versions
                if ext_id not in latest or versions.lt(latest[ext_id][0], ver):
                    latest[ext_id] = (ver, path)
        for ext_id, (ver, path) in sorted(latest.items()):
            from ..i18n import L
            label = AI_EXTENSIONS[ext_id]
            label_en = {"Claude Code 확장": "Claude Code extension", "Codex(OpenAI) 확장": "Codex (OpenAI) extension"}.get(label, label)
            ctx.tools.append(Tool(f"{tool}-ext:{ext_id}", L(f"{name} 확장 · {label}", f"{name} extension · {label_en}"), ver, path))
