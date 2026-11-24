"""한국어·영어 두 언어 지원.

- Msg: 한국어 문자열이면서 .en 에 영어를 함께 들고 있는 문자열. 점검 결과의 내용·참고 문구에 쓴다.
- detect_lang: 보고서 언어를 정한다. macOS는 시스템 선호 언어(파일을 읽기만 함), 그 밖에는 LANG 계열 환경 변수.
"""
from __future__ import annotations

import os
from pathlib import Path


class Msg(str):
    """str(한국어) + .en(영어)"""

    def __new__(cls, ko: str, en: str | None = None):
        obj = str.__new__(cls, ko)
        obj.en = ko if en is None else en
        return obj


def L(ko: str, en: str) -> Msg:
    return Msg(ko, en)


def pick(x, lang: str):
    """출력할 언어의 문자열을 고른다(Msg가 아니면 그대로)."""
    if x is None:
        return None
    return getattr(x, "en", x) if lang == "en" else str(x)


def detect_lang(env: dict | None = None, home: Path | None = None, os_name: str | None = None) -> str:
    env = env if env is not None else dict(os.environ)
    explicit = env.get("AI_TOOL_AUDIT_LANG")
    if explicit in ("ko", "en"):
        return explicit
    if os_name == "macos" and home is not None:
        import plistlib
        try:
            with (home / "Library/Preferences/.GlobalPreferences.plist").open("rb") as fh:
                langs = plistlib.load(fh).get("AppleLanguages") or []
            if langs:
                return "ko" if str(langs[0]).lower().startswith("ko") else "en"
        except (OSError, ValueError, plistlib.InvalidFileException):
            pass
    for k in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        v = env.get(k)
        if v:
            return "ko" if v.lower().startswith("ko") else "en"
    return "en"
