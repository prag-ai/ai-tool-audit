"""점검기 전체가 함께 쓰는 자료형."""
from __future__ import annotations

import os
import platform
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import jsonc

SEVERITIES = ["높음", "중간", "낮음", "정보"]


@dataclass
class ConfigDoc:
    """읽어 들인 설정 파일 하나."""
    tool: str            # claude-code, codex …
    kind: str            # settings, state, mcpjson, config, requirements, hooks …
    layer: str           # user, project, local, managed, profile, system
    path: Path
    fmt: str             # json, toml
    data: Any = None
    lines: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    repo: Path | None = None
    text: str = ""
    mcp: list[str] = field(default_factory=list)   # 이 파일 안 MCP 서버 위치(포인터 패턴)

    def line_of(self, pointer: str) -> int | None:
        if self.fmt == "json":
            # 정확한 포인터가 없으면 가장 가까운 부모의 줄
            p = pointer
            while p:
                if p in self.lines:
                    return self.lines[p]
                p = p.rsplit("/", 1)[0]
            return None
        return toml_line_of(self.text, pointer)


@dataclass
class Tool:
    """설치가 확인된 AI 도구."""
    tool: str
    name: str
    version: str | None
    source: Path | None
    active: bool = True        # PATH에서 실제로 실행되는 설치인가(같은 도구가 여러 벌일 때)


@dataclass
class Finding:
    rule: str
    severity: str
    status: str
    tool: str
    title: str
    path: Path | None = None
    line: int | None = None
    pointer: str | None = None
    evidence: str | None = None
    note: str | None = None


@dataclass
class Context:
    home: Path
    env: dict[str, str]
    os: str                    # macos, linux, windows
    repos: list[Path] = field(default_factory=list)
    enterprise: bool = False
    docs: list[ConfigDoc] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)
    read_files: list[Path] = field(default_factory=list)
    shell_files: list[tuple[Path, str]] = field(default_factory=list)
    isolated: bool = False     # 시험용: 시스템 경로를 home/_sys 아래로 돌린다
    baseline_path: Path | None = None   # 기준선 파일(없으면 ~/.ai-tool-audit/baseline.json)

    def sys(self, path: str | Path) -> Path:
        """시스템 경로(/etc, /Library, C:/ProgramData 등). 격리 모드면 home/_sys 아래로."""
        p = Path(path)
        if not self.isolated:
            return p
        parts = [x for x in p.parts if x not in ("/", "\\") and not x.endswith(":\\") and not x.endswith(":/") and not re.fullmatch(r"[A-Za-z]:", x)]
        return self.home / "_sys" / Path(*parts)

    @classmethod
    def current(cls, repos=None, enterprise=False) -> "Context":
        sysname = platform.system()
        os_name = {"Darwin": "macos", "Windows": "windows"}.get(sysname, "linux")
        return cls(home=Path.home(), env=dict(os.environ), os=os_name,
                   repos=[Path(r).expanduser().resolve() for r in (repos or [])],
                   enterprise=enterprise)

    def has_tool(self, tool: str) -> bool:
        return any(t.tool == tool for t in self.tools)

    def user_app_dir(self, name: str) -> Path:
        """앱별 사용자 설정 폴더: macOS ~/Library/Application Support/<이름>, Windows %APPDATA%/<이름>, Linux ~/.config/<이름>."""
        if self.os == "macos":
            return self.home / "Library/Application Support" / name
        if self.os == "windows":
            return Path(self.env.get("APPDATA") or self.home / "AppData/Roaming") / name
        return Path(self.env.get("XDG_CONFIG_HOME") or self.home / ".config") / name

    def tool_version(self, tool: str) -> str | None:
        cands = [t for t in self.tools if t.tool == tool and t.version]
        for t in cands:
            if t.active:
                return t.version
        return cands[0].version if cands else None

    # 파일 읽기는 모두 여기를 거친다(읽은 파일 목록을 보고서에 싣기 위해).
    def read_text(self, path: Path) -> str | None:
        try:
            if not path.is_file():
                return None
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            return None
        self.read_files.append(path)
        return text

    def load(self, tool: str, kind: str, layer: str, path: Path, fmt: str,
             repo: Path | None = None, mcp: list[str] | None = None) -> ConfigDoc | None:
        text = self.read_text(path)
        if text is None:
            return None
        doc = ConfigDoc(tool=tool, kind=kind, layer=layer, path=path, fmt=fmt, repo=repo, text=text,
                        mcp=list(mcp or []))
        try:
            if fmt == "json":
                doc.data, doc.lines = jsonc.loads(text) if text.strip() else ({}, {})
            elif fmt == "toml":
                doc.data = tomllib.loads(text)
            elif fmt == "text":
                doc.data = text
        except (ValueError, tomllib.TOMLDecodeError) as e:
            doc.error = str(e)
        self.docs.append(doc)
        return doc


# ── TOML 줄 번호(근사) ─────────────────────────────
def toml_line_of(text: str, pointer: str) -> int | None:
    """'/mcp_servers/foo/env/KEY' 같은 포인터의 줄을 찾는다.
    tomllib는 줄 번호를 주지 않으므로, 표 머리([a.b])를 따라가며 마지막 키를 찾는다."""
    parts = [p.replace("~1", "/").replace("~0", "~") for p in pointer.strip("/").split("/") if p]
    if not parts:
        return None
    lines = text.splitlines()
    full = re.compile(r"^\s*\[\[?\s*" + r"\s*\.\s*".join(
        rf'(?:"{re.escape(t)}"|{re.escape(t)})' for t in parts) + r"\s*\]\]?\s*$")
    for i, ln in enumerate(lines):
        if full.match(ln):
            return i + 1
    key = parts[-1]
    key_re = re.compile(rf'^\s*"?{re.escape(key)}"?\s*=')
    # 1) 부모 표 머리를 찾고 그 아래에서 키를 찾는다
    for cut in range(len(parts) - 1, -1, -1):
        table = parts[:cut]
        rest = parts[cut:]
        if not table:
            start = 0
        else:
            hdr = re.compile(r"^\s*\[\[?\s*" + r"\s*\.\s*".join(
                rf'(?:"{re.escape(t)}"|{re.escape(t)})' for t in table) + r"\s*\]\]?\s*$")
            idx = next((i for i, ln in enumerate(lines) if hdr.match(ln)), None)
            if idx is None:
                continue
            start = idx + 1
            if len(rest) == 0:
                return idx + 1
        first = rest[0]
        first_re = re.compile(rf'^\s*"?{re.escape(first)}"?\s*[=.]')
        for i in range(start, len(lines)):
            if i > start and re.match(r"^\s*\[", lines[i]):
                break
            if (len(rest) == 1 and key_re.match(lines[i])) or (len(rest) > 1 and first_re.match(lines[i])):
                return i + 1
    for i, ln in enumerate(lines):
        if key_re.match(ln):
            return i + 1
    return None
