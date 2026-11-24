# 기여 안내

## 개발 환경

```bash
uv sync                                  # 개발 의존성(pytest, pyyaml) 설치
uv run python scripts/build_rules.py     # rules/*.yaml → JSON, docs/규칙목록.md 생성
uv run pytest -q                         # 시험
```

## 규칙 추가하기

1. `rules/<도구>.yaml`에 규칙을 적습니다. 필드는 아래와 같습니다.

```yaml
- id: CC-PERM-005                 # 도구-분류-번호(세 자리)
  tool: claude-code               # 여러 도구가 같은 키를 쓰면 tools: [vscode, cursor]
  title: 모든 셸 명령을 묻지 않고 실행하도록 허용(Bash 전체)
  severity: 높음                   # 높음·중간·낮음·정보
  status: 확정                     # 공식 문서로 확인하지 못했으면 검토필요
  docs: {kind: [settings]}        # 어느 설정 파일에 적용할지
  detect: {type: list_match, pointer: /permissions/allow, equals: [Bash], regex: ['Bash\(\s*\*\s*\)']}
  why: 왜 위험한지(한국어 한두 문장)
  fix: 어떻게 고치는지
  incidents: [nx-s1ngularity-2025]   # data/incidents.yaml의 ID
  refs: [https://공식 문서 주소]
```

2. `detect.type`은 `equals`, `present`, `list_match`, `file_mode`, `file_exists`, `shell_regex`, `check` 가운데 고릅니다. 틀에 맞지 않으면 `src/ai_tool_audit/checks/`에 함수를 만들고 `type: check`, `name: 함수이름`으로 연결합니다.
3. 근거 사건이 있으면 `data/incidents.yaml`에 날짜·원문 주소·한 줄 요약을 적습니다. **원문을 직접 확인한 사실만** 씁니다.
4. `tests/conftest.py`의 위험 설정(`make_risky`)에 걸려야 할 예를, 안전 설정(`make_safe`)에 걸리면 안 되는 예를 넣고 시험을 추가합니다.
5. 영어 문구를 `rules/en.yaml`(규칙의 title·why·fix)과 `data/incidents_en.yaml`(사건의 title·summary)에 넣습니다. 빠지면 빌드가 실패합니다. 점검 함수에서 결과 문구를 만들 때는 `L("한국어", "English")`로 두 언어를 함께 적습니다.
6. `scripts/build_rules.py`를 실행해 JSON과 규칙 목록 문서를 다시 만듭니다. 영어 출력에 한국어가 섞이면 시험(`test_english_output_has_no_korean`)이 실패합니다.

## 지켜야 할 것

- 점검기는 파일을 바꾸지 않고, 네트워크를 쓰지 않고, 다른 프로그램을 실행하지 않습니다. 이 원칙을 깨는 변경은 받지 않습니다.
- 출력에 비밀값·홈 경로가 나가지 않아야 합니다. 시험 픽스처의 가짜 토큰은 소스에 통째로 적지 말고 조립하세요(`tests/conftest.py` 참고).
- 공식 문서로 확인하지 못한 설정은 `status: 검토필요`로 둡니다.
