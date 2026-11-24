"""선언형 규칙(equals·list_match 등)으로 표현하기 어려운 점검.

규칙 파일의 detect: {type: check, name: <여기 이름>} 으로 연결한다.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..engine import finding, resolve, short
from ..jsonc import escape_pointer_token
from ..model import ConfigDoc, Context
from ..redact import find_known_tokens, is_literal_secret, mask, redact_url
from ..i18n import L
from . import versions

CHECKS = {}


def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


# ── MCP 서버 목록 ─────────────────────────────────
def mcp_servers(ctx: Context):
    """(doc, 서버 이름, 서버 설정 dict, 포인터)를 도구 구분 없이 돌려준다.
    각 discover 모듈이 문서를 읽을 때 MCP 서버 위치(doc.mcp)를 적어 둔다."""
    for doc in ctx.docs:
        if not doc.mcp or not isinstance(doc.data, dict):
            continue
        for pat in doc.mcp:
            for ptr, srv in resolve(doc.data, pat):
                if isinstance(srv, dict):
                    name = ptr.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")
                    yield doc, name, srv, ptr


def server_url(srv: dict):
    for k in ("url", "httpUrl", "serverUrl"):
        if isinstance(srv.get(k), str):
            return k, srv[k]
    return None, None


SECRET_FIELDS = ["env", "headers", "http_headers"]


@check("mcp_literal_secret")
def mcp_literal_secret(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        for fld in SECRET_FIELDS:
            block = srv.get(fld)
            if not isinstance(block, dict):
                continue
            for k, v in block.items():
                if is_literal_secret(k, v):
                    p = f"{ptr}/{fld}/{escape_pointer_token(k)}"
                    kinds = sorted({kind for kind, _ in find_known_tokens(v)})
                    kinds_en = sorted({KIND_EN.get(kind, kind) for kind in kinds})
                    mk = mask(v)
                    out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                                       evidence=L(f"서버 {name}: {k} = {mk}" + (f" [{', '.join(kinds)} 형식]" if kinds else ""),
                                                  f"server {name}: {k} = {mk.en}" + (f" [{', '.join(kinds_en)} format]" if kinds else ""))))
        for blk, key in (("oauth", "client_secret"), ("auth", "CLIENT_SECRET")):
            b = srv.get(blk)
            if isinstance(b, dict) and is_literal_secret("client_secret", b.get(key)):
                p = f"{ptr}/{blk}/{key}"
                out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                                   evidence=L(f"서버 {name}: {key} = {mask(b[key])}", f"server {name}: {key} = {mask(b[key]).en}")))
    return out


RUNNERS = {"npx": "npm", "bunx": "npm", "uvx": "pypi", "pipx": "pypi"}


def _package_arg(cmd: str, args: list) -> tuple[str | None, str]:
    """실행기(npx 등) 뒤의 패키지 이름. (패키지, 생태계)"""
    base = Path(cmd).name.lower().removesuffix(".cmd").removesuffix(".exe")
    eco = RUNNERS.get(base)
    rest = [a for a in args if isinstance(a, str)]
    if base in ("pnpm", "yarn") and rest[:1] == ["dlx"]:
        eco, rest = "npm", rest[1:]
    if base == "pipx" and rest[:1] == ["run"]:
        rest = rest[1:]
    if eco is None:
        return None, ""
    skip_next = {"--package", "-p", "--from", "--with", "--python"}
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in skip_next:
            # --package <이름> 형식이면 그 이름이 패키지
            if a in ("--package", "-p", "--from") and i + 1 < len(rest):
                return rest[i + 1], eco
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a, eco
    return None, eco


def _is_pinned(pkg: str, eco: str) -> bool:
    if eco == "npm":
        body = pkg[1:] if pkg.startswith("@") else pkg
        if "@" not in body:
            return False
        ver = body.split("@", 1)[1]
        return bool(re.match(r"^v?\d+\.\d+\.\d+", ver))   # latest·^1·~1·1.x 는 고정이 아님
    # pypi: 이름==1.2.3, 이름@1.2.3, git+주소@v1.2.3 또는 커밋 해시
    return bool(re.search(r"(==|@)v?\d+(\.\d+)*$", pkg) or re.search(r"@[0-9a-f]{40}$", pkg))


@check("mcp_unpinned")
def mcp_unpinned(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        cmd, args = srv.get("command"), srv.get("args") or []
        if not isinstance(cmd, str) or not isinstance(args, list):
            continue
        pkg, eco = _package_arg(cmd, args)
        if pkg and not _is_pinned(pkg, eco):
            p = f"{ptr}/args"
            out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                               evidence=L(f"서버 {name}: {Path(cmd).name} {pkg} (버전 미고정)", f"server {name}: {Path(cmd).name} {pkg} (version not pinned)")))
    return out


LOCAL_HOSTS = re.compile(r"^http://(localhost|127\.\d+\.\d+\.\d+|\[::1\])(:\d+)?(/|$)", re.I)


@check("mcp_plain_http")
def mcp_plain_http(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        key, url = server_url(srv)
        if isinstance(url, str) and url.lower().startswith("http://") and not LOCAL_HOSTS.match(url):
            p = f"{ptr}/{key}"
            out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                               evidence=L(f"서버 {name}: {short(redact_url(url), 60)}", f"server {name}: {short(redact_url(url), 60)}")))
    return out


# ── Claude Code ───────────────────────────────────
def _cc_settings(ctx, layers=None):
    for d in ctx.docs:
        if d.tool == "claude-code" and d.kind == "settings" and isinstance(d.data, dict):
            if layers is None or d.layer in layers:
                yield d


@check("cc_env_secret")
def cc_env_secret(rule, ctx):
    out = []
    for d in _cc_settings(ctx):
        env = d.data.get("env")
        if not isinstance(env, dict):
            continue
        for k, v in env.items():
            if is_literal_secret(k, v):
                p = f"/env/{escape_pointer_token(k)}"
                sev = "높음" if d.layer in ("project",) else rule["severity"]
                out.append(finding(rule, path=d.path, line=d.line_of(p), pointer=p,
                                   evidence=L(f"{k} = {mask(v)}", f"{k} = {mask(v).en}"), severity=sev,
                                   note=L("저장소에 커밋되는 파일입니다", "This file is committed to the repository") if d.layer == "project" else None))
    return out


@check("cc_project_bypass")
def cc_project_bypass(rule, ctx):
    """프로젝트·로컬 설정의 bypassPermissions — 버전에 따라 효력이 다르다(research/01 1.2, 03 CVE-2026-33068)."""
    out = []
    ver = ctx.tool_version("claude-code")
    for d in _cc_settings(ctx, layers=("project", "local")):
        if (d.data.get("permissions") or {}).get("defaultMode") != "bypassPermissions":
            continue
        p = "/permissions/defaultMode"
        if ver and versions.ge(ver, "2.1.257"):
            sev, note = "낮음", L(f"설치 버전 {ver}에서는 프로젝트·로컬 파일의 이 값이 효력이 없습니다. 다른 도구나 옛 버전이 읽을 수 있어 지우는 것을 권장합니다.",
                                f"In the installed version {ver} this value has no effect in project/local files. Other tools or older versions may still read it, so remove it.")
        elif ver and versions.lt(ver, "2.1.53"):
            sev, note = "높음", L(f"설치 버전 {ver}은 이 값이 있으면 신뢰 대화상자도 생략됩니다(CVE-2026-33068, 2.1.53에서 수정).",
                                f"Installed version {ver} also skips the trust dialog when this value is present (CVE-2026-33068, fixed in 2.1.53).")
        elif ver:
            sev, note = "높음", L(f"설치 버전 {ver}에서는 프로젝트 파일의 이 값이 적용됩니다(2.1.257부터 무시).",
                                f"In installed version {ver} this value in a project file takes effect (ignored from 2.1.257).")
        else:
            sev, note = "중간", L("설치 버전을 알 수 없어 효력 여부를 판정하지 못했습니다.", "The installed version is unknown, so whether this value takes effect could not be determined.")
        out.append(finding(rule, path=d.path, line=d.line_of(p), pointer=p,
                           evidence="defaultMode = bypassPermissions", severity=sev, note=note))
    return out


@check("cc_http_hook")
def cc_http_hook(rule, ctx):
    out = []
    allowed = any((d.data.get("allowedHttpHookUrls") for d in _cc_settings(ctx)))
    if allowed:
        return out
    for d in _cc_settings(ctx):
        for ptr, h in resolve(d.data, "/hooks/*/*/hooks/*"):
            if isinstance(h, dict) and h.get("type") == "http":
                out.append(finding(rule, path=d.path, line=d.line_of(ptr), pointer=ptr,
                                   evidence=L(f"http 훅 → {short(redact_url(h.get('url', '?')), 50)}", f"http hook → {short(redact_url(h.get('url', '?')), 50)}")))
    return out


@check("cc_managed_missing")
def cc_managed_missing(rule, ctx):
    if not any(t.tool == "claude-code" for t in ctx.tools):
        return []
    managed = [d for d in _cc_settings(ctx, layers=("managed",))]
    want = {"permissions.disableBypassPermissionsMode": lambda m: (m.get("permissions") or {}).get("disableBypassPermissionsMode") == "disable",
            "allowManagedHooksOnly": lambda m: m.get("allowManagedHooksOnly") is True,
            "allowManagedMcpServersOnly": lambda m: m.get("allowManagedMcpServersOnly") is True}
    if not managed:
        from ..discover.claude_code import managed_dir
        return [finding(rule, path=managed_dir(ctx) / "managed-settings.json", evidence=L("관리 설정 파일 없음", "no managed settings file"))]
    merged = {}
    for d in managed:
        merged.update(d.data)
    missing = [k for k, ok in want.items() if not ok(merged)]
    if not missing:
        return []
    return [finding(rule, path=managed[0].path, evidence=L("빠진 키: " + ", ".join(missing), "missing keys: " + ", ".join(missing)))]


# ── Codex ─────────────────────────────────────────
def _cx_configs(ctx, layers=None):
    for d in ctx.docs:
        if d.tool == "codex" and d.kind == "config" and isinstance(d.data, dict):
            if layers is None or d.layer in layers:
                yield d


def _cx_scopes(data: dict):
    """최상위와 [profiles.*] 각각을 (접두 포인터, 표)로."""
    yield "", data
    for name, prof in (data.get("profiles") or {}).items():
        if isinstance(prof, dict):
            yield f"/profiles/{escape_pointer_token(name)}", prof


@check("cx_approval_never")
def cx_approval_never(rule, ctx):
    out = []
    for d in _cx_configs(ctx):
        for pre, tbl in _cx_scopes(d.data):
            if tbl.get("approval_policy") != "never":
                continue
            sandbox = tbl.get("sandbox_mode") or d.data.get("sandbox_mode")
            if sandbox == "read-only":
                continue
            p = f"{pre}/approval_policy"
            out.append(finding(rule, path=d.path, line=d.line_of(p), pointer=p,
                               evidence=L(f'approval_policy = "never", sandbox_mode = {short(sandbox) if sandbox else "(기본값)"}',
                                          f'approval_policy = "never", sandbox_mode = {short(sandbox) if sandbox else "(default)"}')))
    return out


@check("cx_mcp_approval_mode")
def cx_mcp_approval_mode(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        if doc.tool != "codex":
            continue
        mode = srv.get("default_tools_approval_mode")
        if isinstance(mode, str) and mode != "prompt":
            p = f"{ptr}/default_tools_approval_mode"
            out.append(finding(rule, path=doc.path, line=doc.line_of(p), pointer=p,
                               evidence=L(f"서버 {name}: default_tools_approval_mode = {mode}", f"server {name}: default_tools_approval_mode = {mode}")))
        for tptr, tool in resolve(srv, "/tools/*"):
            if isinstance(tool, dict) and isinstance(tool.get("approval_mode"), str) and tool["approval_mode"] != "prompt":
                p = f"{ptr}{tptr}/approval_mode"
                out.append(finding(rule, path=doc.path, line=doc.line_of(p), pointer=p,
                                   evidence=L(f"서버 {name} 도구 {tptr.rsplit('/',1)[-1]}: approval_mode = {tool['approval_mode']}",
                                              f"server {name} tool {tptr.rsplit('/',1)[-1]}: approval_mode = {tool['approval_mode']}")))
    return out


@check("cx_shell_env")
def cx_shell_env(rule, ctx):
    if not any(t.tool == "codex" for t in ctx.tools):
        return []
    users = list(_cx_configs(ctx, layers=("user",)))
    data = users[0].data if users else {}
    pol = data.get("shell_environment_policy") or {}
    if pol.get("inherit", "all") in ("none", "core"):   # core는 HOME·PATH 같은 기본 변수만 넘긴다
        return []
    if pol.get("ignore_default_excludes", True) is False:
        return []
    if pol.get("exclude") or pol.get("include_only") or pol.get("filters"):
        return []
    from ..discover.codex import codex_home
    path = users[0].path if users else codex_home(ctx) / "config.toml"
    line = users[0].line_of("/shell_environment_policy") if users else None
    return [finding(rule, path=path, line=line, pointer="/shell_environment_policy",
                    evidence=L("shell_environment_policy 기본값 그대로(제외 규칙 없음)", "shell_environment_policy left at defaults (no exclude rules)"))]


@check("cx_project_hooks_trusted")
def cx_project_hooks_trusted(rule, ctx):
    out = []
    users = list(_cx_configs(ctx, layers=("user",)))
    projects = (users[0].data.get("projects") or {}) if users else {}
    for repo in ctx.repos:
        trust = None
        for k, v in projects.items():
            try:
                if Path(k).expanduser().resolve() == repo and isinstance(v, dict):
                    trust = v.get("trust_level")
            except OSError:
                continue
        if trust != "trusted":
            continue
        for d in ctx.docs:
            if d.tool == "codex" and d.repo == repo and ((d.kind == "hooks" and d.data) or
                                                       (d.kind == "config" and isinstance(d.data, dict) and d.data.get("hooks"))):
                out.append(finding(rule, path=d.path, evidence=L("신뢰한 프로젝트의 훅", "hooks in a trusted project")))
    return out


@check("cx_requirements_missing")
def cx_requirements_missing(rule, ctx):
    if not any(t.tool == "codex" for t in ctx.tools):
        return []
    if any(d.tool == "codex" and d.kind == "requirements" for d in ctx.docs):
        return []
    from ..discover.codex import system_dir
    return [finding(rule, path=system_dir(ctx) / "requirements.toml", evidence=L("requirements.toml 없음", "no requirements.toml"))]


# ── 공통: 알려진 토큰 형식, MCP 범위 ───────────────
from ..redact import find_known_tokens  # noqa: E402


@check("known_tokens")
def known_tokens(rule, ctx):
    """AI 도구 설정 파일과 셸 시작 파일의 줄에서 알려진 토큰 형식을 찾는다."""
    out = []
    sources = [(d.path, d.text, d.tool) for d in ctx.docs if d.text] + [(p, t, "공통") for p, t in ctx.shell_files]
    for path, text, tool in sources:
        for n, line in enumerate(text.splitlines(), 1):
            for kind, tok in find_known_tokens(line):
                out.append(finding(rule, tool=tool, path=path, line=n, evidence=L(f"{kind}: {mask(tok)}", f"{KIND_EN.get(kind, kind)}: {mask(tok).en}")))
    return out


def _is_broad_path(a: str, ctx) -> bool:
    a = a.strip().rstrip("/\\") or "/"
    home = str(ctx.home).rstrip("/")
    return a in ("/", "~", "$HOME", "${HOME}", "${userHome}", "C:", "C:\\", home) or a.lower() in ("c:", "c:\\")


@check("mcp_broad_fs")
def mcp_broad_fs(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        args = [a for a in (srv.get("args") or []) if isinstance(a, str)]
        if not any("filesystem" in a.lower() for a in args + [str(srv.get("command", ""))]):
            continue
        broad = [a for a in args if _is_broad_path(a, ctx)]
        if broad:
            p = f"{ptr}/args"
            out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(p), pointer=p,
                               evidence=L(f"서버 {name}: 접근 범위 {broad[0]}", f"server {name}: access scope {broad[0]}")))
    return out


@check("mcp_repo_servers")
def mcp_repo_servers(rule, ctx):
    out = []
    for doc, name, srv, ptr in mcp_servers(ctx):
        if doc.repo is None:
            continue
        k, url = server_url(srv)
        how = redact_url(url) if url else " ".join([str(srv.get("command", ""))] + redact_args(srv.get("args"))[:3])
        out.append(finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(ptr), pointer=ptr,
                           evidence=L(f"서버 {name}: {short(how, 60)}", f"server {name}: {short(how, 60)}")))
    return out


from ..redact import redact_args  # noqa: E402


# ── Gemini CLI ────────────────────────────────────
@check("gm_mcp_underscore")
def gm_mcp_underscore(rule, ctx):
    return [finding(rule, tool=doc.tool, path=doc.path, line=doc.line_of(ptr), pointer=ptr, evidence=L(f"서버 이름 {name}", f"server name {name}"))
            for doc, name, srv, ptr in mcp_servers(ctx) if doc.tool == "gemini" and "_" in name]


@check("gm_env_override")
def gm_env_override(rule, ctx):
    out = []
    for k in ("GEMINI_CLI_SYSTEM_SETTINGS_PATH", "GEMINI_CLI_SYSTEM_DEFAULTS_PATH"):
        if ctx.env.get(k):
            out.append(finding(rule, evidence=L(f"환경 변수 {k} 설정됨", f"environment variable {k} is set")))
    return out


_DOTENV = re.compile(r"^\s*(?:export\s+)?(GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*['\"]?([^'\"\s$][^'\"\s]{7,})")


@check("gm_dotenv_key")
def gm_dotenv_key(rule, ctx):
    out = []
    for d in ctx.docs:
        if d.tool == "gemini" and d.kind == "dotenv" and d.text:
            for n, line in enumerate(d.text.splitlines(), 1):
                m = _DOTENV.match(line)
                if m:
                    out.append(finding(rule, path=d.path, line=n, evidence=L(f"{m.group(1)}={mask(m.group(2))}", f"{m.group(1)}={mask(m.group(2)).en}")))
    return out


@check("gm_managed_missing")
def gm_managed_missing(rule, ctx):
    if not ctx.has_tool("gemini"):
        return []
    sysdocs = [d for d in ctx.docs if d.tool == "gemini" and d.layer == "system" and isinstance(d.data, dict)]
    ok = any(((d.data.get("security") or {}).get("disableYoloMode") is True or
              (d.data.get("admin") or {}).get("secureModeEnabled") is True) for d in sysdocs)
    if ok:
        return []
    from ..discover.gemini import system_dir
    return [finding(rule, path=sysdocs[0].path if sysdocs else system_dir(ctx) / "settings.json",
                    evidence=L("disableYoloMode·secureModeEnabled 없음", "neither disableYoloMode nor secureModeEnabled is set"))]


# ── Claude Desktop ────────────────────────────────
@check("cd_policy_missing")
def cd_policy_missing(rule, ctx):
    if not ctx.has_tool("claude-desktop"):
        return []
    pol = [d for d in ctx.docs if d.tool == "claude-desktop" and d.kind == "policy" and isinstance(d.data, dict)]
    if not pol:
        return [finding(rule, evidence=L("Claude Desktop 기업 정책을 찾지 못함(macOS 관리 프로파일·Linux 정책 파일)", "no Claude Desktop enterprise policy found (macOS managed profile / Linux policy file)"))]
    data = {}
    for d in pol:
        data.update(d.data)
    if data.get("isLocalDevMcpEnabled") is False and data.get("isDesktopExtensionEnabled") is not False:
        return [finding(rule, path=pol[0].path, evidence=L("로컬 MCP는 껐지만 데스크톱 확장은 켜져 있음(확장으로 로컬 서버 실행 가능)", "local MCP is off but desktop extensions are on (extensions can still run local servers)"))]
    return []


# ── VS Code·Cursor ────────────────────────────────
def _editor_settings(ctx, layers=None):
    for d in ctx.docs:
        if d.tool in ("vscode", "cursor") and d.kind == "settings" and isinstance(d.data, dict):
            if layers is None or d.layer in layers:
                yield d


WHY_EN = {"범용 실행기": "general-purpose runner", "모든 명령에 맞는 패턴": "pattern matching every command",
          "기본 거부 명령을 허용으로 바꿈": "default-deny command switched to allow"}
KIND_EN = {"GitHub 토큰": "GitHub token", "GitHub 세분화 토큰": "GitHub fine-grained token", "Anthropic API 키": "Anthropic API key",
           "OpenAI API 키": "OpenAI API key", "OpenAI 프로젝트 키": "OpenAI project key", "AWS 액세스 키": "AWS access key",
           "Google API 키": "Google API key", "Slack 토큰": "Slack token", "GitLab 토큰": "GitLab token", "npm 토큰": "npm token",
           "Hugging Face 토큰": "Hugging Face token", "Stripe 키": "Stripe key"}

RUNNERS_SHELL = {"bash", "sh", "zsh", "fish", "pwsh", "powershell", "cmd", "python", "python3", "node", "npx",
                 "bun", "deno", "perl", "ruby", "env", "sudo", "xargs"}
DEFAULT_DENY = {"rm", "rmdir", "del", "kill", "curl", "wget", "eval", "chmod", "chown", "/^Remove-Item\\b/i"}
WIDE_RX = re.compile(r"^/(\^)?\.[*+](\$)?/[a-z]*$")


def _approved(v) -> bool:
    return v is True or (isinstance(v, dict) and v.get("approve") is True)


@check("vsc_terminal_autoapprove")
def vsc_terminal_autoapprove(rule, ctx):
    out = []
    for d in _editor_settings(ctx):
        tbl = d.data.get("chat.tools.terminal.autoApprove")
        if not isinstance(tbl, dict):
            continue
        for k, v in tbl.items():
            if not _approved(v):
                continue
            key = k.strip()
            why = None
            if key.split()[0].lower() in RUNNERS_SHELL if key else False:
                why = "범용 실행기"
            elif WIDE_RX.match(key) or key in (".*", "*"):
                why = "모든 명령에 맞는 패턴"
            elif key in DEFAULT_DENY:
                why = "기본 거부 명령을 허용으로 바꿈"
            if why:
                p = f"/chat.tools.terminal.autoApprove/{escape_pointer_token(k)}"
                out.append(finding(rule, tool=d.tool, path=d.path, line=d.line_of(p), pointer=p,
                                   evidence=L(f'"{k}": true ({why})', f'"{k}": true ({WHY_EN[why]})')))
    return out


BROAD_GLOBS = {"**", "**/*", "*", "**/**", "/**"}
BROAD_URLS = {"*", "**", "https://*", "http://*", "*://*", "https://**", "https://*/*", "https://**/*"}


@check("vsc_edits_broad")
def vsc_edits_broad(rule, ctx):
    out = []
    for d in _editor_settings(ctx):
        tbl = d.data.get("chat.tools.edits.autoApprove")
        if isinstance(tbl, dict):
            for k, v in tbl.items():
                if v is True and k.strip() in BROAD_GLOBS:
                    p = f"/chat.tools.edits.autoApprove/{escape_pointer_token(k)}"
                    out.append(finding(rule, tool=d.tool, path=d.path, line=d.line_of(p), pointer=p, evidence=f'"{k}": true'))
    return out


@check("vsc_urls_broad")
def vsc_urls_broad(rule, ctx):
    out = []
    for d in _editor_settings(ctx):
        tbl = d.data.get("chat.tools.urls.autoApprove")
        items = tbl.items() if isinstance(tbl, dict) else [(x, True) for x in tbl] if isinstance(tbl, list) else []
        for k, v in items:
            if isinstance(k, str) and k.strip() in BROAD_URLS and (v is True or isinstance(v, dict)):
                p = "/chat.tools.urls.autoApprove"
                out.append(finding(rule, tool=d.tool, path=d.path, line=d.line_of(p), pointer=p, evidence=f'"{k}"'))
    return out


_ALLOW_ALL = re.compile(r"allow.?all|autopilot|bypass|full.?access|yolo", re.I)


@check("vsc_permission_level")
def vsc_permission_level(rule, ctx):
    out = []
    for d in _editor_settings(ctx):
        for ptr in ("/chat.defaultConfiguration/approvals", "/chat.permissions.default"):
            for p, v in resolve(d.data, ptr):
                if isinstance(v, str) and _ALLOW_ALL.search(v):
                    out.append(finding(rule, tool=d.tool, path=d.path, line=d.line_of(p), pointer=p, evidence=f"{short(v)}"))
    return out


WS_KEYS = re.compile(r"^(chat\.tools\.|chat\.mcp\.|chat\.agent\.|chat\.\w+Locations$|chat\.defaultConfiguration|chat\.permissions|task\.allowAutomaticTasks|security\.workspace\.trust)")


@check("vsc_workspace_ai_keys")
def vsc_workspace_ai_keys(rule, ctx):
    out = []
    for d in _editor_settings(ctx, layers=("workspace",)):
        for k in d.data:
            if WS_KEYS.match(k):
                p = f"/{escape_pointer_token(k)}"
                out.append(finding(rule, tool=d.tool, path=d.path, line=d.line_of(p), pointer=p, evidence=k))
    return out


EDITOR_NAME = {"vscode": "VS Code", "cursor": "Cursor"}


def _trust_off(ctx) -> str | None:
    for d in _editor_settings(ctx, layers=("user", "profile")):
        if d.data.get("security.workspace.trust.enabled") is False:
            return L(f"{EDITOR_NAME[d.tool]} 작업 공간 신뢰 꺼짐", f"{EDITOR_NAME[d.tool]} workspace trust disabled")
        if d.data.get("task.allowAutomaticTasks") == "on":
            return L(f"{EDITOR_NAME[d.tool]} 자동 작업 허용(on)", f"{EDITOR_NAME[d.tool]} automatic tasks allowed (on)")
    if ctx.has_tool("cursor") and not _cursor_trust_on(ctx):
        return L("Cursor 설치됨(작업 공간 신뢰 기본값이 꺼져 있다는 보고)", "Cursor installed (reported to ship with workspace trust off)")
    return None


def _cursor_trust_on(ctx) -> bool:
    return any(d.tool == "cursor" and d.data.get("security.workspace.trust.enabled") is True
               for d in _editor_settings(ctx, layers=("user", "profile")))


@check("vsc_folder_open_task")
def vsc_folder_open_task(rule, ctx):
    out = []
    raised = _trust_off(ctx)
    for d in ctx.docs:
        if d.tool != "vscode" or d.kind != "tasks" or not isinstance(d.data, dict):
            continue
        for p, v in resolve(d.data, "/tasks/*/runOptions/runOn"):
            if v == "folderOpen":
                label = next((t.get("label") for q, t in resolve(d.data, p.rsplit("/", 2)[0]) if isinstance(t, dict)), None)
                out.append(finding(rule, path=d.path, line=d.line_of(p), pointer=p,
                                   evidence=L(f'작업 "{label or "?"}" runOn = folderOpen', f'task "{label or "?"}" runOn = folderOpen'),
                                   severity="높음" if raised else rule["severity"],
                                   note=L(f"함께 확인된 조건: {raised} → 폴더를 열기만 해도 실행될 수 있음",
                                          f"also found: {raised.en} → may run just by opening the folder") if raised else None))
    return out


@check("cur_trust_default")
def cur_trust_default(rule, ctx):
    if not ctx.has_tool("cursor") or _cursor_trust_on(ctx):
        return []
    from ..discover.vscode import user_dir
    return [finding(rule, path=user_dir(ctx, "cursor") / "settings.json",
                    evidence=L("security.workspace.trust.enabled 를 true로 명시하지 않음", "security.workspace.trust.enabled is not explicitly set to true"))]


@check("cur_sandbox_wide")
def cur_sandbox_wide(rule, ctx):
    out = []
    for d in ctx.docs:
        if d.tool == "cursor" and d.kind == "sandbox" and isinstance(d.data, dict):
            for p, v in resolve(d.data, "/additionalReadPaths/*"):
                if isinstance(v, str) and (_is_broad_path(v, ctx) or re.search(r"(\.ssh|\.aws|\.gnupg|\.config/gcloud|\.kube)", v)):
                    out.append(finding(rule, path=d.path, line=d.line_of(p), pointer=p, evidence=L(f"읽기 범위 추가: {v}", f"adds read path: {v}")))
    return out


@check("ext_archived")
def ext_archived(rule, ctx):
    return [finding(rule, tool=t.tool.split("-ext:")[0], path=t.source, evidence=L(f"{t.name} {t.version}", f"{getattr(t.name, 'en', t.name)} {t.version}"))
            for t in ctx.tools if t.tool.endswith("-ext:rooveterinaryinc.roo-cline")]


@check("ext_amazon_q_184")
def ext_amazon_q_184(rule, ctx):
    return [finding(rule, tool=t.tool.split("-ext:")[0], path=t.source, evidence=L(f"{t.name} {t.version}", f"{getattr(t.name, 'en', t.name)} {t.version}"))
            for t in ctx.tools if t.tool.endswith("-ext:amazonwebservices.amazon-q-vscode") and t.version == "1.84.0"]


# ── 버전 ↔ 보안 권고 ─────────────────────────────
from . import advisories as _adv  # noqa: E402


def _adv_finding(rule, tool, path, package, version, hits, active=True, where=""):
    sev, target, ids = _adv.summarize(hits)
    lst = ", ".join(ids[:5])
    ko = f"권고 {len(hits)}건: {lst}" + (" 외" if len(ids) > 5 else "") + ("" if active else " · PATH에서 실행되지 않는 다른 설치")
    en = f"{len(hits)} advisories: {lst}" + (" and more" if len(ids) > 5 else "") + ("" if active else " · another install not on PATH")
    w_en = where.replace("MCP 서버", "MCP server")
    return finding(rule, tool=tool, path=path, severity=sev,
                   evidence=L(f"{where}{package} {version} → {target or '수정 버전 없음'} 이상으로 올려야 함",
                              f"{w_en}{package} {version} → upgrade to {target or '(no fixed version)'} or later"),
                   note=L(ko, en))


@check("version_advisories")
def version_advisories(rule, ctx):
    data = _adv.load()
    out = []
    for t in ctx.tools:
        pkg = _adv.TOOL_PACKAGE.get(t.tool)
        if pkg and t.version:
            hits = _adv.matching(pkg, t.version, data)
            if hits:
                out.append(_adv_finding(rule, t.tool, t.source, pkg, t.version, hits, t.active))
    # 버전을 고정한 MCP 서버(npx 패키지@1.2.3)
    for doc, name, srv, ptr in mcp_servers(ctx):
        cmd, args = srv.get("command"), srv.get("args") or []
        if not isinstance(cmd, str) or not isinstance(args, list):
            continue
        pkg_arg, eco = _package_arg(cmd, args)
        m = _adv.NPM_PINNED.match(pkg_arg or "") if eco == "npm" else None
        if m:
            hits = _adv.matching(m.group(1), m.group(2), data)
            if hits:
                f = _adv_finding(rule, doc.tool, doc.path, m.group(1), m.group(2), hits, where=f"MCP 서버 {name}: ")
                f.line, f.pointer = doc.line_of(f"{ptr}/args"), f"{ptr}/args"
                out.append(f)
    return out


@check("baseline_changes")
def baseline_changes(rule, ctx):
    from .. import baseline
    base = baseline.load(ctx, getattr(ctx, "baseline_path", None))
    if not base:
        return []
    d = baseline.diff(ctx, base)
    out = []
    for kind, label in (("added", "새로 생김"), ("changed", "바뀜")):
        for s in d[kind]:
            label_en = {"added": "added", "changed": "changed"}[kind]
            ko = f"서버 {s['name']} ({label}): {s['how']}" + (f"  ← 이전: {s['before']}" if kind == "changed" else "")
            en = f"server {s['name']} ({label_en}): {s['how']}" + (f"  ← before: {s['before']}" if kind == "changed" else "")
            out.append(finding(rule, tool=s["tool"], evidence=short(L(ko, en), 140),
                               note=L(f"기준선 저장 시각 {base.get('saved_at', '?')}", f"baseline saved at {base.get('saved_at', '?')}"), path=None))
            out[-1].pointer = s["file"]
    return out
