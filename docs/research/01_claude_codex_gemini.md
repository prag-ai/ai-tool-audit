# 01. AI 코딩 도구 설정 조사 — Claude Code · Claude Desktop · Codex CLI · Gemini CLI

`ai-tool-audit`(개발자 PC의 AI 도구 설정을 읽기 전용으로 점검하는 CLI)의 점검 규칙 근거 자료다.

- 조사 기준일: 2026-11-24. 공식 문서·공식 저장소·공식 지원 문서에서 확인한 것만 적었다.
- 문서에서 찾지 못한 것은 **미확인**으로 표시했다. 문서에 없는 경로·키를 추측으로 채우지 않았다.
- 표의 "위험한 이유"는 문서에 적힌 동작에서 끌어낸 판단이다. 문서가 직접 경고한 경우에는 "(문서 경고)"를 붙였다.
- 표기: `~`는 사용자 홈 디렉터리(Windows는 `%USERPROFILE%`).

---

## 1. Claude Code (CLI)

문서 기준 버전은 v2.1.3xx대다(문서 안에 v2.1.319·v2.1.324 등 버전 조건이 나온다). 키마다 "몇 버전부터"가 붙어 있으니, 규칙을 만들 때 점검 대상의 `claude --version`과 함께 판정해야 한다.

### 1.1 설정 파일 위치와 형식

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 사용자 설정 | `~/.claude/settings.json` (Windows `%USERPROFILE%\.claude\settings.json`). JSON(주석·끝 쉼표 불허) | 모든 프로젝트에 적용된다. 넓은 허용 규칙이 여기 있으면 전 프로젝트가 영향을 받는다 | https://code.claude.com/docs/en/settings |
| 프로젝트 공유 설정 | `<프로젝트>/.claude/settings.json` (git에 커밋해 팀이 공유) | 저장소를 받은 사람 모두에게 적용된다. 남이 만든 저장소의 권한·훅·env가 들어온다 | https://code.claude.com/docs/en/settings |
| 프로젝트 로컬 설정 | `<프로젝트>/.claude/settings.local.json`. "Yes, and don't ask again"을 누르면 Claude Code가 여기에 `allow` 규칙을 쓴다. git 저장소에서는 저장소 루트에 둔다(v2.1.211부터) | 사용자가 무심코 누른 상시 승인이 쌓이는 곳. git에 추적되지 않는 동안에는 작업 폴더 신뢰(workspace trust) 없이 allow 규칙이 적용된다 | https://code.claude.com/docs/en/settings |
| 내부 상태 파일 | `~/.claude.json`. 계정 정보, MCP 서버 설정(local·user 범위), 프로젝트별 신뢰 결정, 전역 설정 키가 들어 있다 | MCP 서버 정의와 그 `env`(API 키 등)가 여기 들어갈 수 있다 | https://code.claude.com/docs/en/settings , https://code.claude.com/docs/en/mcp |
| 설정 디렉터리 변경 | 환경 변수 `CLAUDE_CONFIG_DIR` | 점검기가 기본 경로만 보면 놓친다. 이 변수가 있으면 그 경로도 봐야 한다 | https://code.claude.com/docs/en/settings , https://code.claude.com/docs/en/authentication |
| 우선순위 | 관리(managed) > 명령줄 `--settings` > 프로젝트 로컬 > 프로젝트 공유 > 사용자. `permissions.allow` 같은 목록은 덮어쓰지 않고 **합쳐진다** | 한 파일만 보고 판정하면 안 된다. 허용 목록은 모든 파일을 합쳐 봐야 한다 | https://code.claude.com/docs/en/settings |

### 1.2 위험한 권한 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 기본 권한 모드 | `permissions.defaultMode` = `"default"`(=`"manual"`) / `"acceptEdits"` / `"plan"` / `"auto"` / `"dontAsk"` / `"bypassPermissions"`. `auto`·`bypassPermissions`는 프로젝트·로컬 파일에서는 효력이 없고 사용자·관리 설정에서만 먹는다(v2.1.257 전에는 아무 파일에서나 먹었음) | `bypassPermissions`는 "Claude Code runs everything without asking". `.git`, `.claude` 같은 보호 경로 쓰기도 묻지 않는다. 문서는 컨테이너·VM 같은 격리 환경에서만 쓰라고 한다(문서 경고) | https://code.claude.com/docs/en/settings-reference , https://code.claude.com/docs/en/permissions |
| `acceptEdits` | 위 키의 값 | 파일 편집과 `mkdir`·`touch`·`mv`·`cp` 같은 명령을 묻지 않고 실행 | https://code.claude.com/docs/en/permissions |
| `auto` 모드 | 위 키의 값 | 사람 대신 분류기가 명령을 판단한다. 사람 승인이 빠진다 | https://code.claude.com/docs/en/permissions |
| CLI 플래그 | `--dangerously-skip-permissions`(= `--permission-mode bypassPermissions`), `--permission-mode <모드>` | 셸 별칭(alias)·래퍼 스크립트에 박혀 있으면 매번 우회 모드로 실행된다 | https://code.claude.com/docs/en/settings-reference |
| 우회 확인창 생략 | `skipDangerousModePermissionPrompt: true`. 사용자가 확인창을 한 번 수락하면 Claude Code가 사용자 설정에 이 값을 써 넣는다 | 이 값이 있다는 것은 사용자가 우회 모드를 실제로 쓴 적이 있다는 흔적이다 | https://code.claude.com/docs/en/settings-reference |
| 넓은 허용 규칙 | `permissions.allow`에 `"Bash"` 또는 `"Bash(*)"`(둘은 같음, 모든 Bash 명령), `"WebFetch"`·`"WebFetch(domain:*)"`(모든 URL), `"Read"`(모든 읽기), `"mcp__<서버>__*"`·`"mcp__<서버>"`(그 서버의 모든 도구) | 해당 도구 전체가 확인 없이 실행된다. `WebFetch(domain:*)`는 샌드박스 명령의 네트워크까지 모든 호스트로 연다 | https://code.claude.com/docs/en/permissions |
| 추가 디렉터리 | `permissions.additionalDirectories` | 작업 폴더 밖까지 읽기·편집 범위를 넓힌다 | https://code.claude.com/docs/en/settings |
| 샌드박스 | `sandbox.enabled`(기본 꺼짐) / `sandbox.allowUnsandboxedCommands`(false면 샌드박스 밖 재시도 금지) / `sandbox.excludedCommands`(여기 맞는 명령은 파일·네트워크 제한 없이 실행) / `sandbox.failIfUnavailable` / `sandbox.autoAllowBashIfSandboxed`(true면 샌드박스 안 Bash를 묻지 않음, 기본 `false`, v2.1.324 전에는 기본 `true`) / `sandbox.network.allowedDomains` | 샌드박스가 꺼져 있으면 모델이 만든 명령이 OS 수준 격리 없이 돈다. `excludedCommands`가 넓으면 사실상 샌드박스 밖이다. Windows 네이티브는 샌드박스 미지원(WSL2만 지원) | https://code.claude.com/docs/en/sandboxing , https://code.claude.com/docs/en/settings-reference |
| 샌드박스 해제 재시도 | 도구 매개변수 `dangerouslyDisableSandbox`. `bypassPermissions`에서는 묻지 않고 실행 | 샌드박스에서 실패한 명령을 샌드박스 밖에서 다시 돌린다 | https://code.claude.com/docs/en/sandboxing |
| 방어 키(있으면 좋음) | `permissions.disableBypassPermissionsMode: "disable"`, `disableAutoMode`, `permissions.denyInsteadOfPrompting: true`, `permissions.blockWritesOutsideWorkingDirectories: true` | 없으면 감점이 아니라 "권장 미적용"으로 볼 항목 | https://code.claude.com/docs/en/settings-reference , https://code.claude.com/docs/en/permissions |

### 1.3 MCP 서버 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 범위와 위치 | local 범위: `~/.claude.json`의 해당 프로젝트 경로 아래 / project 범위: `<프로젝트>/.mcp.json` / user 범위: `~/.claude.json` | `.mcp.json`은 저장소에 커밋된다. 남의 저장소가 실행 명령을 들여올 수 있다 | https://code.claude.com/docs/en/mcp |
| 구조 | `{"mcpServers": {"<이름>": {"type": "stdio"\|"http"\|"sse"\|"ws", "command", "args", "env", "url", "headers"}}}`. `type`이 없으면 stdio로 읽는다 | `command`+`args`는 로컬에서 바로 실행되는 프로그램이다. `npx -y <패키지>`면 설치·실행이 한 번에 일어난다 | https://code.claude.com/docs/en/mcp |
| 환경 변수 확장 | `${VAR}`, `${VAR:-기본값}`을 `command`·`args`·`env`·`url`·`headers`에서 쓸 수 있다 | `${VAR}`로 쓰면 안전하고, 값이 직접 적혀 있으면 비밀값이 평문으로 남은 것 | https://code.claude.com/docs/en/mcp |
| 프로젝트 서버 자동 승인 | `enableAllProjectMcpServers: true`(`.mcp.json`의 모든 서버를 묻지 않고 승인), `enabledMcpjsonServers: ["이름", …]`. 승인 대화상자에서 고르면 Claude Code가 `.claude/settings.local.json`에 써 넣는다 | 저장소가 `.mcp.json`에 서버를 추가해도 묻지 않고 연결된다 | https://code.claude.com/docs/en/settings-reference |
| 비대화 실행 | `claude -p`, Agent SDK, 대부분의 클라우드 세션은 승인창을 띄울 수 없어 프로젝트 서버를 **묻지 않고** 불러온다 | CI·스크립트에서 쓰면 `.mcp.json`이 그대로 실행된다 | https://code.claude.com/docs/en/mcp |
| 차단·허용 목록 | `disabledMcpjsonServers`, `allowedMcpServers`(항목마다 `serverName` / `serverCommand` / `serverUrl` 중 하나), `deniedMcpServers`, 관리 전용 `allowManagedMcpServersOnly` | 허용 목록이 없으면 모든 서버가 허용된다 | https://code.claude.com/docs/en/settings-reference , https://code.claude.com/docs/en/managed-settings |
| MCP 도구 자동 승인 | 별도 키 없음. `permissions.allow`의 `mcp__<서버>__<도구>` 또는 `mcp__<서버>__*` 규칙으로 승인 | 서버 전체 와일드카드는 그 서버의 쓰기 도구까지 묻지 않게 만든다 | https://code.claude.com/docs/en/permissions |

### 1.4 훅과 자동 실행

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 훅 위치 | `~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, 관리 설정, 플러그인 `hooks/hooks.json`, 스킬·서브에이전트 프런트매터(frontmatter). 여러 파일의 훅은 합쳐진다 | 커밋된 프로젝트 설정의 훅은 저장소를 받은 사람 PC에서 실행된다 | https://code.claude.com/docs/en/hooks |
| 구조 | `"hooks": {"<이벤트>": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "...", "timeout": 600}]}]}`. `type`은 `command`·`http`·`mcp_tool`·`prompt`·`agent` | `command`는 임의 셸 명령, `http`는 이벤트 JSON을 외부 URL로 POST한다(데이터 유출 경로) | https://code.claude.com/docs/en/hooks |
| 이벤트 | `SessionStart`, `Setup`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `Stop`, `SessionEnd`, `ConfigChange`, `FileChanged` 등 30여 개 | `SessionStart`·`UserPromptSubmit`은 매 세션·매 입력마다 돈다 | https://code.claude.com/docs/en/hooks |
| 신뢰 | 프로젝트 스킬의 프런트매터 훅은 설정 파일 훅과 같은 신뢰 규칙을 따라 "신뢰하지 않은 폴더에서도 `-p`로 실행될 수 있다" | 비대화 실행에서 저장소 훅이 그대로 돈다(문서 경고) | https://code.claude.com/docs/en/hooks |
| 훅 끄기·제한 | `disableAllHooks: true`, 관리 전용 `allowManagedHooksOnly: true`, `allowedHttpHookUrls`, `httpHookAllowedEnvVars` | `http` 훅이 있는데 URL 제한이 없으면 임의 주소로 보낼 수 있다 | https://code.claude.com/docs/en/hooks , https://code.claude.com/docs/en/managed-settings |
| 훅 외 명령 실행 키 | `apiKeyHelper`(시스템 셸로 실행), `awsAuthRefresh`, `awsCredentialExport`, `otelHeadersHelper`, `statusLine`, `fileSuggestion`. 프로젝트·로컬 설정의 `apiKeyHelper`는 작업 폴더 신뢰 뒤에 실행된다 | 이름은 "훅"이 아니지만 설정 파일에 적힌 셸 명령이 자동으로 돈다 | https://code.claude.com/docs/en/settings-reference , https://code.claude.com/docs/en/hooks |

### 1.5 비밀값이 남기 쉬운 곳

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 로그인 자격 증명 | macOS: 암호화된 키체인. 키체인 쓰기가 실패하면(SSH 세션 등) `~/.claude/.credentials.json`(권한 `0600`)으로 대체. Linux: `~/.claude/.credentials.json`(`0600`). Windows: `%USERPROFILE%\.claude\.credentials.json`(사용자 프로필 ACL 상속) | 파일 권한이 0600보다 넓으면 같은 PC의 다른 계정이 읽는다. macOS에서 이 파일이 있으면 키체인 대체가 일어났다는 뜻 | https://code.claude.com/docs/en/authentication |
| 환경 변수 | `ANTHROPIC_API_KEY`(X-Api-Key), `ANTHROPIC_AUTH_TOKEN`(Bearer), `CLAUDE_CODE_OAUTH_TOKEN`(`claude setup-token`이 만든 1년짜리 토큰), 클라우드 제공자용 `CLAUDE_CODE_USE_BEDROCK` 등 | 셸 시작 파일(`.zshrc` 등)에 평문으로 적히기 쉽다 | https://code.claude.com/docs/en/authentication |
| 설정의 `env` 블록 | `"env": {"ANTHROPIC_API_KEY": "…"}`처럼 설정 파일에 넣을 수 있다 | 공유 프로젝트 설정에 넣으면 저장소에 키가 커밋된다 | https://code.claude.com/docs/en/settings-reference |
| MCP 서버 `env`·`headers` | `.mcp.json`, `~/.claude.json`의 `env`·`headers` 값 | 평문 토큰이 들어가기 쉽다. `${VAR}` 확장을 쓰지 않은 경우 | https://code.claude.com/docs/en/mcp |
| MCP OAuth | 토큰은 엔드포인트별로 저장. client secret은 "macOS 키체인 또는 credentials 파일" | Linux·Windows에서는 파일에 남는다 | https://code.claude.com/docs/en/mcp |
| Anthropic 프로필 | `~/.config/anthropic`(macOS·Linux), `%APPDATA%\Anthropic`(Windows) | `ant auth login`이 쓴 자격 증명이 여기 남는다 | https://code.claude.com/docs/en/authentication |

### 1.6 기업 관리 기능

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 관리 설정 파일 | macOS `/Library/Application Support/ClaudeCode/managed-settings.json`, Linux·WSL `/etc/claude-code/managed-settings.json`, Windows `C:\Program Files\ClaudeCode\managed-settings.json`. 같은 폴더에 `managed-settings.d/*.json`, `managed-mcp.json`. 옛 경로 `C:\ProgramData\ClaudeCode\managed-settings.json`은 더는 읽지 않는다 | 옛 경로에만 정책이 있으면 정책이 걸려 있지 않은 것 | https://code.claude.com/docs/en/managed-settings |
| MDM | macOS 구성 프로파일 도메인 `com.anthropic.claudecode`. Windows `HKLM\SOFTWARE\Policies\ClaudeCode`의 `Settings` 값(REG_SZ/REG_EXPAND_SZ, JSON 문자열). 사용자가 쓸 수 있는 `HKCU\SOFTWARE\Policies\ClaudeCode`는 관리자 문서가 없을 때만 쓰인다 | HKCU는 사용자가 고칠 수 있어 정책으로 볼 수 없다. WSL에서는 `/etc/claude-code`도 사용자 쓰기가 가능하다고 문서가 적는다 | https://code.claude.com/docs/en/managed-settings |
| 서버 관리 설정 | claude.ai 관리 콘솔에서 내려받는 설정. `/status`의 `Setting sources` 줄로 확인 | 로컬 파일만 봐서는 보이지 않는다 | https://code.claude.com/docs/en/settings |
| 관리 전용 잠금 키 | `allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `allowManagedMcpServersOnly`, `disableCommandPluginSources`, `managedMcpServers`, `forceLoginMethod`, `forceLoginOrgUUID`, `allowedProviders`, `requiredMinimumVersion` | 기업 PC에서 이 키가 없으면 사용자 설정이 정책을 넘어선다 | https://code.claude.com/docs/en/managed-settings , https://code.claude.com/docs/en/authentication |

### 1.7 설치 여부 판별

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 네이티브 설치 | 실행 파일 `~/.local/bin/claude`(→ `~/.local/share/claude/versions/<버전>` 심볼릭 링크). Windows `%USERPROFILE%\.local\bin\claude.exe` | 오래된 버전이 `versions/`에 남아 있을 수 있다 | https://code.claude.com/docs/en/setup |
| 기타 설치 | Homebrew `brew install --cask claude-code`(또는 `claude-code@latest`), WinGet `Anthropic.ClaudeCode`, npm `@anthropic-ai/claude-code`, apt·dnf·apk `claude-code` | Homebrew·WinGet·패키지 관리자 설치는 자동 업데이트되지 않는다 | https://code.claude.com/docs/en/setup |
| 버전 확인 | `claude --version`(예: `2.1.211 (Claude Code)`), 진단 `claude doctor`(읽기 전용) | — | https://code.claude.com/docs/en/setup |

---

## 2. Claude Desktop

Claude Desktop 안의 Code 기능과 Cowork는 Claude Code를 돌리므로 1장의 `~/.claude/` 설정도 함께 읽는다(문서: "the desktop app … all read the same settings files").

### 2.1 설정 파일 위치와 형식

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 앱 설정(MCP) | macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows `%APPDATA%\Claude\claude_desktop_config.json`, Linux `~/.config/Claude/claude_desktop_config.json`. JSON | 로컬 MCP 서버 정의와 그 `env`가 들어 있다 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| 로그 | macOS `~/Library/Logs/Claude`, Windows `%APPDATA%\Claude\logs`, Linux `~/.config/Claude/logs`. `mcp.log`, `mcp-server-<이름>.log`(서버 stderr) | 서버가 stderr에 토큰을 찍으면 로그에 남는다 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| Claude Code 공유 설정 | `~/.claude/settings.json` 등 1장 경로 | Desktop의 Code 세션 권한도 여기서 결정된다 | https://code.claude.com/docs/en/settings |
| Windows MSIX 가상화 경로 | 미확인(제3자 글에만 `%LOCALAPPDATA%\Packages\Claude_<id>\…` 언급, 공식 문서에서 확인 못 함) | — | — |

### 2.2 위험한 권한 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| MCP 도구 승인 | 공식 문서는 "도구 실행 전 승인을 묻는다"고만 적는다. `claude_desktop_config.json`에 자동 승인 키가 있는지는 **미확인** | — | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| 파일시스템 서버 범위 | `args`에 넘긴 디렉터리가 접근 범위. "서버는 사용자 계정 권한으로 돈다"(문서 경고) | 홈 디렉터리 전체나 `/`를 넘기면 모든 파일이 대상 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| Code 세션 권한 모드 | 1.2절 키를 그대로 따른다 | — | https://code.claude.com/docs/en/settings |

### 2.3 MCP 서버 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 구조 | `{"mcpServers": {"<이름>": {"command": "npx", "args": [...], "env": {...}}}}` | 앱 실행 때마다 자동으로 서버 프로세스를 띄운다 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| 데스크톱 확장(.mcpb) | 원클릭 설치 패키지. manifest에서 `"sensitive": true`인 값은 OS 보안 저장소(macOS 키체인, Windows 자격 증명 관리자, Linux 배포판 키체인)로 암호화. 공식 디렉터리 확장은 기본으로 자동 업데이트 | 확장 설치 위치는 문서에 없음(**미확인**). 허용 목록은 "설치 후 로컬 MCP 파일 변조는 막지 못한다"(문서 언급, 검색 요약 기준) | https://support.claude.com/en/articles/10949351 , https://support.claude.com/en/articles/12592343-enabling-and-using-the-desktop-extension-allowlist |

### 2.4 훅·자동 실행

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 앱 자체 훅 | 미확인(Desktop 앱 고유의 훅 기능 문서 없음). Code 세션은 1.4절 Claude Code 훅을 따른다 | — | https://code.claude.com/docs/en/hooks |
| MCP 서버 자동 기동 | `claude_desktop_config.json`의 stdio 서버는 앱 시작 때 실행 | 사용자가 Claude만 켜도 등록된 명령이 돈다 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |

### 2.5 비밀값이 남기 쉬운 곳

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| MCP `env` | `claude_desktop_config.json`의 `mcpServers.<이름>.env` | 평문 JSON 파일에 토큰이 남는다 | https://modelcontextprotocol.io/docs/develop/connect-local-servers |
| 확장의 민감값 | OS 보안 저장소 | 파일 점검으로는 안 보인다(정상) | https://support.claude.com/en/articles/10949351 |
| 인증 | Desktop은 `apiKeyHelper`·`ANTHROPIC_API_KEY`를 읽지 않고 OAuth를 쓴다(제3자 추론 구성 제외). 토큰 저장 위치는 **미확인** | — | https://code.claude.com/docs/en/authentication |
| 제3자 추론(3P) 구성 | 로컬 구성 `~/Library/Application Support/Claude-3p/configLibrary/`(macOS), `%LOCALAPPDATA%\Claude-3p\configLibrary\`(Windows). 저장된 API 키를 다른 기기로 복사하지 말라는 언급 | API 키가 이 폴더 계열에 저장될 수 있다(형식 **미확인**) | https://claude.com/docs/third-party/claude-desktop/mdm |

### 2.6 기업 관리 기능

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| macOS 정책 | 환경설정 도메인 `com.anthropic.claudefordesktop`. 3P 문서 기준 파일: `/Library/Managed Preferences/com.anthropic.claudefordesktop.plist`(기기), `/Library/Managed Preferences/<user>/com.anthropic.claudefordesktop.plist`(사용자) | — | https://support.claude.com/en/articles/12622667-enterprise-configuration-for-claude-desktop , https://claude.com/docs/third-party/claude-desktop/mdm |
| Windows 정책 | `HKLM\SOFTWARE\Policies\Claude`(권장), `HKCU\SOFTWARE\Policies\Claude`. 불리언은 DWORD(1/0) | 하위 키에 넣은 값은 읽지 않는다(3P 문서) | https://support.claude.com/en/articles/12622667-enterprise-configuration-for-claude-desktop , https://claude.com/docs/third-party/claude-desktop/mdm |
| Linux 정책 | `/etc/claude-desktop/managed-settings.json`(3P 문서) | — | https://claude.com/docs/third-party/claude-desktop/mdm |
| 정책 키 | `isLocalDevMcpEnabled`(로컬 MCP 허용, 기본 true), `isDesktopExtensionEnabled`(기본 true), `isDesktopExtensionDirectoryEnabled`(기본 true), `isClaudeCodeForDesktopEnabled`(기본 true), `secureVmFeaturesEnabled`(Cowork, 기본 true), `computerUseEnabled`, `disableAutoUpdates`(기본 false), `forceLoginOrgUUID`, `allowedWorkspaceFolders` | 기본값이 모두 "허용"이다. 기업 PC에 정책이 없으면 로컬 MCP·확장·Code가 다 켜진 상태 | https://support.claude.com/en/articles/12622667-enterprise-configuration-for-claude-desktop |
| 로컬 MCP 차단의 빈틈 | 조직 설정에서 로컬 MCP를 꺼도 데스크톱 확장은 로컬 서버를 돌릴 수 있어 "Block all desktop extensions"도 골라야 한다(검색 요약 기준) | 한 키만 보고 "차단됨"으로 판정하면 틀린다 | https://support.claude.com/en/articles/12592343-enabling-and-using-the-desktop-extension-allowlist |

### 2.7 설치 여부 판별

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 앱 위치 | 미확인(`/Applications/Claude.app` 등 공식 문서 확인 못 함). 설정 폴더(2.1절) 존재로 간접 판별 가능 | — | — |
| 버전 확인 | 미확인(CLI 명령 없음. 메뉴 "Check for Updates…"만 문서에 있음) | — | https://modelcontextprotocol.io/docs/develop/connect-local-servers |

---

## 3. OpenAI Codex CLI

현재 공식 문서는 `developers.openai.com/codex/…`에서 `learn.chatgpt.com/docs/…`로 영구 이동(308)했다.

### 3.1 설정 파일 위치와 형식

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 사용자 설정 | `~/.codex/config.toml`(TOML). 루트는 `CODEX_HOME`(기본 `~/.codex`) | — | https://learn.chatgpt.com/docs/config-file/config-basic , https://learn.chatgpt.com/docs/config-file/environment-variables |
| 프로젝트 설정 | `<프로젝트>/.codex/config.toml`(루트→현재 폴더 순, 가까운 것이 이김). **신뢰한 프로젝트에서만** 읽는다 | 신뢰한 저장소의 설정이 사용자 설정을 덮는다 | https://learn.chatgpt.com/docs/config-file/config-basic |
| 프로필 | `~/.codex/<이름>.config.toml`, `--profile <이름>` | 위험 설정이 프로필 파일에 숨어 있을 수 있다 | https://learn.chatgpt.com/docs/config-file/config-basic |
| 시스템 설정 | `/etc/codex/config.toml`(Unix) | — | https://learn.chatgpt.com/docs/config-file/config-basic |
| 우선순위 | CLI 플래그·`--config`(`-c`) > 프로젝트 > 프로필 > 사용자 > 클라우드 관리 기본값 > 시스템 > 내장 기본값. 단 `requirements.toml`은 이 위에서 제약을 건다 | — | https://learn.chatgpt.com/docs/config-file/config-basic |
| 프로젝트 신뢰 | 사용자 설정의 `[projects."<경로>"] trust_level = "trusted" \| "untrusted"`. untrusted면 프로젝트 `.codex/`(설정·훅·규칙)를 건너뛴다 | `trusted`가 많을수록 남의 `.codex/` 설정이 적용될 여지가 커진다 | https://learn.chatgpt.com/docs/config-file/config-reference |

### 3.2 위험한 권한 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 승인 정책 | `approval_policy` = `"on-request"` / `"never"` / `{ granular = { sandbox_approval, rules, mcp_elicitations, request_permissions, skill_approval } }`. `"untrusted"`는 폐지(설정에 있으면 실행이 안 될 수 있음), `"on-failure"`는 폐기 예정(deprecated) | `never`는 승인창이 전혀 뜨지 않는다 | https://learn.chatgpt.com/docs/config-file/config-reference , https://learn.chatgpt.com/docs/agent-approvals-security |
| 샌드박스 모드 | `sandbox_mode` = `"read-only"` / `"workspace-write"` / `"danger-full-access"` | `danger-full-access`는 샌드박스 없음 | https://learn.chatgpt.com/docs/config-file/config-reference |
| 권한 프로필 | `default_permissions` = `":read-only"` / `":workspace"` / `":danger-full-access"` 또는 `[permissions.<이름>]` | `sandbox_mode` 대신 이 키로 전체 권한을 줄 수 있다. 둘 다 봐야 한다 | https://learn.chatgpt.com/docs/config-file/config-reference |
| 네트워크 | `[sandbox_workspace_write] network_access = true`, `writable_roots = [...]` | 기본은 네트워크 꺼짐. 켜면 프롬프트 인젝션된 명령이 외부로 데이터를 보낼 수 있다(문서에 "Elevated Risk" 표시) | https://learn.chatgpt.com/docs/agent-approvals-security |
| CLI 플래그 | `--dangerously-bypass-approvals-and-sandbox`(별칭 `--yolo`): "Run every command without approvals or sandboxing". `--sandbox danger-full-access`, `--ask-for-approval never`(`-a never`), `--approve-for-me`(별칭 `--not-so-yolo`, 자동 검토자) | 문서가 "외부에서 단단히 격리한 환경에서만"이라고 경고 | https://learn.chatgpt.com/docs/cli/reference , https://learn.chatgpt.com/docs/agent-approvals-security |
| 자동 검토 | `approvals_reviewer = "auto_review"` | 승인 요청을 사람이 아니라 자동 검토가 처리 | https://learn.chatgpt.com/docs/agent-approvals-security |
| 웹 검색 | `web_search` = `"cached"`(기본) / `"live"` / `"disabled"`. `--yolo`나 전체 권한이면 기본이 `live` | 실시간 웹 내용은 프롬프트 인젝션 통로 | https://learn.chatgpt.com/docs/config-file/config-basic |
| 경고 숨김 | `notice.hide_full_access_warning` | 전체 권한 경고를 끈 흔적 | https://learn.chatgpt.com/docs/config-file/config-reference |
| OS 샌드박스 | macOS Seatbelt(`sandbox-exec`), Linux `bwrap`+`seccomp`, Windows MXC(`elevated`·`unelevated`는 옛 대체). WSL1은 0.115부터 미지원 | — | https://learn.chatgpt.com/docs/agent-approvals-security |
| `--full-auto` | 현재 문서에서 찾지 못함(**미확인**. 폐지 여부도 확인 못 함) | — | — |

### 3.3 MCP 서버 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 위치·구조 | `config.toml`의 `[mcp_servers.<id>]`. stdio: `command`, `args`, `env`, `env_vars`, `cwd`. HTTP: `url`, `bearer_token_env_var`, `http_headers`(정적 헤더), `env_http_headers`, `http_headers_helper`(로컬 명령), `auth = "oauth"\|"chatgpt"`, `oauth.client_secret` | `http_headers`·`env`·`oauth.client_secret`에 값이 직접 적히면 평문 비밀값 | https://learn.chatgpt.com/docs/config-file/config-reference |
| 도구 승인 | `default_tools_approval_mode` = `auto` / `prompt` / `writes` / `approve`, 도구별 `tools.<tool>.approval_mode`. `writes`는 읽기 전용 표시가 없는 도구만 묻는다 | 값별 정확한 의미는 `writes` 외에는 문서에 풀이가 없다(**부분 미확인**). `approve`가 "자동 승인"인지 문서 문장으로 확인 못 함 | https://learn.chatgpt.com/docs/extend/mcp , https://learn.chatgpt.com/docs/config-file/config-reference |
| 도구 범위 | `enabled_tools`(허용), `disabled_tools`(거부), `enabled` | — | https://learn.chatgpt.com/docs/extend/mcp |
| 플러그인 MCP | `plugins.<plugin>.mcp_servers.<server>.*`(같은 키) | 플러그인 안의 서버도 봐야 한다 | https://learn.chatgpt.com/docs/config-file/config-reference |

### 3.4 훅·자동 실행

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 훅 위치 | 시스템 `/etc/codex/hooks.json`(macOS·Linux), `%ProgramData%\OpenAI\Codex\hooks.json`(Windows). 사용자 `$CODEX_HOME/hooks.json`. 신뢰한 프로젝트 `.codex/hooks.json`. 각 층의 `config.toml` `[hooks]`에도 적을 수 있다. 플러그인 `hooks/hooks.json` | — | https://learn.chatgpt.com/docs/hooks |
| 구조 | `{"hooks": {"PreToolUse": [{"matcher": …, "hooks": [{"type": "command", "command": "…"}]}]}}`. 이벤트: `SessionStart`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop` | 임의 명령 실행 | https://learn.chatgpt.com/docs/hooks |
| 훅 신뢰 | 관리 대상이 아닌 훅은 사용자가 `/hooks`에서 검토·신뢰해야 실행. 신뢰는 훅 정의의 해시에 묶임. `--dangerously-bypass-hook-trust`는 이 검사를 건너뜀 | 이 플래그가 별칭·스크립트에 있으면 검토 없이 훅이 돈다 | https://learn.chatgpt.com/docs/hooks , https://learn.chatgpt.com/docs/cli/reference |
| 알림 명령 | `notify = ["명령", …]`(Codex가 JSON을 넘겨 실행) | 훅 외에 자동 실행되는 명령 | https://learn.chatgpt.com/docs/config-file/config-reference |
| 셸 환경 전달 | `shell_environment_policy.inherit` = `all` / `core` / `none`, `.ignore_default_excludes`(기본 `true`: 이름에 KEY·SECRET·TOKEN이 든 변수를 **남긴다**. `false`로 해야 자동 제외), `.filters`, `.set` | 기본값대로면 셸의 API 키 변수가 모델이 돌리는 명령에 넘어간다 | https://learn.chatgpt.com/docs/config-file/config-reference |

### 3.5 비밀값이 남기 쉬운 곳

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 로그인 캐시 | `~/.codex/auth.json`(평문) 또는 OS 자격 증명 저장소. `cli_auth_credentials_store` = `file` / `keyring` / `auto` / `ephemeral`. 문서: "`auth.json`을 비밀번호처럼 다루라, 접근 토큰이 들어 있다" | 평문 토큰 파일. 권한·백업·동기화 폴더 노출 점검 대상 | https://learn.chatgpt.com/docs/auth |
| MCP OAuth | `mcp_oauth_credentials_store` = `auto` / `file` / `keyring` | `file`이면 평문 | https://learn.chatgpt.com/docs/config-file/config-reference |
| 환경 변수 | `OPENAI_API_KEY`(`codex login --with-api-key`에 파이프), `CODEX_API_KEY`(비대화 실행), `CODEX_ACCESS_TOKEN` | 셸 시작 파일에 평문 저장되기 쉽다 | https://learn.chatgpt.com/docs/auth , https://learn.chatgpt.com/docs/config-file/environment-variables |
| 제공자 토큰 | `model_providers.<id>.experimental_bearer_token`(문서: "discouraged; use `env_key`"), `env_key` | 설정 파일에 토큰 직접 기재 | https://learn.chatgpt.com/docs/config-file/config-reference |

### 3.6 기업 관리 기능

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 강제 요건 | `requirements.toml`: `/etc/codex/requirements.toml`(macOS·Linux), `%ProgramData%\OpenAI\Codex\requirements.toml`(Windows). 키 예: `allowed_approval_policies`, `allowed_sandbox_modes`, `allowed_web_search_modes`, `[mcp_servers.<이름>] identity = { command = … } / { url = … }`(비어 있으면 모든 MCP 비활성), `[features]` | — | https://learn.chatgpt.com/docs/enterprise/managed-configuration |
| 관리 기본값(옛 방식) | `managed_config.toml`: Unix `/etc/codex/managed_config.toml`, Windows `~/.codex/managed_config.toml` | Windows 경로는 사용자 홈이라 사용자가 고칠 수 있다(경로상 추론) | https://learn.chatgpt.com/docs/enterprise/managed-configuration |
| macOS MDM | 도메인 `com.openai.codex`, 키 `config_toml_base64`(기본값), `requirements_toml_base64`(요건) | — | https://learn.chatgpt.com/docs/enterprise/managed-configuration |
| 클라우드 정책 | Agent Security 요건(로그인한 워크스페이스에 내려옴) | 로컬 파일만으로는 안 보인다 | https://learn.chatgpt.com/docs/enterprise/managed-configuration |

### 3.7 설치 여부 판별

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 독립 설치 | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh`. 실행 파일 기본 `~/.local/bin/codex`(macOS·Linux), `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin`(Windows). `CODEX_INSTALL_DIR`로 변경. 패키지 캐시 `CODEX_HOME/packages/standalone` | — | https://learn.chatgpt.com/docs/config-file/environment-variables , https://github.com/openai/codex/blob/main/scripts/install/install.sh |
| 기타 | npm `@openai/codex`, Homebrew `brew install --cask codex` | — | https://github.com/openai/codex |
| 버전 확인 | `codex --version`은 공식 문서에서 **미확인** | — | — |

---

## 4. Google Gemini CLI

공식 문서는 GitHub 저장소 `google-gemini/gemini-cli`의 `docs/` 원문을 출처로 삼았다.

### 4.1 설정 파일 위치와 형식

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 시스템 기본값 | Linux `/etc/gemini-cli/system-defaults.json`, Windows `C:\ProgramData\gemini-cli\system-defaults.json`, macOS `/Library/Application Support/GeminiCli/system-defaults.json`. `GEMINI_CLI_SYSTEM_DEFAULTS_PATH`로 변경. 우선순위 가장 낮음 | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 사용자 | `~/.gemini/settings.json`(JSON) | — | 같은 문서 |
| 프로젝트 | `<프로젝트>/.gemini/settings.json` | 남의 저장소 설정. 폴더 신뢰가 꺼져 있으면 그대로 적용 | 같은 문서 |
| 시스템 덮어쓰기 | Linux `/etc/gemini-cli/settings.json`, Windows `C:\ProgramData\gemini-cli\settings.json`, macOS `/Library/Application Support/GeminiCli/settings.json`. `GEMINI_CLI_SYSTEM_SETTINGS_PATH`로 변경. 가장 높은 우선순위 | 환경 변수로 경로를 바꿀 수 있어 사용자가 우회 가능(문서가 래퍼 스크립트를 권함) | 같은 문서, https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/enterprise.md |
| `.env` 자동 로드 | 현재 폴더 `.env` → 상위로 올라가며 → `~/.env`. `.gemini/.env`도 읽음 | 프로젝트 `.env`가 CLI 환경에 섞여 들어온다 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 폴더 신뢰 | `security.folderTrust.enabled`(기본 true). 결정은 `~/.gemini/trustedFolders.json`. 신뢰하지 않은 폴더는 프로젝트 설정·`.env` 무시, MCP 연결 안 함 | 폴더 신뢰를 끄면 이 보호가 모두 사라진다 | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/trusted-folders.md |

### 4.2 위험한 권한 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 기본 승인 모드 | `general.defaultApprovalMode` = `"default"` / `"auto_edit"` / `"plan"`. YOLO는 설정 파일로는 켤 수 없고 명령줄로만 켠다 | `auto_edit`은 편집 도구 자동 승인 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| CLI 플래그 | `--yolo`, `--approval-mode yolo`(모든 도구 호출 자동 승인), `--approval-mode auto_edit`, `--allowed-tools "<도구>"` | 별칭·스크립트에 박히면 상시 자동 승인 | 같은 문서 |
| 허용 도구 | `tools.allowed`(확인창 생략 목록, 예 `"run_shell_command(git)"`), `tools.core`, `tools.exclude`, `tools.confirmationRequired` | `run_shell_command` 전체 허용은 모든 셸 명령 자동 실행 | 같은 문서 |
| 영구 승인 | `security.enablePermanentToolApproval`("모든 이후 세션 허용" 선택지), `security.autoAddToPolicyByDefault`. 영구 승인은 정책 파일(`~/.gemini/policies/*.toml`)에 규칙으로 남는다(정확한 파일명 **미확인**) | 한 번 누른 승인이 계속 남는다 | 같은 문서, https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/policy-engine.md |
| 정책 엔진 | 규칙 `decision = "allow" \| "deny" \| "ask_user"`. 사용자 `~/.gemini/policies/*.toml`. 관리자 Linux `/etc/gemini-cli/policies`, macOS `/Library/Application Support/GeminiCli/policies`, Windows `C:\ProgramData\gemini-cli\policies`, `adminPolicyPaths`. 워크스페이스 단계(`.gemini/policies`)는 현재 비활성 | 넓은 `allow` 규칙 점검 대상 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/policy-engine.md |
| 샌드박스 | `tools.sandbox`(불리언·프로필 경로·`docker`/`podman`/`lxc`/`windows-native`), `tools.sandboxNetworkAccess`(기본 false), `tools.sandboxAllowedPaths`, 환경 변수 `GEMINI_SANDBOX`, 플래그 `--sandbox`/`-s`. 기본 꺼짐. `--yolo`면 기본으로 켜진다고 문서에 적힘 | 샌드박스 없이 자동 승인이면 가장 위험 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 방어 키 | `security.disableYoloMode`, `security.disableAlwaysAllow`, `admin.secureModeEnabled`(YOLO·"항상 허용" 금지) | 기업 PC에 없으면 권장 미적용 | 같은 문서 |

### 4.3 MCP 서버 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 구조 | `settings.json`의 `mcpServers.<이름>`: `command`, `args`, `env`, `cwd`, `url`(SSE), `httpUrl`(스트리밍 HTTP), `headers`, `timeout`, `trust`, `includeTools`, `excludeTools` | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 서버 단위 자동 승인 | `trust: true` = "bypasses all tool call confirmations for this server"(기본 false) | 그 서버의 모든 도구가 묻지 않고 실행 | https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md |
| 허용·제외 | `mcp.allowed`, `mcp.excluded`, 관리용 `admin.mcp.enabled`, `admin.mcp.config`(허용 목록), `admin.mcp.requiredConfig` | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 이름 주의 | 서버 별칭에 밑줄(`_`)을 쓰면 정책 엔진이 서버 이름을 잘못 읽어 "보안 정책이 조용히 실패"할 수 있다(문서 경고) | 정책 우회 | 같은 문서 |
| 환경 변수 | `env`에 `$VAR`·`${VAR}`(Windows `%VAR%`) 확장. 명시한 변수는 자동 가림(redaction) 대상에서 빠짐 | 평문 값 점검 | https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md |

### 4.4 훅·자동 실행

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 위치 | 프로젝트 `.gemini/settings.json`, 사용자 `~/.gemini/settings.json`, 시스템 `/etc/gemini-cli/settings.json`, 확장(extension) | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/index.md |
| 구조 | `"hooks": {"BeforeTool": [{"matcher": "write_file\|replace", "hooks": [{"name", "type": "command", "command", "timeout"}]}]}`. 이벤트 `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `Notification`, `SessionStart`, `SessionEnd`, `PreCompress`, `BeforeModel`, `AfterModel`, `BeforeToolSelection` | "훅은 사용자 권한으로 임의 코드를 실행한다"(문서 경고) | 같은 문서, https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 신뢰 | 프로젝트 훅은 지문(fingerprint)을 찍어, 이름·명령이 바뀌면 새 훅으로 보고 실행 전 경고 | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/hooks/index.md |
| 끄기 | `hooksConfig.enabled`, `hooksConfig.disabled` | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |

### 4.5 비밀값이 남기 쉬운 곳

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 환경 변수 | `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`(서비스 계정 JSON 키 파일 경로) | 키 파일 경로가 가리키는 JSON 자체가 비밀값 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| `.env` | `.gemini/.env`, `~/.gemini/.env`, 프로젝트 `.env`. 문서 FAQ가 키를 `.gemini/.env`에 두는 방법을 안내 | 프로젝트 안 `.env`는 실수로 커밋되기 쉽다 | https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/faq.md |
| 설정 값 | `settings.json`에서 `"apiKey": "$MY_API_TOKEN"`처럼 변수 참조 가능 | 변수 대신 값이 직접 적힌 경우 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| MCP OAuth 토큰 | `~/.gemini/mcp-oauth-tokens.json` | 파일 기반 토큰 | https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md |
| Google 로그인 캐시 | "credentials will be cached locally"까지만 문서에 있음. 파일 이름·키체인 사용 여부 **미확인** | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/authentication.mdx |

### 4.6 기업 관리 기능

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 시스템 설정 | 4.1절 시스템 덮어쓰기 파일. 객체(`mcpServers`)는 합쳐진다 | 사용자 권한이 충분하면 고칠 수 있다(문서 언급) | https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/enterprise.md |
| 관리 콘솔 제어 | Strict Mode(기본 켜짐, YOLO 금지), Extensions(기본 꺼짐), MCP(기본 꺼짐). "로컬에서 덮어쓸 수 없다" | 로컬 파일로는 확인 불가 | https://github.com/google-gemini/gemini-cli/blob/main/docs/admin/enterprise-controls.md |
| 관리 정책 폴더 | 4.2절 관리자 정책 경로. 문서가 소유권·쓰기 권한 조건을 둔다(Windows는 `C:\ProgramData` 안이어야 함) | 권한이 느슨하면 정책으로 인정되지 않는다 | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/policy-engine.md |

### 4.7 설치 여부 판별

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 설치 | npm `npm install -g @google/gemini-cli`, Homebrew `brew install gemini-cli`, 설치 없이 `npx @google/gemini-cli` | `npx` 사용은 실행 파일이 남지 않아 설치 흔적으로 못 잡는다 | https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/installation.mdx |
| 버전 확인 | `gemini --version` | — | https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md |
| 설정 흔적 | `~/.gemini/` 폴더 | — | 같은 문서 |

---

## 5. GitHub Copilot CLI (요약)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 설정 폴더 | `~/.copilot`(`COPILOT_HOME`으로 변경). `settings.json`(주 설정, 주석 허용), `config.json`(내부 상태: 인증 데이터·신뢰 폴더), `mcp-config.json`(`mcpServers`), `permissions-config.json`(저장된 도구·폴더 승인), `providers.json`(BYOK), `hooks/` | — | https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference |
| 저장소 설정 | `.github/copilot/settings.json`, `.github/copilot/settings.local.json`, 저장소 훅 `.github/hooks/` | 저장소에서 들어오는 설정·훅 | 같은 문서 |
| 위험 플래그 | `--allow-all`(= `--allow-all-tools --allow-all-paths --allow-all-urls`), `--yolo`(= `--allow-all`), `--allow-all-tools`(환경 변수 `COPILOT_ALLOW_ALL`), `--allow-all-paths`, `--allow-all-urls`, `--allow-tool='shell(git:*)'`. 대화 중 `/allow-all`, `/yolo` | 문서: "destructive commands to run without individual approval" | https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference , https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli |
| 비밀값 | 인증 데이터는 `config.json`. `providers.json`의 API 키·Bearer 토큰·헤더 값은 **평문**(문서 경고). MCP OAuth는 키체인을 못 쓰면 `mcp-oauth-config/`, 비밀 자리표시는 `mcp-secrets/`로 대체. 환경 변수 `COPILOT_GITHUB_TOKEN` > `GH_TOKEN` > `GITHUB_TOKEN` | 평문 파일 | 위 두 문서 |
| 기업 관리 | macOS plist `com.github.copilot`, 파일 `/Library/Application Support/GitHubCopilot/managed-settings.json`. Windows `HKLM\SOFTWARE\Policies\GitHubCopilot`, `%ProgramFiles%\GitHubCopilot\managed-settings.json`. Linux `/etc/github-copilot/managed-settings.json`. POSIX에서 심볼릭 링크·root 소유 아님·누구나 쓰기 가능이면 거부. `permissions.disableBypassPermissionsMode: "disable"`은 MDM 값이 항상 이김 | 대부분의 키는 사용자 설정이 MDM 기본값을 덮을 수 있다 | https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference |
| 설치·버전 | npm `@github/copilot`, WinGet `GitHub.Copilot`, Homebrew `brew install --cask copilot-cli`. 버전은 `copilot version` | — | https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli , https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference |

## 6. Amazon Q Developer CLI → Kiro CLI (요약)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 현황 | Kiro 문서에 "Migrating from Q Developer", "Upgrading from Q CLI" 항목이 있다. 후속 제품 관계의 공식 문장은 검색 요약으로만 확인 | 둘 다 점검해야 할 수 있다 | https://kiro.dev/docs/permissions/ |
| Q CLI MCP·에이전트 | 전역 MCP 설정은 `~/.aws/amazonq/cli-agents`(Q CLI), IDE는 `~/.aws/amazonq/agents/default.json`. 도구 권한 수준: 자동 승인 / 승인 필요 / 위험 | — | https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/qdev-mcp.html |
| Kiro 위험 플래그 | `--trust-all-tools`, `/tools trust-all`: "규칙이 거부하지 않는 모든 도구 동작을 신뢰" | 전 도구 자동 승인 | https://kiro.dev/docs/permissions/ |
| Kiro 경로 | 에이전트 `.kiro/agents/`(작업 폴더), `~/.kiro` 아래 `agents`. `~/.kiro/settings/mcp.json`, 옛 `~/.aws/amazonq/mcp.json`은 공식 문서에서 **미확인**(제3자 글에만 있음) | — | https://kiro.dev/docs/permissions/ |
| 자격 증명·버전·기업 정책 | **미확인** | — | — |

---

## 7. 확인하지 못했거나 문서끼리 엇갈린 항목

1. **Claude Desktop**: `claude_desktop_config.json`의 MCP 도구 자동 승인 키, 데스크톱 확장 설치 경로, 앱 실행 파일 위치, 버전 확인 방법, OAuth 토큰 저장 위치 — 모두 미확인.
2. **Claude Desktop 정책 경로 표기 차이**: 일반 지원 문서는 macOS 도메인 `com.anthropic.claudefordesktop`만 밝히고 plist 파일 경로는 3P(제3자 추론) 문서에만 있다. Linux 정책 파일 `/etc/claude-desktop/managed-settings.json`도 3P 문서 기준이다. 키 이름도 두 문서가 다르다(일반: `isLocalDevMcpEnabled` 등 / 3P: `managedMcpServers`, `deploymentMode` 등).
3. **Codex**: `--full-auto` 플래그가 현재 문서에 없다(폐지 여부 미확인). `codex --version` 미확인. MCP `default_tools_approval_mode`의 `auto`·`approve`·`prompt` 각각의 정확한 의미 풀이가 문서에 없다. `approval_policy = "untrusted"`는 폐지됐는데, 관리 문서 예시(`allowed_approval_policies = ["untrusted", "on-request"]`)에는 아직 `untrusted`가 남아 있다(프로젝트 `trust_level = "untrusted"` 호환용으로 설명됨).
4. **Gemini CLI**: Google 로그인 자격 증명 캐시 파일 이름과 키체인 사용 여부 미확인. 영구 승인이 기록되는 정책 파일 이름 미확인. 관리 콘솔 문서는 MCP·확장 기본값을 "꺼짐"으로, 설정 레퍼런스는 `admin.mcp.enabled`·`admin.extensions.enabled` 기본값을 `true`로 적는다(대상이 다른 것으로 보이나 문서가 관계를 설명하지 않음). 문서는 "`--yolo`면 샌드박스가 기본으로 켜진다"고 적는데, 같은 문서의 `tools.sandbox` 설명에는 이 조건이 없다.
5. **Claude Code**: `sandbox.autoAllowBashIfSandboxed` 기본값이 v2.1.324에서 `true`→`false`로 바뀌었다. `permissions.defaultMode: "bypassPermissions"`의 효력 범위가 v2.1.257에서 바뀌었다. 규칙은 버전별로 판정해야 한다.
6. **Amazon Q / Kiro**: 대부분 미확인(자격 증명 위치, 기업 정책, 버전 명령, MCP 파일 경로).

---

## 8. 점검 규칙 후보

규칙 ID는 `도구약어-분류-번호`로 제안한다. 도구약어: CC(Claude Code), CD(Claude Desktop), CX(Codex), GM(Gemini), CP(Copilot), KR(Kiro/Q). 분류: PERM(권한), SBX(샌드박스), MCP, HOOK, SEC(비밀값), MGMT(기업 관리), INST(설치).

비밀값 규칙은 **값을 출력하지 않는다**. 키 이름·파일 경로·줄 번호와 "값이 직접 적혀 있음"만 보고한다.

| 규칙 ID | 탐지 조건 | 심각도 |
|---|---|---|
| CC-PERM-001 | 사용자·관리 설정의 `permissions.defaultMode == "bypassPermissions"` | 상 |
| CC-PERM-002 | 프로젝트·로컬 설정에 `defaultMode: "bypassPermissions"`(v2.1.257 미만이면 상, 이상이면 효력 없음 → 하) | 상/하 |
| CC-PERM-003 | `skipDangerousModePermissionPrompt: true` 존재(우회 모드 사용 흔적) | 중 |
| CC-PERM-004 | 셸 시작 파일·별칭에 `--dangerously-skip-permissions` 또는 `--permission-mode bypassPermissions` | 상 |
| CC-PERM-005 | 합쳐진 `permissions.allow`에 `Bash` 또는 `Bash(*)` | 상 |
| CC-PERM-006 | `permissions.allow`에 `WebFetch(domain:*)` 또는 `mcp__<서버>__*`/`mcp__<서버>` 같은 서버 전체 와일드카드 | 중 |
| CC-PERM-007 | `defaultMode` 가 `auto` 또는 `acceptEdits` | 하 |
| CC-SBX-001 | `sandbox.enabled`가 없거나 false이면서 넓은 Bash 허용(CC-PERM-005)이나 우회 모드 동시 존재 | 상 |
| CC-SBX-002 | `sandbox.enabled: true`인데 `allowUnsandboxedCommands`가 false로 설정되지 않음, 또는 `excludedCommands`에 와일드카드가 넓은 항목 | 중 |
| CC-MCP-001 | `enableAllProjectMcpServers: true` | 상 |
| CC-MCP-002 | `.mcp.json`의 stdio 서버 `command`가 `npx`/`uvx`이고 `args`에 `-y`·버전 미고정 패키지 | 중 |
| CC-MCP-003 | `allowedMcpServers` 미설정(기업 PC 기준) | 하 |
| CC-HOOK-001 | 커밋된 `.claude/settings.json`에 `hooks` 존재(특히 `SessionStart`·`UserPromptSubmit`) | 중 |
| CC-HOOK-002 | `type: "http"` 훅이 있는데 `allowedHttpHookUrls` 없음 | 상 |
| CC-HOOK-003 | 프로젝트 설정에 `apiKeyHelper`·`awsCredentialExport`·`otelHeadersHelper`·`statusLine` 명령 존재 | 중 |
| CC-SEC-001 | 설정 파일 `env` 블록에 `ANTHROPIC_API_KEY`·`ANTHROPIC_AUTH_TOKEN`·`CLAUDE_CODE_OAUTH_TOKEN` 값 직접 기재(특히 커밋된 파일) | 상 |
| CC-SEC-002 | `.mcp.json`·`~/.claude.json` MCP `env`/`headers`에 `${VAR}`가 아닌 직접 값 | 상 |
| CC-SEC-003 | `~/.claude/.credentials.json` 권한이 0600보다 넓음 | 상 |
| CC-SEC-004 | macOS에서 `~/.claude/.credentials.json` 존재(키체인 대체 발생) | 하 |
| CC-SEC-005 | 셸 시작 파일에 `export ANTHROPIC_API_KEY=` 등 평문 | 중 |
| CC-MGMT-001 | 옛 경로 `C:\ProgramData\ClaudeCode\managed-settings.json`만 있고 새 경로 없음 | 중 |
| CC-MGMT-002 | 기업 PC인데 관리 설정에 `disableBypassPermissionsMode`·`allowManagedHooksOnly`·`allowManagedMcpServersOnly` 없음 | 중 |
| CC-MGMT-003 | 정책이 `HKCU`에만 있음(사용자 수정 가능) | 중 |
| CD-MCP-001 | `claude_desktop_config.json`의 `mcpServers.*.env`에 직접 값 | 상 |
| CD-MCP-002 | 파일시스템 MCP 서버 `args`에 홈 디렉터리 전체·루트 경로 | 중 |
| CD-MGMT-001 | 기업 PC인데 Desktop 정책(`isLocalDevMcpEnabled`, `isDesktopExtensionEnabled`)이 없음 | 중 |
| CD-MGMT-002 | `isLocalDevMcpEnabled=false`인데 `isDesktopExtensionEnabled`가 false 아님(확장으로 로컬 서버 가능) | 하 |
| CX-PERM-001 | `sandbox_mode = "danger-full-access"` 또는 `default_permissions = ":danger-full-access"` | 상 |
| CX-PERM-002 | `approval_policy = "never"`이면서 샌드박스가 `read-only`가 아님 | 상 |
| CX-PERM-003 | 셸 시작 파일·별칭에 `--yolo`·`--dangerously-bypass-approvals-and-sandbox` | 상 |
| CX-PERM-004 | `sandbox_workspace_write.network_access = true` | 중 |
| CX-PERM-005 | `approval_policy = "untrusted"`·`"on-failure"`(폐지·폐기 예정 값, 정책 혼동) | 하 |
| CX-PERM-006 | 프로필 파일(`~/.codex/*.config.toml`)에 위 위험 값 | 상 |
| CX-PERM-007 | `notice.hide_full_access_warning` 켜짐 | 하 |
| CX-MCP-001 | `default_tools_approval_mode` 또는 도구별 `approval_mode`가 `prompt`가 아닌 값(의미 미확인이므로 "검토 필요"로 보고) | 중 |
| CX-MCP-002 | `mcp_servers.*.http_headers`·`env`·`oauth.client_secret`에 직접 값 | 상 |
| CX-HOOK-001 | 별칭·스크립트에 `--dangerously-bypass-hook-trust` | 상 |
| CX-HOOK-002 | 프로젝트 `.codex/hooks.json`·`[hooks]` 존재 + 그 프로젝트가 `trust_level = "trusted"` | 중 |
| CX-HOOK-003 | `notify` 명령 존재(목록 보고) | 하 |
| CX-SEC-001 | `~/.codex/auth.json` 존재 + 권한이 소유자 전용보다 넓음 | 상 |
| CX-SEC-002 | `cli_auth_credentials_store = "file"` 또는 `mcp_oauth_credentials_store = "file"` | 중 |
| CX-SEC-003 | `model_providers.*.experimental_bearer_token` 사용 | 상 |
| CX-SEC-004 | `shell_environment_policy.inherit`가 `all`(또는 미설정)이고 `ignore_default_excludes`가 기본값 `true`이며 `filters`도 없음 → 이름에 KEY·SECRET·TOKEN이 든 변수가 모델이 돌리는 명령에 그대로 넘어감 | 중 |
| CX-MGMT-001 | 기업 PC인데 `requirements.toml`·MDM `requirements_toml_base64` 모두 없음 | 중 |
| CX-MGMT-002 | Windows에서 관리 기본값이 `~/.codex/managed_config.toml`에만 있음(사용자 수정 가능) | 하 |
| GM-PERM-001 | 별칭·스크립트에 `--yolo` 또는 `--approval-mode yolo` | 상 |
| GM-PERM-002 | `general.defaultApprovalMode = "auto_edit"` | 하 |
| GM-PERM-003 | `tools.allowed`에 인자 없는 `run_shell_command` | 상 |
| GM-PERM-004 | `security.folderTrust.enabled = false` | 상 |
| GM-PERM-005 | `~/.gemini/policies/*.toml`에 넓은 `decision = "allow"` 규칙(셸 전체 등) | 중 |
| GM-SBX-001 | `tools.sandboxNetworkAccess = true` | 중 |
| GM-MCP-001 | `mcpServers.*.trust = true` | 상 |
| GM-MCP-002 | MCP 서버 별칭에 `_` 포함(정책 오판정) | 하 |
| GM-MCP-003 | `mcpServers.*.env`·`headers`에 직접 값 | 상 |
| GM-HOOK-001 | 프로젝트 `.gemini/settings.json`에 `hooks` 존재 | 중 |
| GM-SEC-001 | 프로젝트 루트 `.env`·`.gemini/.env`에 `GEMINI_API_KEY`/`GOOGLE_API_KEY` + 해당 파일이 git 추적 중 | 상 |
| GM-SEC-002 | `GOOGLE_APPLICATION_CREDENTIALS`가 가리키는 키 파일이 프로젝트 폴더 안에 있음 | 상 |
| GM-SEC-003 | `~/.gemini/mcp-oauth-tokens.json` 권한이 넓음 | 중 |
| GM-MGMT-001 | 기업 PC인데 시스템 `settings.json`에 `security.disableYoloMode`·`admin.secureModeEnabled` 없음 | 중 |
| GM-MGMT-002 | `GEMINI_CLI_SYSTEM_SETTINGS_PATH`가 사용자 환경에 설정돼 기본 시스템 경로를 우회 | 중 |
| CP-PERM-001 | 별칭·스크립트·환경에 `--allow-all`·`--yolo`·`--allow-all-tools`·`COPILOT_ALLOW_ALL` | 상 |
| CP-PERM-002 | `permissions-config.json`에 `shell` 전체 승인 | 중 |
| CP-SEC-001 | `~/.copilot/providers.json`에 키·토큰 존재(문서상 평문) | 상 |
| CP-SEC-002 | `mcp-oauth-config/`·`mcp-secrets/` 폴더 존재(키체인 미사용 대체) | 하 |
| CP-MGMT-001 | 관리 설정 파일이 심볼릭 링크·root 소유 아님·누구나 쓰기 가능(CLI가 거부하므로 정책 무효) | 중 |
| KR-PERM-001 | 별칭·스크립트에 `--trust-all-tools` | 상 |
| ALL-INST-001 | 설치 판별: `claude`/`codex`/`gemini`/`copilot` 실행 파일 위치와 `--version`(Codex·Desktop은 미확인이라 존재만 보고) | 정보 |
| ALL-SEC-001 | 설정·로그 파일이 iCloud·Dropbox 같은 동기화 폴더 안에 있음(심볼릭 링크 대상 포함) | 중 |
