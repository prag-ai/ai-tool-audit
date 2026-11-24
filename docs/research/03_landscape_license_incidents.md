# 03. 기존 도구 지형 · 라이선스 · 기술 기준 · 근거 사건

> 확인 시점: 2026-11-24. 별 수·최근 커밋은 GitHub API(`gh api repos/…`)로 이 날 읽은 값이다.
> 원칙: 공식 문서·저장소·원문 보도에서 확인한 것만 적고 출처를 단다. 확인하지 못한 것은 **미확인**으로 적는다.
> 「README 기준」은 저장소 README에 적힌 주장이고, 「코드 확인」은 소스를 직접 받아 읽은 것이다.

---

## 0. 한눈에

- MCP 서버·스킬을 훑는 스캐너는 이미 많다. 그중 가장 큰 Snyk Agent Scan(옛 Invariant mcp-scan)은 **분석에 Snyk API가 필요하고, 도구 설명·스킬 본문을 외부로 보낸다.**
- 설정 파일을 오프라인으로 읽는 작은 도구(Nexqor mcp-audit, guardmcp 등)도 있다. 다만 대부분 **MCP 설정(`mcpServers`)만** 본다. Claude Code의 권한 모드·훅·`ANTHROPIC_BASE_URL`, Gemini CLI의 폴더 신뢰, Codex의 `approval_policy`·`sandbox_mode`, VS Code·Cursor의 작업 공간 신뢰·자동 작업을 **도구 여러 개에 걸쳐 한 번에** 보는 도구는 이번 조사 범위에서 찾지 못했다.
- 근거로 쓸 공개 사건은 충분하다. 특히 Claude Code(GHSA 30건), Cursor(33건), Gemini CLI, Codex CLI, mcp-remote, MCP Inspector는 **공식 보안 권고에 고친 버전이 적혀 있어** "설치된 버전이 권고보다 낮은가"를 오프라인으로 판정할 수 있다.

---

## 1. 겹치는 기존 오픈소스

### 1-1. 요약 표

| 프로젝트 | 무엇을 보나 | 외부로 보내는가 | 라이선스 | 최근 커밋(push) | 별 |
|---|---|---|---|---|---|
| [snyk/agent-scan](https://github.com/snyk/agent-scan) (옛 invariantlabs-ai/mcp-scan) | MCP 서버의 도구·프롬프트·리소스, 에이전트 스킬. 프롬프트 인젝션, 도구 섀도잉, 독성 흐름(toxic flow), 숨은 유니코드, 스킬 악성 패턴 등 | **보낸다.** 도구 이름·설명, MCP 서버 설정과 서명, 스킬 본문을 Snyk 분석 API로 전송(비밀값은 가린 뒤). `SNYK_TOKEN` 필요 | Apache-2.0 | 2026-11-23 | 3,276 |
| [cisco-ai-defense/mcp-scanner](https://github.com/cisco-ai-defense/mcp-scanner) | MCP 서버·도구. YARA 규칙, LLM 분석, Cisco AI Defense API 세 엔진. 바이너리는 VirusTotal 해시 조회 | **선택에 따라 보낸다.** API 분석기는 Cisco로, LLM 분석기는 지정한 LLM 제공자로, 바이너리 해시는 VirusTotal로. YARA·정적(JSON 파일) 모드는 오프라인 | Apache-2.0 | 2026-11-23 | 1,125 |
| [BerkantACUN/guardmcp](https://github.com/BerkantACUN/guardmcp) (npm `guardmcp`) | MCP 설정 33개 규칙: 하드코딩 비밀, 버전 미고정 `npx`, 평문 `http://`, TLS 끔, 파일시스템 루트 범위, 도구 포이즈닝(`--live`), **러그풀 고정(pin)**, 섀도 MCP 서버, OWASP MCP Top 10 매핑, SARIF | 기본 스캔은 안 보낸다. `--live`는 서버를 띄워 목록만 받고, `--registry`는 npm 레지스트리를 조회한다(코드 확인: `src/registry/npm.ts`) | Apache-2.0 | 2026-09-24 | 2 |
| [raghav1924/guardmcp](https://github.com/raghav1924/guardmcp) (같은 이름 다른 프로젝트) | Claude Desktop·Cursor·Windsurf MCP 설정. 규칙 SEC01~05(비밀, 셸 실행, 파일시스템, 스키마 없음, 프롬프트 탈취), 0~100 점수, HTML 보고서 | README상 의존성 없는 로컬 실행. 네트워크 코드는 **미확인** | MIT | 2026-11-18 | 0 |
| [apisec-inc/mcp-audit](https://github.com/apisec-inc/mcp-audit) | Claude Desktop·Cursor·VS Code·Windsurf·Zed의 MCP 설정 속 비밀·API 엔드포인트·모델 목록, AI-BOM, 서버 소스의 "프롬프트 입력→셸 실행" 패턴, SARIF | **선택적으로 보낸다.** 스캔 끝에 이메일을 입력하면 요약을 `mcp-audit-api.vercel.app`로 보낸다(코드 확인: `commands/scan.py`). `trust` 명령은 npm·GitHub API를 조회 | MIT | 2026-08-18 | 168 |
| [Nexqor/mcp-audit](https://github.com/Nexqor/mcp-audit) | MCP 설정 정적 점검: 실행 시 원격 코드(`curl \| sh`), `--privileged` 컨테이너, 숨은 문자, 평문 비밀, 넓은 파일시스템, 평문 HTTP, **`alwaysAllow`/`autoApprove`**, 도구 포이즈닝(tools/list 덤프 입력), 버전 미고정 | 보내지 않는다(코드 확인: 표준 라이브러리 `argparse·json·os·re·sys·unicodedata`만 import, 서버 실행 없음) | MIT | 2026-11-21 | 0 |
| [Nexqor/ai-detection-rules](https://github.com/Nexqor/ai-detection-rules) | Sigma 규칙 7개: Bedrock LLMjacking, LiteLLM 관리 키 엔드포인트, **AI 에이전트가 SSH 키·`.env`를 읽는 프로세스**, 웹훅·터널로 나가는 연결, **MCP 설정 파일 변경**, 노출된 Ollama | 해당 없음(탐지 규칙 묶음) | MIT | 2026-11-21 | 0 |
| [Shubhmane9503/sigma-ai-abuse-detections](https://github.com/Shubhmane9503/sigma-ai-abuse-detections) | Sigma 규칙 8개: LLMjacking, AI 키 남용, 섀도 AI, 에이전트·MCP 변조. 양성·음성 로그로 CI 시험 | 해당 없음 | 코드 MIT + **규칙은 DRL 1.1**(`LICENSE-RULES`) | 2026-11-21 | 0 |
| [riseandignite/mcp-shield](https://github.com/riseandignite/mcp-shield) | MCP 설정을 찾아 서버에 붙어 도구 설명의 인젝션·섀도잉·민감 파일 언급 탐지 | 선택. `--claude-api-key`를 주면 도구 설명을 Anthropic API로 보내 분석 | MIT | 2025-04-26(정체) | 555 |
| [Pantheon-Security/medusa](https://github.com/Pantheon-Security/medusa) | 범용 코드 스캐너. v2026.7부터 **저장소의 `.claude/`를 클론 전에 검사**: 위험한 훅(`curl\|bash` 등), 넓은 권한(`Bash(*)`, `bypassPermissions`), 와일드카드 도구 서브에이전트. `secrets scan`은 Claude·Cursor·Copilot·Gemini 대화 기록 속 키를 찾음. SARIF | `secrets scan`은 "No network, no telemetry"(README) | **AGPL-3.0** | 2026-08-10 | 1,025 |
| [alexgreensh/repo-forensics](https://github.com/alexgreensh/repo-forensics) | AI 에이전트 플러그인·스킬·MCP 서버 저장소를 설치 전 감사 | README상 "No cloud API. No telemetry". 패키지 이름 조회는 나감 | NOASSERTION(라이선스 판별 불가, **미확인**) | 2026-11-14 | 209 |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | 에이전트 스킬 설치 전 검사. 정적 분석 + 선택적 LLM 분석, OSV.dev CVE 조회 | 선택. LLM 분석·OSV 조회 시 외부 연결, `--no-llm` 가능 | Apache-2.0 | 2026-11-24 | 27,459 |
| [trailofbits/mcp-context-protector](https://github.com/trailofbits/mcp-context-protector) | 스캐너가 아니라 **실행 중 래퍼**. 서버 설정을 처음 본 값으로 고정(TOFU), 바뀌면 도구 호출 차단, 응답 격리 | 기본은 로컬. 가드레일 제공자 선택 시 외부 | Apache-2.0 | 2026-04-14 | 228 |
| [sidhpurwala-huzaifa/mcp-security-scanner](https://github.com/sidhpurwala-huzaifa/mcp-security-scanner) | 실행 중인 MCP 서버를 침투 시험(인증·전송·도구·프롬프트·리소스) | 대상 서버에만 연결 | Apache-2.0 | 2026-09-10 | 21 |
| [badchars/mcp-security-scanner](https://github.com/badchars/mcp-security-scanner) | MCP 서버 형태의 스캐너(도구 55개): 런타임 점검, SAST, 설정 감사, 의존성, OWASP MCP Top 10 | README상 "No API keys. No external calls" | MIT | 2026-09-16 | 5 |
| [depalmar/ai-dfir-toolkit](https://github.com/depalmar/ai-dfir-toolkit) | AI 관련 사고 대응용 Sigma·YARA·Suricata 규칙, **AI 코딩 에이전트가 남기는 엔드포인트 아티팩트 목록**, 조사 안내 | 해당 없음 | Apache-2.0 | 2026-11-23 | 186 |

참고로 이름이 겹치지만 성격이 다른 것:
- [stufently/claude-code-config-audit](https://github.com/stufently/claude-code-config-audit): 이름과 달리 Claude Code 계정 정보를 **지우는** 정리 스크립트다. 감사 도구가 아니다.
- `mcp-security-scanner`라는 이름은 저장소가 여럿이다(위 두 개 외에 aws-samples, DMontgomery40 등). 사용자가 말한 것이 어느 것인지 **미확인**이라 활동량이 있는 두 개를 실었다.

### 1-2. Invariant Labs mcp-scan → Snyk Agent Scan

- 2025-06-24 Snyk가 Invariant Labs(ETH 취리히 분사, 스위스)를 인수했다고 발표했다. 원문: [Snyk 보도자료](https://snyk.io/news/snyk-acquires-invariant-labs-to-accelerate-agentic-ai-security-innovation)
- 저장소 `invariantlabs-ai/mcp-scan`은 지금 `snyk/agent-scan`으로 넘어간다(GitHub API가 같은 저장소를 돌려줌).
- CHANGELOG에 `0.4.3 Rename to agent-scan.`, `0.4.4 Use Snyk API Key for analysis.`가 있다. PyPI의 옛 패키지 `mcp-scan`은 0.4.3(2026-03-02)이 마지막이고, 새 패키지는 `snyk-agent-scan`이다(PyPI 최신 0.7.0, 2026-11-18. 저장소에는 0.7.1 릴리스 병합 커밋이 2026-11-23에 있음).
- **외부 전송**: README의 "Agent Scan validates discovered components with local checks and the Agent Scan API. It sends … MCP server configurations and signatures, tool names and descriptions, and skill content. Secrets in configuration values and text are redacted before transmission." 무료 등급은 하루 사용량 제한이 있다.
- **서버 실행**: 도구 설명을 얻으려고 설정에 적힌 stdio 명령을 실제로 실행한다. 대화형 실행에서는 서버마다 y/n 동의를 받고, 백그라운드·CI에서는 `--dangerously-run-mcp-servers` 없이는 stdio 서버를 띄우지 않는다. 원격 서버 요청은 링크 로컬·클라우드 메타데이터 주소(`169.254.0.0/16` 등)를 거부한다.
- **자동 발견 대상**: Claude Code/Desktop, Cursor, Gemini CLI, Windsurf, GitHub Copilot 등.
- 출처: [README](https://github.com/snyk/agent-scan/blob/main/README.md), [CHANGELOG](https://github.com/snyk/agent-scan/blob/main/CHANGELOG.md), [이슈 코드](https://github.com/snyk/agent-scan/blob/main/docs/issue-codes.md)

### 1-3. 우리와 겹치는 점 / 빈 곳

| 점검 영역 | 이미 하는 도구 | 우리 쪽 판단 |
|---|---|---|
| MCP 설정 속 평문 비밀 | guardmcp, Nexqor mcp-audit, apisec mcp-audit, raghav guardmcp | 겹친다. 규칙을 새로 짜기보다 gitleaks 규칙을 출처 표시하고 가져온다(2장) |
| `npx`·`uvx` 버전 미고정, `curl \| sh` 실행 | guardmcp(MCPG-104·105), Nexqor | 겹친다 |
| 도구 설명 포이즈닝·숨은 유니코드 | Snyk(E001·W021), Cisco, guardmcp `--live`, mcp-shield, Nexqor(덤프 입력) | 겹친다. 대부분 **서버를 실행**하거나 **외부 분석**을 쓴다 |
| tools/list 해시 고정(러그풀) | guardmcp `pin`, ToB context-protector, 옛 mcp-scan(설명만 md5) | 겹친다. 다만 해시 대상 필드가 도구마다 다르다(3-3절) |
| MCP `alwaysAllow`/`autoApprove` | Nexqor | 부분 겹침 |
| **Claude Code 권한 모드·훅·`enableAllProjectMcpServers`·`ANTHROPIC_BASE_URL`** | medusa(저장소 `.claude/`만, AGPL) | **빈 곳.** 홈 디렉터리 실제 설정까지 보는 도구는 못 찾음 |
| **Gemini CLI `--yolo`·폴더 신뢰, Codex `approval_policy`·`sandbox_mode`** | 없음(조사 범위) | **빈 곳** |
| **VS Code·Cursor 작업 공간 신뢰, `task.allowAutomaticTasks`, `chat.tools.autoApprove`, `.vscode/tasks.json`의 `runOn: folderOpen`** | 없음(조사 범위) | **빈 곳** |
| **설치된 AI 도구·확장 버전 ↔ 공개 보안 권고 대조** | 없음(조사 범위. SkillSpector는 스킬 의존성 CVE만) | **빈 곳.** 4장 권고표를 그대로 규칙으로 쓸 수 있다 |
| AI CLI 대화 기록 속 키 | medusa `secrets scan`(AGPL) | 겹치지만 라이선스 때문에 코드는 못 가져온다 |
| SIEM 탐지(Sigma) | Nexqor, Shubhmane, ai-dfir-toolkit | 겹치지 않음. 우리는 엔드포인트 정적 점검. 보고서에서 "이 설정이면 이 Sigma 규칙을 켜라"로 연결만 가능 |
| 한국어 보고서 | 없음 | **빈 곳** |
| 기본값에서 네트워크 0·서버 실행 0 | Nexqor(정적), guardmcp 기본 | 부분 겹침. 다섯 도구를 가로지르면서 이 성질을 지키는 도구는 못 찾음 |

---

## 2. 가져다 쓸 수 있는 것의 라이선스

전제: Apache 재단의 제3자 라이선스 분류([ASF Resolved](https://www.apache.org/legal/resolved.html))에서 MIT·Apache-2.0·BSD-3-Clause는 **Category A**(포함 가능), AGPL-3.0·GPL은 **Category X**(포함 불가), CC-BY-SA는 수정하지 않은 미디어만 조건부(Category B)다. 우리 프로젝트가 ASF 프로젝트는 아니지만, Apache-2.0 프로젝트에 무엇을 넣어도 되는지 판단하는 기준으로 쓴다.

| 대상 | 라이선스 | 우리 Apache-2.0 저장소에 | 지킬 것 |
|---|---|---|---|
| gitleaks 기본 규칙 [`config/gitleaks.toml`](https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml) | 저장소 전체 MIT(`Copyright (c) 2019 Zachary Rice`). 규칙 파일에 별도 라이선스 표기는 없다 | **포함·수정 가능** | MIT 저작권 문구와 허가 문구를 함께 배포. `THIRD_PARTY_NOTICES`(또는 `LICENSE` 부록)에 원문 넣고, 가져온 규칙 파일 머리에 출처 URL·커밋 해시를 적는다. 파일 머리말이 "auto-generated. Do not edit manually"라 원본은 `cmd/generate/config/`의 Go 코드다. 최신 릴리스 v8.30.1(2026-03-21) |
| [Yelp/detect-secrets](https://github.com/Yelp/detect-secrets) 플러그인 정규식 | Apache-2.0. 저장소 최상단에 `NOTICE` 파일은 없다 | **포함·수정 가능** | Apache-2.0 4조: 라이선스 사본 동봉, 수정한 파일에 바꿨다는 표시, 원 저작권 표기 유지. 마지막 릴리스 1.5.0(2024-05-06)이라 규칙이 오래됐을 수 있음 |
| [trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog) 탐지기 | **AGPL-3.0** | **넣지 않는다** | 코드·정규식 복사 금지. "참고 문헌" 링크만 |
| [mazen160/secrets-patterns-db](https://github.com/mazen160/secrets-patterns-db) | **CC-BY-SA-4.0** | 넣지 않는 쪽을 권함 | 동일조건변경허락이라 수정본에 같은 라이선스가 붙는다. 쓰려면 별도 데이터 파일로 원본 그대로 두고 출처 표시. Apache-2.0 코드와 섞지 않는다 |
| SigmaHQ 규칙, Shubhmane 규칙 | **DRL 1.1**([원문](https://github.com/SigmaHQ/Detection-Rule-License)) | 포함 가능하나 조건 있음 | 규칙을 배포하면 `author` 필드, 규칙 URI, DRL 표기를 유지해야 한다. **규칙으로 데이터를 판정할 때 그 결과 메시지에도 author를 남겨야 한다.** 보고서에 규칙 작성자를 찍는 칸이 필요하다 |
| Nexqor 규칙·mcp-audit | MIT | 포함 가능 | MIT 문구 동봉 |
| guardmcp 규칙 설명·해시 방식 | Apache-2.0 | 포함 가능 | 4조 조건. 아이디어 참고만이면 의무 없음 |
| medusa | **AGPL-3.0** | **넣지 않는다** | 규칙 목록을 보고 같은 점검을 우리 말로 새로 쓰는 것은 가능(표현이 아니라 사실·아이디어). 정규식 복사는 금지 |
| MCP Python SDK `mcp` | MIT | 의존성으로 사용 가능 | 배포 바이너리(예: PyInstaller)에 넣을 때만 MIT 문구 동봉 |

정리: **gitleaks(MIT)와 detect-secrets(Apache-2.0)는 출처 표시만 하면 가져와도 된다.** AGPL(trufflehog, medusa)은 링크만, CC-BY-SA는 섞지 않는다. Sigma 규칙을 싣는다면 보고서 출력에 author를 남기는 칸을 처음부터 설계한다.

---

## 3. 기술 기준

### 3-1. SARIF 2.1.0

**표준(OASIS) 최소 필수 필드** — [SARIF 2.1.0 스키마](https://json.schemastore.org/sarif-2.1.0.json)를 직접 읽어 확인했다.

| 객체 | 필수 |
|---|---|
| 최상위 `sarifLog` | `version`("2.1.0"), `runs` |
| `run` | `tool` |
| `tool` | `driver` |
| `toolComponent`(driver) | `name` |
| `result` | `message` |
| `message` | `text` 또는 `id` 중 하나 |
| `reportingDescriptor`(rule) | `id` |
| `physicalLocation` | `artifactLocation` 또는 `address` 중 하나 |

명세 원문: [OASIS SARIF v2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)

**GitHub code scanning이 요구하는 것** — 표준보다 많다. 출처는 GitHub 문서 원본 마크다운([sarif-support.md](https://github.com/github/docs/blob/main/content/code-security/reference/code-scanning/sarif-files/sarif-support.md), 게시 페이지 [SARIF support for code scanning](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)).

- 최상위: `$schema`, `version`(2.1.0만 지원), `runs[]`
- `run`: `tool.driver`, `results[]`
- `driver`: `name`, `rules[]`
- `rule`: `id`, `shortDescription.text`, `fullDescription.text`, `help.text`
- `result`: `message.text`, `locations[]`, `partialFingerprints`
- `location`: `physicalLocation`
- `physicalLocation`: `artifactLocation.uri`, `region.startLine`, `region.startColumn`, `region.endLine`, `region.endColumn`
- 필수 값은 빈 문자열이면 안 된다.
- `partialFingerprints`는 `primaryLocationLineHash`만 쓴다. `upload-sarif` 액션은 없으면 채워 주지만, REST API(`/code-scanning/sarifs`)로 올릴 때 없으면 중복 경고가 생길 수 있다.
- 위험도는 `properties.security-severity`(0.0 초과~10.0). 9.0 초과 critical, 7.0~8.9 high, 4.0~6.9 medium, 0.1~3.9 low.
- `runAutomationDetails.id`의 마지막 `/` 앞이 category다(같은 커밋에 여러 분석을 올릴 때 구분).
- 한도: gzip 압축 후 파일당 10MB, 파일당 run 20개, run당 결과 25,000개(상위 5,000개만 표시), run당 규칙 25,000개, 규칙당 태그 20개(10개만 표시).
- 업로드 조건([upload-sarif-file.md](https://github.com/github/docs/blob/main/content/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file.md)): 워크플로에 `permissions: security-events: write`. 비공개·내부 저장소는 GitHub Code Security 기능이 켜져 있어야 code scanning을 쓸 수 있다.

**우리 도구에 주는 함의**
- code scanning은 **저장소 안 파일**을 가리키는 결과용이다. `~/.claude.json`, `~/.cursor/mcp.json` 같은 홈 디렉터리 설정은 저장소 경로가 없다. 이런 결과를 GitHub에 올렸을 때 어떻게 표시되는지는 **미확인**. → SARIF 출력은 저장소 범위 파일(`.mcp.json`, `.claude/settings.json`, `.vscode/*.json`, `.cursor/mcp.json`, `.github/workflows/*.yml`)에만 쓰고, PC 전체 점검은 한국어 보고서(HTML/MD)와 JSON으로 내는 것이 맞다.
- JSON 설정은 줄·열이 의미가 약하다. guardmcp는 지문을 "규칙 + 파일 + JSON 논리 경로"로 만든다(README). 우리도 `region`은 원본에서 찾은 줄·열로 채우되, 지문은 JSON 포인터로 만드는 편이 재포맷에 강하다.

### 3-2. MCP 공식 Python SDK

- 패키지명: **`mcp`**(PyPI). 최신 **2.3.0**(2026-10-02 업로드), MIT. v1 계열도 병행 유지(1.30.0, 2026-09-07). 출처: [PyPI mcp](https://pypi.org/project/mcp/), [릴리스](https://github.com/modelcontextprotocol/python-sdk/releases)
- 요구 Python: README는 "Python 3.11+", `pyproject.toml`은 `requires-python = ">=3.10"`. **둘이 다르다.** 우리는 3.11 이상으로 잡는 것이 안전하다.
- v2부터 서버 클래스가 `FastMCP` → **`MCPServer`**(`from mcp.server import MCPServer`)로 바뀌었다(README 예제, Cisco mcp-scanner README에도 "mcp 2.0" 언급). 변경 안내: [What's new in v2](https://py.sdk.modelcontextprotocol.io/whats-new/)
- `MCPServer.run()`의 기본 transport는 `stdio`다(코드 확인: `src/mcp/server/mcpserver/server.py`의 `run(self, transport: Literal["stdio"] = ...)` 오버로드).

stdio 서버 최소 예 — **mcp 2.3.0, Python 3.12.13에서 실제로 띄우고 `tools/list`를 받아 확인했다.**

```python
from mcp.server import MCPServer

mcp = MCPServer("ai-tool-audit")


@mcp.tool()
def audit_summary(path: str = ".") -> str:
    """Return a read-only audit summary for the given path."""
    return f"scanned {path}: 0 findings"


if __name__ == "__main__":
    mcp.run()  # 기본 transport = stdio
```

같은 패키지의 클라이언트(`mcp.client.stdio.stdio_client` + `ClientSession`)로 위 서버를 실행해 받은 `tools/list` 결과(필드는 와이어 이름, `by_alias=True`):

```json
[{"description":"Return a read-only audit summary for the given path.","inputSchema":{"properties":{"path":{"default":".","title":"Path","type":"string"}},"title":"audit_summaryArguments","type":"object"},"name":"audit_summary","outputSchema":{"properties":{"result":{"title":"Result","type":"string"}},"required":["result"],"title":"audit_summaryOutput","type":"object"}}]
```

이 문자열(키 정렬, 구분자 `,` `:`)의 SHA-256은 `64aeceedb6ddebb3763cfdb6fda470e6869f1c357c7b1ea734b51b44db1a61e2`였다. 주의: pydantic 기본 덤프는 `input_schema`처럼 파이썬 이름을 쓴다. 해시는 반드시 와이어 이름(`by_alias=True`)으로 계산해야 다른 구현과 맞는다.

### 3-3. tools/list 해시 고정을 다른 도구는 어떻게 했나

| 구현 | 무엇을 해시하나 | 어디에 저장 | 언제 비교 | 출처 |
|---|---|---|---|---|
| 옛 mcp-scan(v0.3.20) | **도구 `description`만** `md5`. 키는 `서버명.종류.도구명` | `~/.mcp-scan`(로컬) | 다음 스캔 때. 바뀌면 이전 설명과 시각을 보여 줌 | 코드 확인: [`models.py` `hash_entity`](https://github.com/snyk/agent-scan/blob/v0.3.20/src/mcp_scan/models.py), [`Storage.py` `check_and_update`](https://github.com/snyk/agent-scan/blob/v0.3.20/src/mcp_scan/Storage.py) |
| Snyk Agent Scan(현재 0.7.x) | 로컬 변경 탐지 코드(`check_server_changed` 등)는 소스에서 찾지 못함. "signatures"를 API로 보냄 | `--storage-file`(기본 `~/.mcp-scan`) 옵션은 남아 있음 | 서버 쪽에서 비교하는지 **미확인** | [README](https://github.com/snyk/agent-scan/blob/main/README.md) |
| guardmcp | 도구를 이름순 정렬 → `{name, description, properties(최상위 속성의 key·type·enum·pattern·maxLength), annotations}`를 `JSON.stringify` → `sha256`. 설정 수준 해시는 `command`·`args`·`url`과 env **이름만**(값 제외) | 저장소에 커밋하는 `.mcpguard-lock.json` | `scan` 때 MCPG-501(설정)·MCPG-502(실제 도구 목록, `--live`) | 코드 확인: [`src/pin/tools-hash.ts`](https://github.com/BerkantACUN/guardmcp/blob/main/src/pin/tools-hash.ts), README "Rug-pull pinning" |
| Trail of Bits mcp-context-protector | 서버 instructions·도구 설명·입력 스키마를 **의미 비교**(순서 무시). 서버 식별은 실행 명령 문자열 또는 URL | `~/.mcp-context-protector/servers.json` | 연결 시작 때와 `notifications/tools/list_changed`를 받을 때. 다르면 승인 전까지 도구 호출 차단 | [README](https://github.com/trailofbits/mcp-context-protector) |
| Cursor(클라이언트) | 설정 수준. `mcpServers` 항목이 **바뀔 때마다** 재승인 요구(CVE-2025-54136 수정 후) | 클라이언트 내부 | 설정 변경 시 | [GHSA-24mc-g4xr-4395](https://github.com/cursor/cursor/security/advisories/GHSA-24mc-g4xr-4395) |

빈틈과 교훈:
- 옛 mcp-scan은 설명만 해시해서 **입력 스키마나 새 매개변수 추가는 못 잡는다.**
- guardmcp는 최상위 속성만 보고 `title`, `outputSchema`, `required`, 중첩 스키마는 해시에 넣지 않는다(코드 확인). 숨은 지시를 중첩 속성의 `description`에 넣으면 놓칠 수 있다.
- guardmcp 주석에 따르면, 예전에 필드를 NUL로 이어 붙이는 방식이 **충돌**을 일으켜 JSON 직렬화로 바꿨다. 필드 경계가 모호한 방식은 쓰지 않는다.
- Claude Code의 플러그인 해시 고정 우회(CVE-2026-86063): 고정한 SHA와 이름이 같은 브랜치를 만들면 `git checkout`이 브랜치로 풀렸다. "고정값을 받았다"가 아니라 **"실제 결과가 고정값과 같은지"를 다시 확인**해야 한다. 출처: [GHSA-pq7j-f95f-qfcv](https://github.com/advisories/GHSA-pq7j-f95f-qfcv)
- tools/list를 받으려면 **서버를 실행해야 한다**(stdio). "읽기 전용 점검" 원칙과 부딪힌다. Snyk은 서버별 동의, guardmcp는 `--live` 선택 + 환경 변수 정리(설정에 적힌 env만 전달) + 이중 타임아웃 + `tools/call` 금지로 풀었다. 우리도 기본값은 **실행하지 않음**, 해시 고정은 명시적 옵션으로 둔다.

우리 쪽 제안(설계 입력): 와이어 이름 그대로의 도구 객체 전체(`name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`)를 키 정렬 JSON으로 만들어 SHA-256. 서버 단위 해시와 **도구 단위 해시를 함께** 저장해 어느 도구가 바뀌었는지 보여 준다. 키 정렬 규칙은 RFC 8785(JCS)를 따를지 결정이 필요하다(다른 도구와 호환되는 공개 형식은 아직 없음 — 이번 조사 범위에서 **미확인**).

---

## 4. 점검 규칙의 근거가 될 공개 사건

각 행의 마지막 칸은 "어떤 설정·상태였으면 피해가 커졌는가"다. 우리 점검 규칙 후보로 바로 옮길 수 있게 썼다.

### 4-1. 사건 표

| 날짜 | 사건 | 한 줄 요약 | 관련 설정·상태 | 피해를 키운 조건 | 원문 |
|---|---|---|---|---|---|
| 2025-08-26 | **Nx s1ngularity** (GHSA-cxm3-wv7p-598c, CVE-2025-10894) | 탈취한 npm 토큰으로 악성 `nx` 배포. `postinstall`이 설치된 `claude`·`gemini`·`q` CLI에 위험 플래그를 붙여 파일시스템을 뒤져 비밀을 찾게 함 | `--dangerously-skip-permissions`, `--yolo`, `--trust-all-tools`. Nx Console VS Code 확장(18.6.30~18.65.1)이 `latest`를 설치하며 감염 경로가 됨 | AI CLI가 로그인된 채 설치돼 있고, 셸에서 바로 권한 확인 없이 실행되는 상태. `gh` 토큰·npm 토큰이 로컬에 있는 상태 | [Nx 권고](https://github.com/nrwl/nx/security/advisories/GHSA-cxm3-wv7p-598c), [StepSecurity](https://www.stepsecurity.io/blog/supply-chain-security-alert-popular-nx-build-system-package-compromised-with-data-stealing-malware), [Wiz](https://www.wiz.io/blog/s1ngularity-supply-chain-attack) |
| 2025-09-17 배포 / 2025-09-25 공지 | **postmark-mcp 악성 업데이트** (MAL-2025-47604) | 정상 15개 버전 뒤 1.0.16에서 보내는 모든 메일을 `phan@giftshop[.]club`로 숨은 참조 | npm 패키지를 MCP 서버로 실행하는 설정 | `npx postmark-mcp`처럼 **버전 미고정**으로 매번 최신을 받는 상태. 도구 정의 변화가 아니라 코드 변화라 설명 해시로는 못 잡음 | [OSV MAL-2025-47604](https://osv.dev/vulnerability/MAL-2025-47604), [The Register](https://www.theregister.com/2025/09/29/postmark_mcp_server_code_hijacked/). Koi 원문(`koi.security/blog/…`)은 현재 다른 곳으로 이동돼 직접 읽지 못함 |
| 2025-07-17 배포 / 2025-07-23 공지 | **Amazon Q Developer VS Code 확장 1.84.0** (AWS-2025-015, CVE-2025-8217) | 과하게 넓은 GitHub 토큰으로 악성 커밋이 릴리스에 들어감. 홈 디렉터리 파일과 AWS 자원을 지우라는 프롬프트를 Q CLI에 넘김. 문법 오류로 실행은 실패 | `q` CLI에 `--trust-all-tools`, `--no-interactive` | 확장 1.84.0이 설치돼 있고, Q CLI가 설치·로그인돼 있고, AWS 프로필이 로컬에 있는 상태. 1.85.0 이상으로 올려야 함 | [AWS-2025-015](https://aws.amazon.com/security/security-bulletins/AWS-2025-015/), [The Register](https://www.theregister.com/2025/07/24/amazon_q_ai_prompt/) |
| 2025-07-09 | **mcp-remote** CVE-2025-6514 (CVSS 9.6) | 악성 원격 MCP 서버가 조작한 `authorization_endpoint`를 돌려주면 `open()`이 이를 실행 | `npx mcp-remote <URL>`을 MCP 설정에 넣는 방식 | 0.0.5~0.1.15 사용, 신뢰하지 않는 원격 서버 URL, 평문 `http://`(중간자). 윈도에서는 임의 명령 실행 | [JFrog](https://jfrog.com/blog/2025-6514-critical-mcp-remote-rce-vulnerability/), [GHSA-6xpm-ggf7-wc3p](https://github.com/advisories/GHSA-6xpm-ggf7-wc3p) |
| 2025-06-13 | **MCP Inspector** CVE-2025-49596 | Inspector 프록시와 클라이언트 사이 인증이 없어 인증 없이 stdio 명령 실행 | `@modelcontextprotocol/inspector` 실행 상태 | 0.14.1 미만을 띄워 둔 상태 | [GHSA-7f8r-222p-6f5g](https://github.com/advisories/GHSA-7f8r-222p-6f5g) |
| 2025-09-08 | MCP Inspector CVE-2025-58444 | 신뢰하지 않는 MCP 서버에 연결하면 XSS를 거쳐 명령 실행 가능 | 같음 | 0.16.6 미만 | [GHSA-g9hg-qhmf-q45m](https://github.com/advisories/GHSA-g9hg-qhmf-q45m) |
| 2025-08-01 | **Cursor MCPoison** CVE-2025-54136 | 한 번 승인한 MCP 설정을 저장소에서 몰래 바꿔도 재승인을 묻지 않음 | 저장소의 `.cursor/mcp.json` | 공유 저장소에 MCP 설정이 커밋돼 있고 협업자가 쓰기 권한이 있는 상태 | [GHSA-24mc-g4xr-4395](https://github.com/cursor/cursor/security/advisories/GHSA-24mc-g4xr-4395) |
| 2025-08-02 | **Cursor CurXecute** CVE-2025-54135 | 간접 프롬프트 인젝션으로 에이전트가 없던 `.cursor/mcp.json`을 만들어 새 MCP 서버(=임의 명령) 등록 | 작업 공간의 `.cursor/mcp.json` 부재 + 에이전트 파일 쓰기 | 작업 공간에 MCP 설정 파일이 없는 상태(새로 만드는 것은 승인 없이 됐음) | [GHSA-4cxx-hrm3-49rm](https://github.com/cursor/cursor/security/advisories/GHSA-4cxx-hrm3-49rm) |
| 2025-09-10 | **Cursor 작업 공간 신뢰 기본 꺼짐** (Oasis) | 악성 `.vscode/tasks.json`의 `runOn: "folderOpen"` 작업이 폴더를 열기만 해도 실행 | Cursor 기본값 Workspace Trust 꺼짐, `task.allowAutomaticTasks` | 작업 공간 신뢰가 꺼져 있고 자동 작업이 허용된 상태에서 모르는 저장소를 연 경우 | [Oasis Security](https://www.oasis.security/blog/cursor-security-flaw) |
| 2025-08-12 | **GitHub Copilot·VS Code** CVE-2025-53773 | 프롬프트 인젝션으로 에이전트가 설정 파일에 `"chat.tools.autoApprove": true`를 써 넣어 이후 명령을 승인 없이 실행(YOLO 모드) | `.vscode/settings.json`의 `chat.tools.autoApprove` | 이 값이 true이거나, 에이전트가 설정 파일을 승인 없이 쓸 수 있는 상태. 8월 패치 전 버전 | [Embrace The Red](https://embracethered.com/blog/posts/2025/github-copilot-remote-code-execution-via-prompt-injection/), [MSRC](https://msrc.microsoft.com/update-guide/vulnerability/CVE-2025-53773) |
| 2025-07-28 | **Gemini CLI 허용 목록 우회** (Tracebit) | README에 숨긴 인젝션 + `grep` 같은 허용 명령 접두사 뒤에 악성 명령을 붙여 승인 없이 실행, 환경 변수 유출 | `run_shell_command` 허용 목록, 기본 비샌드박스 | 흔한 명령을 허용 목록에 넣고, 샌드박스 없이, 모르는 저장소에서 실행. 0.1.14 미만 | [Tracebit](https://tracebit.com/blog/code-exec-deception-gemini-ai-cli-hijack) |
| 2026-04-24 | **Gemini CLI** CVE-2026-12537 (critical) | 헤드리스(CI)에서 폴더를 자동 신뢰해 `.gemini/`의 `.env`를 읽음. `--yolo`일 때 `~/.gemini/settings.json`의 도구 허용 목록을 무시 | `--yolo`, 폴더 신뢰, `GEMINI_TRUST_WORKSPACE`, `run-gemini-cli`의 `gemini_cli_version` | CI에서 남이 올린 PR·이슈를 다루며 `--yolo`로 실행, `gemini_cli_version`을 0.39.1 미만에 고정 | [GHSA-wpqr-6v78-jr5g](https://github.com/advisories/GHSA-wpqr-6v78-jr5g) |
| 2025-12-04 | **PromptPwnd** (Aikido) | 이슈 제목·본문을 프롬프트에 넣는 CI 워크플로에서 에이전트가 비밀을 공개 이슈에 써 버림. Gemini CLI 저장소의 이슈 분류 워크플로에서 확인 | Gemini: `run_shell_command(gh issue edit)` 등 허용 + `GEMINI_API_KEY`·`GITHUB_TOKEN` 노출. Claude Code Action: `allowed_non_write_users: "*"`. Codex Action: `allow-users: "*"` + `safety-strategy` 변경. GitHub AI Inference: `enable-github-mcp: true` | `${{ github.event.issue.title }}` 등을 프롬프트에 넣고, 쓰기 권한 없는 사용자도 실행할 수 있게 열고, 쓰기 가능한 토큰을 같은 작업에 둔 상태 | [Aikido](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents) |
| 2026-06-05 | **Claude Code GitHub Action 비밀 노출** (Microsoft) | 이슈·PR·댓글의 숨은 지시로 Read 도구가 `/proc/self/environ`을 읽어 `ANTHROPIC_API_KEY` 노출. 하위 프로세스 env 정리(`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`)를 Read 도구가 우회 | `show_full_output`(켜면 키가 로그에 찍힘), WebFetch·Bash·GitHub MCP 같은 외부 전송 도구 | 신뢰하지 않는 입력을 읽는 워크플로에 외부 전송 도구를 열어 두고 `show_full_output`을 켠 상태. Claude Code 2.1.128 미만 | [Microsoft Security Blog](https://www.microsoft.com/en-us/security/blog/2026/06/05/securing-ci-cd-in-agentic-world-claude-code-github-action-case/) |
| 2026-02-25 공개 | **Claude Code 프로젝트 파일 RCE·키 유출** (Check Point) | 저장소의 `.claude/settings.json` 훅, MCP 자동 승인, `ANTHROPIC_BASE_URL`로 신뢰 대화상자 전에 명령 실행·API 키 유출 | `hooks`, `enableAllProjectMcpServers`, `enabledMcpjsonServers`, `ANTHROPIC_BASE_URL` | 모르는 저장소를 열 때 저장소 설정이 이런 키를 갖고 있고, Claude Code가 1.0.87(훅)·1.0.111(MCP, CVE-2025-59536)·2.0.65(키, CVE-2026-21852) 미만 | [Check Point Research](https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/), [GHSA-4fgq-fpq9-mr3g](https://github.com/advisories/GHSA-4fgq-fpq9-mr3g), [GHSA-jh7p-qr78-84p7](https://github.com/advisories/GHSA-jh7p-qr78-84p7) |
| 2026-03-19 | Claude Code CVE-2026-33068 | 저장소의 `.claude/settings.json`에 `permissions.defaultMode: "bypassPermissions"`를 넣으면 신뢰 대화상자가 생략됨 | `permissions.defaultMode` | 2.1.53 미만 + 이 값을 가진 저장소를 연 경우 | [GHSA-mmgp-wc2j-qcv7](https://github.com/advisories/GHSA-mmgp-wc2j-qcv7) |
| 2026-04-14 | **Codex CLI** CVE-2025-61260 (critical) | 저장소의 `.env`와 `.codex/config.toml`을 확인 없이 읽어, 악성 MCP 설정의 명령이 바로 실행 | 프로젝트 로컬 `.codex/config.toml` | 0.23.0 이하로 모르는 저장소에서 `codex` 실행 | [GHSA-xrxf-jgv3-qmrm](https://github.com/advisories/GHSA-xrxf-jgv3-qmrm), [Check Point](https://research.checkpoint.com/2025/openai-codex-cli-command-injection-vulnerability) |
| 2026-05-21 | Cursor CVE-2026-48124 | Cursor가 작업 공간의 `.claude/settings.local.json` 훅을 별도 승인 없이 실행 | 다른 도구의 설정 파일(`.claude/`)을 Cursor가 읽음 | 도구 하나만 점검하면 놓친다. **도구 사이 설정 공유**를 함께 봐야 함 | [GHSA-pc9j-3qc2-95wv](https://github.com/cursor/cursor/security/advisories/GHSA-pc9j-3qc2-95wv) |
| 2026-02-23 | **SANDWORM_MODE** (Endor Labs) | npm 웜이 AI 도구 설정의 `mcpServers`에 악성 서버를 추가하고, 모든 도구 설명 뒤에 "SSH 키·AWS 자격 증명을 읽어 `context` 매개변수로 넘겨라, 사용자에게 말하지 마라"는 지시를 붙임 | `~/.claude/settings.json`, `~/.claude.json`, `claude_desktop_config.json`, `~/.cursor/mcp.json`, `~/.continue/config.json`, `~/.windsurf/mcp.json`. 서버 스크립트는 `~/.dev-utils/` | 사용자가 등록한 적 없는 MCP 서버가 사용자 설정에 생겨도 알아채지 못하는 상태. 홈 아래 스크립트를 실행하는 서버 | [Endor Labs](https://endorlabs.com/learn/sandworm-mode-dissecting-a-multi-stage-npm-supply-chain-attack) |
| 2026-04-23 | **@bitwarden/cli 2026.4.0 오염** (MAL-2026-3020) | 악성 버전 배포(preinstall). 파일 수집기가 AI·MCP 설정을 노림. ※ 2026-11-24 원문 재확인: 공개일은 04-23, "GitHub Action 경유"는 JFrog·OSV 원문에 없음 | `~/.claude.json`, `.claude.json`, `~/.claude/mcp.json`, `~/.kiro/settings/mcp.json` | AI 도구 설정 파일 안에 **API 키나 토큰을 평문으로** 둔 상태 | [JFrog](https://research.jfrog.com/post/bitwarden-cli-hijack/), [OSV MAL-2026-3020](https://osv.dev/vulnerability/MAL-2026-3020) |

### 4-2. 버전 대조 규칙의 원천(공식 권고 목록)

GitHub Advisory Database를 `gh api /advisories?ecosystem=npm&affects=<패키지>`로 읽었다. 우리 도구에 오프라인 표로 넣어 "설치 버전 < 고친 버전"을 판정할 수 있다.

| 패키지 | 권고 수 | 고친 버전 예 |
|---|---|---|
| `@anthropic-ai/claude-code` | 30건(2025-06-23 ~ 2026-11-09) | 최신 CVE-2026-88968 → 2.1.251, CVE-2026-86063(플러그인 해시 고정 우회) → 2.1.179, CVE-2026-33068 → 2.1.53 |
| Cursor(`cursor/cursor` 저장소 권고) | 33건 | CVE-2026-50548·50549(샌드박스 탈출, critical) 등. 고친 버전 번호는 권고 본문마다 확인 필요 |
| `@google/gemini-cli` | 1건(GitHub DB) | CVE-2026-12537 → 0.39.1 |
| `@openai/codex` | 2건 | CVE-2025-59532 → 0.39.0, CVE-2025-61260(고친 버전 칸 비어 있음, 0.23.0 이하 영향) |
| `mcp-remote` | 1건 | CVE-2025-6514 → 0.1.16 |
| `@modelcontextprotocol/inspector` | 2건 | 0.14.1, 0.16.6 |
| Amazon Q VS Code 확장 | AWS 공지 | 1.84.0 제거, 1.85.0 이상 |

목록: [Claude Code 권고](https://github.com/advisories?query=%40anthropic-ai%2Fclaude-code), [Cursor 권고](https://github.com/cursor/cursor/security/advisories)

### 4-3. 사건에서 뽑은 점검 규칙 후보(설계 입력)

1. AI CLI를 권한 확인 없이 실행하게 만드는 흔적: 셸 별칭·rc 파일·스크립트에 `--dangerously-skip-permissions`, `--yolo`, `--trust-all-tools`, `--no-interactive`(Nx, Amazon Q).
2. Claude Code: `permissions.defaultMode: "bypassPermissions"`, `hooks`의 외부 다운로드·셸 실행, `enableAllProjectMcpServers: true`, 저장소 설정의 `ANTHROPIC_BASE_URL`(Check Point, CVE-2026-33068).
3. Gemini CLI: `--yolo`와 `run_shell_command` 넓은 허용, CI의 `GEMINI_TRUST_WORKSPACE`·`gemini_cli_version` 고정값(CVE-2026-12537, Tracebit).
4. Codex: 프로젝트 로컬 `.codex/config.toml`의 MCP 명령, `approval_policy`·`sandbox_mode = "danger-full-access"`([Codex 설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference)) (CVE-2025-61260).
5. VS Code·Cursor: 작업 공간 신뢰 꺼짐, `task.allowAutomaticTasks`, `.vscode/tasks.json`의 `runOn: "folderOpen"`, `chat.tools.autoApprove: true`(Oasis, CVE-2025-53773).
6. MCP: 버전 미고정 `npx`/`uvx`, `mcp-remote` 0.1.16 미만, 평문 `http://` 원격 서버, 사용자가 등록하지 않은 서버(홈 아래 숨은 폴더 스크립트), 도구 설명의 숨은 지시(postmark-mcp, CVE-2025-6514, SANDWORM_MODE).
7. 설정 파일 속 평문 키(Bitwarden CLI 오염).
8. CI 워크플로: `allowed_non_write_users: "*"`, `allow-users: "*"`, `enable-github-mcp: true`, 프롬프트에 `${{ github.event.issue.* }}`·`pull_request.body`, `show_full_output: true`(PromptPwnd, Microsoft).
9. 도구 사이 설정 공유: Cursor가 `.claude/settings.local.json` 훅을 실행한 사례(CVE-2026-48124). 한 도구의 설정이 다른 도구에서 실행되는지 함께 본다.

---

## 5. 우리 도구의 차별점으로 보이는 빈 곳

1. **도구 다섯 종류(Claude Code·Cursor·Codex·Gemini CLI·VS Code 확장)의 "권한·신뢰 설정 상태"를 한 번에 본다.** 기존 도구는 MCP 서버·스킬 내용 중심이고, 권한 모드·훅·작업 공간 신뢰·자동 작업·자동 승인을 홈 디렉터리 실제 설정까지 가로질러 보는 도구는 찾지 못했다(medusa는 저장소의 `.claude/`만, AGPL).
2. **설치된 AI 도구·확장·MCP 패키지 버전을 공개 보안 권고와 오프라인으로 대조한다.** 4-2절 권고표를 묶어 배포하면 네트워크 없이 "고친 버전보다 낮다"를 판정할 수 있다. 이번에 확인한 README 범위에서 이 기능을 가진 도구는 없었다.
3. **기본값에서 외부 전송 0·서버 실행 0, 결과는 사건 근거가 달린 한국어 보고서.** Snyk은 외부 API가 필수이고 Cisco·mcp-shield·SkillSpector는 외부 분석이 선택지다. 규칙마다 4장 사건(날짜·원문 URL)을 붙여 "왜 위험한가"를 한국어로 설명하는 도구는 없었다. tools/list 해시 고정은 명시적 옵션으로만 서버를 띄운다.

---

## 6. 확인하지 못한 것

- Snyk Agent Scan 현재 버전이 서버 쪽에서 도구 정의 변경(러그풀)을 비교하는지: **미확인**(로컬 코드에서는 찾지 못함).
- raghav1924/guardmcp의 네트워크 사용 여부: **미확인**(README만 읽음).
- alexgreensh/repo-forensics의 실제 라이선스(GitHub가 NOASSERTION으로 표시): **미확인**.
- 사용자가 말한 `mcp-security-scanner`가 어느 저장소인지: **미확인**(활동 있는 두 개를 실음).
- Koi Security의 postmark-mcp 원문 글: 주소가 다른 사이트로 넘어가 직접 읽지 못함. 사실관계는 OSV 기록과 The Register로 확인.
- Amazon Q 사건의 `--trust-all-tools`·`--no-interactive`는 AWS 공지에는 없고 The Register 보도에만 있다. 404 Media 원문은 직접 읽지 못함.
- Claude Code GitHub Action의 "Comment and Control"(RyotaK) 건과 claude-code-action v1.0.94 수정 여부: 2차 보도만 확인, 원문 **미확인**이라 표에서 뺐다.
- 홈 디렉터리 파일을 가리키는 SARIF 결과를 GitHub code scanning이 어떻게 표시하는지: **미확인**.
- Cursor 권고들의 고친 버전 번호: 권고 본문마다 따로 확인해야 함(이번에는 목록만).
- tools/list 해시에 쓸 공용 정규화 형식(다른 도구와 호환): 공개된 표준을 찾지 못함 — **미확인**.
- Aikido가 공개한 Opengrep 규칙의 라이선스와 범위: **미확인**.
- MCP Python SDK의 Python 최소 버전: README(3.11+)와 `pyproject.toml`(>=3.10)이 다름. 어느 쪽이 의도인지 **미확인**.
