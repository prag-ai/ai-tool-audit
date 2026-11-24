"""JSON / JSONC 읽기 — 값과 함께 'JSON 포인터 → 줄 번호' 표를 돌려준다.

VS Code·Cursor 설정은 주석(//, /* */)과 끝 쉼표를 허용하는 JSONC다.
표준 json 모듈은 줄 번호를 주지 않아서, 보고서에 "몇 번째 줄"을 적으려고 직접 읽는다.
"""
from __future__ import annotations


class JsoncError(ValueError):
    def __init__(self, msg: str, line: int):
        super().__init__(f"{msg} (줄 {line})")
        self.line = line


def escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


class _Parser:
    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.line = 1
        self.lines: dict[str, int] = {}

    # ── 공백·주석 ─────────────────────────────
    def _advance(self, n: int = 1) -> None:
        for _ in range(n):
            if self.s[self.i] == "\n":
                self.line += 1
            self.i += 1

    def _ws(self) -> None:
        s = self.s
        while self.i < len(s):
            c = s[self.i]
            if c in " \t\r\n﻿":
                self._advance()
            elif s.startswith("//", self.i):
                while self.i < len(s) and s[self.i] != "\n":
                    self.i += 1
            elif s.startswith("/*", self.i):
                end = s.find("*/", self.i + 2)
                if end < 0:
                    raise JsoncError("닫히지 않은 주석", self.line)
                self._advance(end + 2 - self.i)
            else:
                break

    def _peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    # ── 값 ────────────────────────────────────
    def value(self, ptr: str):
        self._ws()
        self.lines[ptr] = self.line
        c = self._peek()
        if c == "{":
            return self._object(ptr)
        if c == "[":
            return self._array(ptr)
        if c == '"':
            return self._string()
        return self._literal()

    def _object(self, ptr: str) -> dict:
        self._advance()  # {
        out: dict = {}
        while True:
            self._ws()
            if self._peek() == "}":
                self._advance()
                return out
            if self._peek() != '"':
                raise JsoncError("객체 키가 와야 합니다", self.line)
            key_line = self.line
            key = self._string()
            self._ws()
            if self._peek() != ":":
                raise JsoncError("':'가 와야 합니다", self.line)
            self._advance()
            child = f"{ptr}/{escape_pointer_token(key)}"
            out[key] = self.value(child)
            self.lines[child] = key_line  # 키가 있는 줄을 기준으로
            self._ws()
            c = self._peek()
            if c == ",":
                self._advance()
            elif c == "}":
                continue
            else:
                raise JsoncError("',' 또는 '}'가 와야 합니다", self.line)

    def _array(self, ptr: str) -> list:
        self._advance()  # [
        out: list = []
        while True:
            self._ws()
            if self._peek() == "]":
                self._advance()
                return out
            out.append(self.value(f"{ptr}/{len(out)}"))
            self._ws()
            c = self._peek()
            if c == ",":
                self._advance()
            elif c == "]":
                continue
            else:
                raise JsoncError("',' 또는 ']'가 와야 합니다", self.line)

    def _string(self) -> str:
        s = self.s
        self._advance()  # "
        buf = []
        while True:
            if self.i >= len(s):
                raise JsoncError("닫히지 않은 문자열", self.line)
            c = s[self.i]
            if c == '"':
                self._advance()
                return "".join(buf)
            if c == "\\":
                nxt = s[self.i + 1 : self.i + 2]
                simple = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
                if nxt in simple:
                    buf.append(simple[nxt])
                    self.i += 2
                elif nxt == "u":
                    hexs = s[self.i + 2 : self.i + 6]
                    code = int(hexs, 16)
                    self.i += 6
                    if 0xD800 <= code < 0xDC00 and s.startswith("\\u", self.i):
                        low = int(s[self.i + 2 : self.i + 6], 16)
                        code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
                        self.i += 6
                    buf.append(chr(code))
                else:
                    raise JsoncError("잘못된 이스케이프", self.line)
            else:
                if c == "\n":
                    self.line += 1
                buf.append(c)
                self.i += 1

    def _literal(self):
        s = self.s
        for word, val in (("true", True), ("false", False), ("null", None)):
            if s.startswith(word, self.i):
                self.i += len(word)
                return val
        j = self.i
        while j < len(s) and s[j] in "+-0123456789.eE":
            j += 1
        tok = s[self.i : j]
        if not tok:
            raise JsoncError(f"알 수 없는 값 {s[self.i:self.i+10]!r}", self.line)
        self.i = j
        try:
            return int(tok)
        except ValueError:
            return float(tok)


def loads(text: str) -> tuple[object, dict[str, int]]:
    """JSONC 문자열 → (값, 포인터별 줄 번호). 최상위 포인터는 ''."""
    p = _Parser(text)
    val = p.value("")
    p._ws()
    if p.i < len(p.s):
        raise JsoncError("값 뒤에 남은 글자", p.line)
    return val, p.lines
