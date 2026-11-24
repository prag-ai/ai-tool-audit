"""여러 도구가 함께 쓰는 위치: npm 전역 설치 폴더, 셸 시작 파일."""
from __future__ import annotations

import json
from pathlib import Path

from ..model import Context

SHELL_FILES = [".zshrc", ".zprofile", ".zshenv", ".bashrc", ".bash_profile", ".profile",
               ".bash_aliases", ".config/fish/config.fish"]


def npm_global_roots(ctx: Context) -> list[Path]:
    h = ctx.home
    cands: list[Path] = []
    cands += sorted((h / ".nvm/versions/node").glob("*/lib/node_modules"))
    cands += [h / ".npm-global/lib/node_modules", h / ".local/lib/node_modules",
              ctx.sys("/opt/homebrew/lib/node_modules"), ctx.sys("/usr/local/lib/node_modules"),
              ctx.sys("/usr/lib/node_modules")]
    appdata = ctx.env.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / "npm/node_modules")
    prefix = ctx.env.get("NPM_CONFIG_PREFIX") or ctx.env.get("npm_config_prefix")
    if prefix:
        cands.append(Path(prefix) / "lib/node_modules")
    seen, out = set(), []
    for c in cands:
        if c.is_dir() and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _path_node_roots(ctx: Context) -> list[Path]:
    """PATH에 있는 노드 bin 폴더에 대응하는 전역 node_modules(실제로 실행되는 쪽)."""
    sep = ";" if ctx.os == "windows" else ":"
    out = []
    for d in ctx.env.get("PATH", "").split(sep):
        if not d:
            continue
        p = Path(d)
        for cand in (p.parent / "lib/node_modules", p / "node_modules"):
            if cand.is_dir():
                out.append(cand.resolve())
    return out


def npm_package_installs(ctx: Context, package: str) -> list[tuple[str | None, Path, bool]]:
    """전역 npm 패키지 설치 목록 [(버전, package.json, PATH에서 실행되는 쪽인가)]. 실행되는 쪽이 먼저."""
    active_roots = _path_node_roots(ctx)
    hits = []
    for root in npm_global_roots(ctx):
        pj = root / package / "package.json"
        text = ctx.read_text(pj)
        if not text:
            continue
        try:
            ver = json.loads(text).get("version")
        except ValueError:
            ver = None
        active = any(root.resolve() == a for a in active_roots)
        hits.append((ver, pj, active))
    hits.sort(key=lambda h: not h[2])
    if hits and not any(h[2] for h in hits):
        hits[0] = (hits[0][0], hits[0][1], True)   # PATH로 판별 못 하면 첫 번째를 기준으로
    return hits


def load_shell_files(ctx: Context) -> None:
    """셸 시작 파일은 규칙의 패턴 일치에만 쓴다(내용을 출력하지 않는다)."""
    for name in SHELL_FILES:
        p = ctx.home / name
        text = ctx.read_text(p)
        if text is not None:
            ctx.shell_files.append((p, text))


def mac_app_version(ctx: Context, app: str) -> tuple[str | None, Path] | None:
    """/Applications/<앱>.app 의 Info.plist에서 버전을 읽는다(macOS)."""
    import plistlib
    for base in (ctx.sys("/Applications"), ctx.home / "Applications"):
        plist = base / app / "Contents/Info.plist"
        try:
            if not plist.is_file():
                continue
            with plist.open("rb") as fh:
                info = plistlib.load(fh)
            ctx.read_files.append(plist)
            return info.get("CFBundleShortVersionString") or info.get("CFBundleVersion"), base / app
        except (OSError, ValueError, plistlib.InvalidFileException):
            continue
    return None


def extension_dirs(ctx: Context, root: Path) -> list[tuple[str, str, Path]]:
    """VS Code류 확장 폴더 → [(확장 ID, 버전, 경로)]. 폴더 이름 'publisher.name-1.2.3[-platform]'."""
    import re
    out = []
    try:
        entries = sorted(root.iterdir()) if root.is_dir() else []
    except OSError:
        return out
    for p in entries:
        m = re.match(r"^([A-Za-z0-9-]+\.[A-Za-z0-9._-]+?)-(\d+\.\d+\.\d+[A-Za-z0-9.+-]*)$", p.name)
        if p.is_dir() and m:
            ver = re.sub(r"-(darwin|win32|linux|alpine|web)(-[a-z0-9]+)?$", "", m.group(2))   # 플랫폼 꼬리 제거
            out.append((m.group(1).lower(), ver, p))
    return out
