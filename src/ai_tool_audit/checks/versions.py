"""버전 비교(외부 라이브러리 없이). 1.2.3, 2.1.331, 0.39.0-alpha 정도를 다룬다."""
from __future__ import annotations

import re


def parse(v: str) -> tuple:
    v = v.strip().lstrip("v")
    main, _, pre = v.partition("-")
    nums = [int(x) for x in re.findall(r"\d+", main)[:4]]
    while len(nums) < 3:
        nums.append(0)
    # 정식판이 사전판보다 크다
    return (*nums, 0 if pre else 1, pre)


def lt(a: str, b: str) -> bool:
    return parse(a) < parse(b)


def ge(a: str, b: str) -> bool:
    return not lt(a, b)


def in_range(version: str, spec: str | None) -> bool:
    """GitHub 권고의 범위 표기('>= 0.0.5, <= 0.1.15', '< 2.1.53', '= 1.84.0')에 맞는가."""
    if not spec:
        return False
    for part in spec.split(","):
        part = part.strip()
        for op in (">=", "<=", ">", "<", "="):
            if part.startswith(op):
                ref = part[len(op):].strip()
                a, b = parse(version), parse(ref)
                ok = {">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b, "=": a == b}[op]
                if not ok:
                    return False
                break
        else:
            return False
    return True
