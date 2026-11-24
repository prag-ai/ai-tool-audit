import hashlib
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from ai_tool_audit.engine import load_incidents, load_rules
from ai_tool_audit.report import terminal, to_json

from conftest import FAKE, scan

EXPECTED_RISKY = {
    "CC-PERM-001", "CC-PERM-002", "CC-PERM-003", "CC-PERM-004", "CC-PERM-005", "CC-PERM-006",
    "CC-MCP-001", "CC-HOOK-001", "CC-HOOK-002", "CC-HOOK-003", "CC-SEC-001", "CC-SEC-003", "CC-SEC-006",
    "CX-PERM-001", "CX-PERM-002", "CX-PERM-003", "CX-PERM-004", "CX-PERM-007", "CX-MCP-001",
    "CX-HOOK-002", "CX-HOOK-003", "CX-SEC-001", "CX-SEC-002", "CX-SEC-003", "CX-SEC-004",
    "ALL-MCP-001", "ALL-MCP-002", "ALL-MCP-004", "ALL-SEC-001",
}


def test_risky_finds_expected(risky):
    ctx, findings = scan(*risky)
    got = {f.rule for f in findings}
    assert EXPECTED_RISKY <= got, f"빠진 규칙: {EXPECTED_RISKY - got}"
    assert not any(d.error for d in ctx.docs)


def test_risky_details(risky):
    ctx, findings = scan(*risky)
    by = {}
    for f in findings:
        by.setdefault(f.rule, []).append(f)
    # 버전 판정: 2.1.100은 2.1.257 미만이라 저장소의 bypass가 효력 있음 → 높음
    assert by["CC-PERM-002"][0].severity == "높음"
    # 주석 처리된 별칭은 잡지 않는다
    assert len(by["CC-PERM-004"]) == 1
    # $(…)로 불러오는 키는 평문이 아니다 → OPENAI 하나만
    assert len(by["ALL-SEC-001"]) == 1 and "OPENAI_API_KEY" in by["ALL-SEC-001"][0].evidence
    # 버전 고정된 서버(some-mcp@1.2.3, mcp-foo==1.0.0)는 잡지 않는다
    unpinned = " ".join(f.evidence for f in by["ALL-MCP-002"])
    assert "server-filesystem" in unpinned and "mcp-server-sqlite" in unpinned
    assert "some-mcp" not in unpinned and "mcp-foo" not in unpinned
    # 줄 번호가 나온다
    assert all(f.line for f in by["CC-PERM-005"] + by["CX-PERM-001"])
    # MCP 비밀값: 헤더(Bearer)와 codex env 둘 다
    # MCP 비밀값: claude 헤더(Bearer), codex env, gemini env 값 속 토큰, cursor auth.CLIENT_SECRET
    assert len(by["ALL-MCP-001"]) == 4


def test_safe_has_no_findings(safe):
    ctx, findings = scan(*safe)
    assert findings == [], [(f.rule, f.evidence) for f in findings]
    assert {"claude-code", "codex", "gemini", "vscode", "cursor", "claude-desktop"} <= {t.tool for t in ctx.tools}


def test_version_newer_lowers_bypass(tmp_path, risky):
    home, repo = risky
    (home / ".local/share/claude/versions/2.1.100").rename(home / ".local/share/claude/versions/2.1.300")
    _, findings = scan(home, repo)
    f = next(f for f in findings if f.rule == "CC-PERM-002")
    assert f.severity == "낮음"


def test_enterprise_rules_only_with_flag(safe):
    _, normal = scan(*safe)
    _, ent = scan(*safe, enterprise=True)
    assert not any(f.rule.endswith(("MGMT-001", "MGMT-002")) for f in normal)
    assert {"CC-MGMT-002", "CX-MGMT-001"} <= {f.rule for f in ent}


def _outputs(home, repo):
    ctx, findings = scan(home, repo)
    rules = {r["id"]: r for r in load_rules()}
    return terminal(ctx, findings, rules, load_incidents()) + to_json(ctx, findings)


def test_no_secret_leak(risky):
    out = _outputs(*risky)
    for v in FAKE.values():
        assert v not in out, f"비밀값이 출력에 나옴: {v[:12]}"
    assert "FAKE…(가림)" in out


def test_no_home_path_leak(risky):
    home, repo = risky
    out = _outputs(home, repo)
    assert str(home) not in out


def _tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        st = p.lstat()
        h.update(f"{p}|{st.st_mode}|{st.st_mtime_ns}|{st.st_size}".encode())
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def test_read_only(risky):
    home, repo = risky
    root = home.parent
    before = _tree_hash(root)
    _outputs(home, repo)
    assert _tree_hash(root) == before


def test_no_network(risky, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("네트워크 연결 시도")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    _outputs(*risky)


def test_no_subprocess(risky, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("다른 프로그램 실행 시도")
    monkeypatch.setattr(subprocess, "Popen", boom)
    _outputs(*risky)


def test_rules_json_up_to_date():
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, str(root / "scripts/build_rules.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_multiple_installs_prefers_path(tmp_path):
    from conftest import w
    from ai_tool_audit.discover import discover_all
    from ai_tool_audit.model import Context
    home = tmp_path / "home"
    for node, ver in (("v20.0.0", "0.100.0"), ("v22.0.0", "0.171.0")):
        w(home / f".nvm/versions/node/{node}/lib/node_modules/@openai/codex/package.json", f'{{"version": "{ver}"}}')
        (home / f".nvm/versions/node/{node}/bin").mkdir(parents=True)
    path = str(home / ".nvm/versions/node/v22.0.0/bin")
    ctx = Context(home=home, env={"PATH": path}, os="linux", isolated=True)
    discover_all(ctx)
    assert ctx.tool_version("codex") == "0.171.0"
    assert [t.active for t in ctx.tools if t.tool == "codex"].count(True) == 1


EXPECTED_STAGE2 = {
    "GM-PERM-001", "GM-PERM-002", "GM-PERM-003", "GM-PERM-004", "GM-PERM-006", "GM-SBX-001", "GM-MCP-001",
    "GM-MCP-002", "GM-HOOK-001", "GM-SEC-001", "GM-SEC-003",
    "VSC-PERM-001", "VSC-PERM-002", "VSC-PERM-004", "VSC-PERM-005", "VSC-PERM-006", "VSC-PERM-007", "VSC-PERM-008",
    "VSC-WS-001", "VSC-TRUST-001", "VSC-TRUST-002", "VSC-TASK-001", "VSC-TASK-002", "VSC-MCP-003",
    "VSC-EXT-001", "VSC-EXT-002", "CUR-TRUST-001", "CUR-PERM-001", "CUR-PERM-002", "CUR-SBX-001",
    "ALL-SEC-003", "ALL-MCP-005", "ALL-MCP-006",
}


def test_stage2_risky(risky):
    ctx, findings = scan(*risky)
    got = {f.rule for f in findings}
    assert EXPECTED_STAGE2 <= got, f"빠진 규칙: {EXPECTED_STAGE2 - got}"
    tools = {t.tool for t in ctx.tools}
    assert {"gemini", "vscode", "cursor", "claude-desktop"} <= tools or {"gemini", "vscode", "cursor"} <= tools
    by = {}
    for f in findings:
        by.setdefault(f.rule, []).append(f)
    # VS Code 터미널 자동 승인: bash, /.*/, curl 은 잡고 npm test·rm:false 는 안 잡는다
    ev = " ".join(f.evidence for f in by["VSC-PERM-002"])
    assert "bash" in ev and "/.*/" in ev and "curl" in ev and "npm test" not in ev and '"rm"' not in ev
    # folderOpen 작업은 신뢰 꺼짐 때문에 높음으로 올라간다
    assert by["VSC-TASK-002"][0].severity == "높음"
    # 저장소 .vscode/settings.json 의 자동 승인도 잡는다(사용자+저장소 두 곳)
    assert len(by["VSC-PERM-001"]) == 2
    # 알려진 토큰: 셸 export, gemini env 값 속 토큰, .gemini/.env의 AWS 키
    kinds = " ".join(f.evidence for f in by["ALL-SEC-003"])
    assert "GitHub 토큰" in kinds and "AWS 액세스 키" in kinds


def test_stage2_no_leak(risky):
    from conftest import AWS_KEY, GH_TOKEN
    out = _outputs(*risky)
    assert GH_TOKEN not in out and AWS_KEY not in out


# ── 3단계: 버전 대조, 기준선, 보고서 ──────────────
def test_version_range_parsing():
    from ai_tool_audit.checks.versions import in_range
    assert in_range("0.1.10", ">= 0.0.5, <= 0.1.15")
    assert not in_range("0.1.16", ">= 0.0.5, <= 0.1.15")
    assert in_range("2.1.52", "< 2.1.53") and not in_range("2.1.53", "< 2.1.53")
    assert in_range("1.84.0", "= 1.84.0") and not in_range("1.85.0", "= 1.84.0")
    assert not in_range("1.0.0", None)


def test_version_advisories(risky):
    from ai_tool_audit.checks import advisories
    _, findings = scan(*risky)
    vf = [f for f in findings if f.rule == "ALL-VER-001"]
    # 시험 픽스처의 Claude Code 2.1.100 은 실제 권고 데이터에서 영향 범위에 든다
    expected = advisories.matching("@anthropic-ai/claude-code", "2.1.100")
    assert expected, "권고 데이터에 2.1.100 해당 건이 있어야 시험이 의미 있다"
    cc = [f for f in vf if f.tool == "claude-code"]
    assert len(cc) == 1 and "이상으로 올려야 함" in cc[0].evidence and f"권고 {len(expected)}건" in cc[0].note


def test_safe_versions_clean(safe):
    _, findings = scan(*safe)
    assert not [f for f in findings if f.rule == "ALL-VER-001"]


def test_baseline_detects_added_and_changed(risky):
    import json
    from ai_tool_audit import baseline
    from ai_tool_audit.discover import discover_all
    from ai_tool_audit.model import Context
    home, repo = risky
    ctx, _ = scan(home, repo)
    baseline.save(ctx)
    assert (home / ".ai-tool-audit/baseline.json").exists()
    # 설정을 바꾼다: 서버 하나 명령 변경 + 새 서버 추가(SANDWORM 방식)
    cj = home / ".claude.json"
    d = json.loads(cj.read_text())
    d["mcpServers"]["fs"]["args"] = ["-y", "@evil/fs"]
    d["mcpServers"]["dev-utils"] = {"command": "node", "args": [str(home / ".dev-utils/server.js")]}
    cj.write_text(json.dumps(d))
    _, findings = scan(home, repo)
    base = [f for f in findings if f.rule == "ALL-BASE-001"]
    ev = " ".join(f.evidence for f in base)
    assert "dev-utils (새로 생김)" in ev and "fs (바뀜)" in ev
    assert str(home) not in ev


def test_reports_md_html(risky, tmp_path):
    from ai_tool_audit.engine import load_incidents, load_rules
    from ai_tool_audit.report.document import markdown
    from ai_tool_audit.report.ledger import html
    from conftest import AWS_KEY, GH_TOKEN
    home, repo = risky
    ctx, findings = scan(home, repo)
    rules = {r["id"]: r for r in load_rules()}
    for fn in (markdown, html):
        out = fn(ctx, findings, rules, load_incidents())
        for v in list(FAKE.values()) + [GH_TOKEN, AWS_KEY]:
            assert v not in out
        assert str(home) not in out
        assert str(home)[:25] not in out, "잘린 홈 경로가 남음(가리기 전에 자른 경우)"
        assert "먼저 고칠 것" in out and "읽은 파일" in out
    h = html(ctx, findings, rules, load_incidents())
    assert h.startswith("<!doctype html>")
    assert h.count("<div class='row'>") == 2 * len(findings)      # 한국어판 + 영어판
    assert "data-l='ko'" in h and "data-l='en'" in h and "navigator.language" in h
    assert "<script src" not in h and "https://fonts" not in h    # 외부 요청 없음


HANGUL = __import__("re").compile(r"[가-힣]")


def test_english_output_has_no_korean(risky):
    """영어 출력에 한국어가 섞이면 번역이 빠진 것이다(픽스처 이름은 모두 영문)."""
    from ai_tool_audit.engine import load_incidents, load_rules
    from ai_tool_audit.report.document import markdown
    from ai_tool_audit.report.ledger import _sheet
    ctx, findings = scan(*risky)
    rules, incs = {r["id"]: r for r in load_rules()}, load_incidents()
    for out in (terminal(ctx, findings, rules, incs, lang="en"), markdown(ctx, findings, rules, incs, lang="en"),
                _sheet(ctx, findings, rules, incs, "en")):
        bad = [ln for ln in out.splitlines() if HANGUL.search(ln)]
        assert not bad, bad[:5]


def test_detect_lang(tmp_path):
    from ai_tool_audit.i18n import detect_lang
    assert detect_lang({"LANG": "ko_KR.UTF-8"}) == "ko"
    assert detect_lang({"LANG": "en_US.UTF-8"}) == "en"
    assert detect_lang({"LANG": "en_US.UTF-8", "AI_TOOL_AUDIT_LANG": "ko"}) == "ko"
    import plistlib
    pref = tmp_path / "Library/Preferences"
    pref.mkdir(parents=True)
    (pref / ".GlobalPreferences.plist").write_bytes(plistlib.dumps({"AppleLanguages": ["ko-KR", "en-US"]}))
    assert detect_lang({"LANG": "en_US.UTF-8"}, tmp_path, "macos") == "ko"
