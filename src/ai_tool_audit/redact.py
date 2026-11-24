"""출력에 비밀값·사용자 이름이 나가지 않게 가린다."""
from __future__ import annotations

import re
from pathlib import Path

# 이름만 보고 비밀값으로 보는 키(대소문자 무시)
SECRET_NAME = re.compile(r"(api[_-]?key|token|secret|password|passwd|auth|credential|bearer|private[_-]?key)", re.I)
# 값에 환경 변수 참조만 있으면 비밀값이 아니다: ${VAR}, ${env:VAR}, ${input:x}, $VAR
ENV_REF = re.compile(r"^\s*(\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*)\s*$")
# 헤더 값의 "Bearer ${TOKEN}"처럼 참조를 섞은 경우
HAS_ENV_REF = re.compile(r"\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*")


def is_literal_secret(name: str, value) -> bool:
    """키 이름이 비밀값 같고, 값이 환경 변수 참조가 아닌 실제 문자열이면 True."""
    if not isinstance(value, str) or not value.strip():
        return False
    if find_known_tokens(value):
        return True
    if not SECRET_NAME.search(name):
        return False
    if ENV_REF.match(value):
        return False
    stripped = HAS_ENV_REF.sub("", value).strip()
    stripped = re.sub(r"^(Bearer|Basic|Token)\s*", "", stripped, flags=re.I).strip()
    return len(stripped) >= 8


def mask(value: str):
    """앞 4글자만 남기고 가린다."""
    from .i18n import L
    v = str(value)
    if len(v) <= 4:
        return L("****", "****")
    return L(v[:4] + "…(가림)", v[:4] + "…(masked)")


def display_path(path: Path | None, home: Path) -> str:
    if path is None:
        return "-"
    try:
        rel = Path(path).resolve().relative_to(Path(home).resolve())
        return "~/" + rel.as_posix() if str(rel) != "." else "~"
    except ValueError:
        return Path(path).as_posix()


_FLAG = re.compile(r"^--?([A-Za-z0-9_-]+)$")
_LONG_RANDOM = re.compile(r"^(?=.*\d)(?=.*[A-Za-z])[A-Za-z0-9_\-+/=.]{24,}$")


def redact_args(args) -> list[str]:
    """MCP 실행 인자에서 비밀값처럼 보이는 것을 가린다: --token X, --api-key=X, KEY=X, 긴 무작위 문자열."""
    out, hide_next = [], False
    for a in [str(x) for x in (args or [])]:
        if hide_next:
            out.append(mask(a))
            hide_next = False
            continue
        m = _FLAG.match(a)
        if m and SECRET_NAME.search(m.group(1)):
            out.append(a)
            hide_next = True
            continue
        if "=" in a:
            k, v = a.split("=", 1)
            if SECRET_NAME.search(k) and v and not ENV_REF.match(v):
                out.append(f"{k}={mask(v)}")
                continue
        if _LONG_RANDOM.match(a) and "/" not in a:
            out.append(mask(a))
            continue
        out.append(a)
    return out


def redact_url(url: str) -> str:
    """주소의 사용자 정보와 비밀값 같은 쿼리 값을 가린다."""
    u = re.sub(r"(https?://)[^/@\s]+@", r"\1***@", str(url))
    return re.sub(r"([?&])([^=&]+)=([^&]+)",
                  lambda m: f"{m.group(1)}{m.group(2)}={mask(m.group(3)) if SECRET_NAME.search(m.group(2)) else m.group(3)}", u)


# 알려진 토큰 형식(서비스별 공개 접두어 기준으로 직접 작성). 값 자체가 이 모양이면 키 이름과 상관없이 비밀값으로 본다.
KNOWN_TOKENS = [
    ("GitHub 토큰", r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b"),
    ("GitHub 세분화 토큰", r"\bgithub_pat_[A-Za-z0-9_]{60,255}\b"),
    ("Anthropic API 키", r"\bsk-ant-(?:api\d\d|admin\d\d|oat\d\d)-[A-Za-z0-9_\-]{60,}"),
    ("OpenAI API 키", r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_\-]{16,}T3BlbkFJ[A-Za-z0-9_\-]{16,}"),
    ("OpenAI 프로젝트 키", r"\bsk-proj-[A-Za-z0-9_\-]{40,}"),
    ("AWS 액세스 키", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("Google API 키", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("Slack 토큰", r"\bxox[abprs]-[0-9A-Za-z-]{10,}"),
    ("GitLab 토큰", r"\bglpat-[0-9A-Za-z_\-]{20,}"),
    ("npm 토큰", r"\bnpm_[A-Za-z0-9]{36}\b"),
    ("Hugging Face 토큰", r"\bhf_[A-Za-z]{30,}\b"),
    ("Stripe 키", r"\b[sr]k_live_[0-9A-Za-z]{20,}"),
]
KNOWN_TOKEN_RES = [(n, re.compile(rx)) for n, rx in KNOWN_TOKENS]


def find_known_tokens(text: str):
    """[(토큰 종류, 일치 문자열)]"""
    out = []
    for name, rx in KNOWN_TOKEN_RES:
        for m in rx.finditer(text):
            out.append((name, m.group(0)))
    return out
