# 02. IDE·편집기 확장 설정 조사 — VS Code(Copilot) · Cursor · Windsurf(Devin Desktop) · Cline · Roo Code · Continue · JetBrains

`ai-tool-audit`(개발자 PC의 AI 도구 설정을 읽기 전용으로 점검하는 CLI)의 점검 규칙 근거 자료다. 01편(Claude Code·Codex·Gemini·Copilot CLI)에 이어 IDE와 IDE 확장을 다룬다.

- 조사 기준일: 2026-11-24. 공식 문서·공식 저장소(소스 코드 포함)·공식 변경 기록에서 확인한 것만 적었다.
- 문서에서 찾지 못한 것은 **미확인**으로 표시했다. 공식 문서가 아니라 커뮤니티·보안 업체 글에서만 본 것은 **(비공식)**을 붙였다.
- 공식 문서가 없고 공식 저장소 소스 코드에서 확인한 것은 **(소스)**를 붙였다. 소스는 버전에 따라 바뀌므로 규칙에 버전 조건을 달아야 한다.
- "위험한 이유"는 문서에 적힌 동작에서 끌어낸 판단이다. 문서가 직접 경고한 경우 "(문서 경고)"를 붙였다.
- 표기: `~`는 사용자 홈 디렉터리(Windows는 `%USERPROFILE%`).

### 먼저 알아 둘 변화 (2026년 안에 바뀐 것)

| 변화 | 점검기에 주는 영향 | 출처 URL |
|---|---|---|
| VS Code 문서가 `/docs/copilot/...`에서 `/docs/agents/...`로 옮겨졌고, 에이전트 실행 방식이 "하네스(harness)"로 나뉘었다: Copilot 하네스, Local 하네스(사용 중단 예정, 2027년 2월 제거), Claude·Codex 하네스 | 같은 기능이라도 하네스마다 읽는 설정 파일이 다르다. Local 하네스 전용 키(`chat.useAgentsMdFile` 등)는 곧 의미가 없어진다 | https://code.visualstudio.com/docs/agents/run/approvals.md , https://code.visualstudio.com/docs/enterprise/manage-ai-settings.md |
| Windsurf가 2026-06-02에 **Devin Desktop**으로 이름을 바꿨다. 사용자 데이터·확장 폴더 경로가 바뀌었고 `~/.codeium/`은 그대로다 | 옛 경로와 새 경로를 둘 다 봐야 한다 | https://docs.devin.ai/desktop/devin-desktop-faq.md |
| Roo Code 저장소가 **보관(archived)** 처리됐다(마지막 push 2026-05-15) | 설치돼 있으면 보안 수정이 더 나오지 않는 확장이다 | GitHub API `repos/RooCodeInc/Roo-Code` → `archived: true` (https://github.com/RooCodeInc/Roo-Code) |
| Cline이 설정 저장소를 VS Code 확장 전용 저장소(globalStorage)에서 `~/.cline/`로 옮겼다(IDE·CLI·SDK 공용) | 옛 경로(globalStorage)와 새 경로를 둘 다 봐야 한다 | https://github.com/cline/cline/blob/main/docs/getting-started/config.mdx , https://github.com/cline/cline/blob/main/apps/vscode/src/hosts/vscode/mcp-settings-legacy-migration.ts |

---

## 1. VS Code 본체 + GitHub Copilot(에이전트)

### 1.1 설정 파일 위치

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 사용자 settings.json | macOS `~/Library/Application Support/Code/User/settings.json` / Windows `%APPDATA%\Code\User\settings.json` / Linux `~/.config/Code/User/settings.json` | 아래 자동 승인 키가 모든 작업 공간에 적용된다 | https://code.visualstudio.com/docs/configure/settings |
| 프로필 settings.json | `.../Code/User/profiles/<프로필 ID>/settings.json` (프로필에서 설정을 한 번이라도 바꿨을 때만 생김) | 기본 settings.json만 보면 프로필에 숨은 위험 설정을 놓친다 | https://code.visualstudio.com/docs/configure/settings |
| 작업 공간 설정 | `<프로젝트>/.vscode/settings.json` | 남의 저장소를 열면 그 저장소가 정한 설정이 들어온다. 실행 파일 경로 4종(`git.path`, `terminal.external.*Exec`)만 작업 공간에서 무시된다 | https://code.visualstudio.com/docs/configure/settings |
| 확장 전역 저장소(globalStorage) | `<사용자 데이터>/User/globalStorage/<게시자.확장ID>/` (예: Cline `saoudrizwan.claude-dev`, Roo `rooveterinaryinc.roo-cline`). 폴더 규칙은 확장 소스에서 확인. VS Code 공식 문서가 OS별 절대 경로를 적어 둔 곳은 **미확인** | 확장이 MCP 설정·API 키를 여기 둔다 | (소스) https://github.com/cline/cline/blob/main/apps/vscode/src/hosts/vscode/mcp-settings-legacy-migration.ts |
| Insiders·VSCodium 등 | 폴더 이름만 다른 변형(`Code - Insiders` 등)의 경로 | 공식 문서에서 이번에 확인하지 못함 → **미확인** | — |

### 1.2 위험한 자동 승인 설정 (기본값은 AI 설정 참조 문서 기준)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 전역 자동 승인 | `chat.tools.global.autoApprove` 기본 `false`. `true`면 위험 | 문서 설명: "Automatically approve all tools - this setting disables critical security protections." 모든 작업 공간에서 파일 편집·명령 실행·외부 도구 호출을 묻지 않는다(문서 경고) | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/docs/agents/run/approvals.md |
| 터미널 명령 규칙 | `chat.tools.terminal.autoApprove` 기본 `{ "rm": false, "rmdir": false, "del": false, "kill": false, "curl": false, "wget": false, "eval": false, "chmod": false, "chown": false, "/^Remove-Item\\b/i": false }`. 값 `true` = 묻지 않고 실행. 정규식 키(`"/^npm run lint$/"`), 객체형 `{ "approve": true, "matchCommandLine": true }` 가능 | 사용자가 `bash`·`sh`·`python`·`node`·`curl` 같은 범용 실행기나 `"/.*/"`류 정규식을 `true`로 넣으면 사실상 전부 자동 실행. 기본 거부 항목(`curl`, `rm` 등)을 `true`로 뒤집은 것도 위험 신호 | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/docs/agents/run/approvals.md |
| 규칙 기반 터미널 승인 스위치 | `chat.tools.terminal.enableAutoApprove` 기본 `true` | 꺼 두면 규칙·저장된 승인을 쓰지 않는다(안전 쪽). 정책 이름 `ChatToolsTerminalEnableAutoApprove` | 같은 출처 |
| 기본 규칙 무시 | `chat.tools.terminal.ignoreDefaultAutoApproveRules` (실험) | 켜면 위의 기본 거부 목록(rm·curl 등)이 빠진다 | https://code.visualstudio.com/docs/agents/run/approvals.md |
| 터미널 프롬프트 자동 응답 | `chat.tools.terminal.autoReplyToPrompts` 기본 `false` | 켜면 `[y/N]` 같은 확인 질문에 기본값으로 자동 답한다 | https://code.visualstudio.com/docs/agents/reference/ai-settings |
| 민감 파일 편집 승인 | `chat.tools.edits.autoApprove` 기본 `{}`. 글롭 → 불리언. 예 `"**/.env": false` = 편집 전 승인 필요 | `"**/*": true`처럼 넓게 `true`를 주면 설정 파일(`.vscode/*.json`)·`.env` 편집도 묻지 않는다. VS Code가 기본으로 보호하는 파일 목록은 문서에 명시돼 있지 않음 → 기본 목록 **미확인** | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/updates/v1_104 |
| URL 자동 승인 | `chat.tools.urls.autoApprove` 기본 `[]`. URL 패턴 → `true` 또는 `{ "approveRequest", "approveResponse" }` | 넓은 패턴이면 에이전트가 외부로 데이터를 보내거나, 인젝션이 섞인 응답을 검토 없이 받는다. 문서: URL 승인은 응답 내용을 검토하지 않는다 | https://code.visualstudio.com/docs/agents/run/approvals.md , https://code.visualstudio.com/docs/agents/run/security.md |
| 자동 승인 대상 제외 | `chat.tools.eligibleForAutoApproval` (도구 → `false`면 항상 수동 승인) | 있으면 안전 쪽. 정책 `ChatToolsEligibleForAutoApproval` | https://code.visualstudio.com/docs/agents/run/approvals.md |
| 권한 수준 기본값 | `chat.defaultConfiguration` 예 `{ "approvals": "assisted" }` (Copilot), `chat.permissions.default` (Local). Copilot 수준: Manual(기본) / Assisted / Allow all. Local: Default / Allow all / Autopilot(미리보기). Claude 하네스: Bypass Permissions 등. Codex 하네스: Full Access | "Allow all"·Bypass Permissions·Full Access는 도구 호출 검토 기회를 없앤다(문서 경고). Codex Full Access는 샌드박스도 끈다 | https://code.visualstudio.com/docs/agents/run/approvals.md |
| 세션 한정 우회 | 채팅 명령 `/yolo`, `/autoApprove` | 파일에 남지 않으므로 정적 점검으로는 못 잡는다(정보로만 적음) | (검색 결과 요약) https://code.visualstudio.com/docs/agents/run/approvals — 본문에서 직접 재확인은 **미확인** |
| 에이전트 요청 상한 | `chat.agent.maxRequests` 기본 `25` | 값을 크게 올리면 자동 승인 상태에서 사람 개입 없이 오래 돈다 | https://code.visualstudio.com/docs/agents/reference/ai-settings |
| 에이전트 샌드박스(Local) | `chat.agent.sandbox.enabled` 기본 `off` (`off`/`on`). Copilot 샌드박스는 "Outbound network access is allowed by default" | 샌드박스 없이 자동 승인을 쓰면 명령이 사용자 권한 그대로 돈다. 문서는 인젝션이 걱정되면 자동 승인 대신 샌드박스·개발 컨테이너를 쓰라고 한다 | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/docs/agents/run/security.md |
| 에이전트 자체 | `chat.agent.enabled` 기본 `true` (정책 `ChatAgentMode`) | 정보용 | https://code.visualstudio.com/docs/agents/reference/ai-settings |

### 1.3 MCP 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 작업 공간 MCP (편집기 형식) | `<프로젝트>/.vscode/mcp.json`, 최상위 `"servers": {}`, 선택 `"inputs": []`, `"sandbox": {}` | 저장소가 MCP 서버(=로컬 명령)를 들고 온다. 문서: 작업 공간 MCP는 작업 공간 신뢰를 이어받아, 폴더를 신뢰하면 별도 신뢰 확인 없이 시작될 수 있다 | https://code.visualstudio.com/docs/agents/reference/mcp-configuration , https://code.visualstudio.com/docs/agents/run/security.md |
| 작업 공간 루트 MCP (Copilot 형식) | `<프로젝트>/.mcp.json`, 최상위 `"mcpServers": {}` | 위와 같음. `.vscode/mcp.json`만 보면 놓친다 | https://code.visualstudio.com/docs/agents/reference/mcp-configuration |
| 사용자 MCP | Copilot: `$COPILOT_HOME/mcp-config.json` 또는 `~/.copilot/mcp-config.json`. Local 하네스: 사용자 프로필의 `mcp.json`(OS별 절대 경로는 문서에 없음 → **미확인**, 관례상 `.../Code/User/mcp.json`) | 모든 작업 공간에 적용 | https://code.visualstudio.com/docs/agents/reference/mcp-configuration |
| 서버 필드(편집기 형식) | `type`(`stdio`/`http`/`sse`), `command`, `args`, `cwd`, `env`, `envFile`, `dev`, `sandboxEnabled`, `sandbox`, `url`, `headers`, `oauth` | `env`·`headers`에 키를 평문으로 넣으면 저장소·백업으로 샌다. `${input:...}`(`password: true`)나 `${env:NAME}` 참조가 안전한 방법 | https://code.visualstudio.com/docs/agents/reference/mcp-configuration |
| 서버 필드(Copilot 형식) | `type`, `command`, `args`, `env`, `cwd`, `url`, `headers`, `tools`, `oauthClientId`. 변수 `${NAME}`, `${NAME:-default}` | `tools`는 쓸 도구를 고를 뿐 "doesn't bypass tool approvals" | 같은 출처 |
| MCP 샌드박스 | `sandbox.filesystem.allowWrite/denyRead/denyWrite`, `sandbox.network.allowedDomains/deniedDomains` (서버 단위에만 허용 규칙 유효) | Local 하네스에서는 편집기 샌드박스가 걸린 MCP 도구가 **자동 승인**된다. 샌드박스 범위가 넓으면 자동 승인 범위도 넓다 | 같은 출처 |
| 다른 앱 설정 가져오기 | `chat.mcp.discovery.enabled` 기본 `false`(Copilot CLI 출처만 켜짐). 출처: Claude Desktop `claude_desktop_config.json`, Cursor `~/.cursor/mcp.json`·`<ws>/.cursor/mcp.json`, Windsurf `~/.codeium/windsurf/mcp_config.json` | 켜면 다른 도구의 MCP 서버가 VS Code에도 붙는다. 점검기는 이 출처 파일도 함께 읽어야 한다 | https://code.visualstudio.com/docs/agents/reference/mcp-configuration , https://code.visualstudio.com/docs/agents/reference/ai-settings |
| MCP 접근 범위 | `chat.mcp.access` 기본 `true` (값 `"none"`이면 차단, 정책 `ChatMCP`) | 정보용. 기업 정책 점검에 쓴다 | 같은 출처 |
| 자동 시작 | `chat.mcp.autostart` 기본 `newAndOutdated` | 새로 추가·변경된 서버가 채팅 메시지를 보낼 때 자동으로 뜬다 | https://code.visualstudio.com/docs/agents/reference/ai-settings |
| MCP 도구 개별 자동 승인 키 | 편집기 쪽 `alwaysAllow` 같은 서버별 키는 문서에 없음. 저장된 승인은 UI("In this Session" 등)로 관리 | 저장 위치 **미확인** | https://code.visualstudio.com/docs/agents/run/security.md |

### 1.4 자동 실행 위험 (작업 공간 신뢰·작업)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 폴더 열 때 작업 실행 | `<프로젝트>/.vscode/tasks.json`의 작업에 `"runOptions": { "runOn": "folderOpen" }` | "The task will be run when the containing folder is opened." 저장소를 여는 것만으로 명령이 돈다 | https://code.visualstudio.com/docs/editor/tasks |
| 자동 작업 허용 | `task.allowAutomaticTasks`: `off`(기본, 처음 한 번 허용/거부를 묻는다) / `on`(신뢰된 작업 공간에서 묻지 않고 실행) | `on`이면 신뢰한 폴더의 `folderOpen` 작업이 바로 돈다. 문서: 신뢰하지 않은 작업 공간에서는 이 설정과 상관없이 실행되지 않는다 | https://code.visualstudio.com/docs/editor/tasks |
| 작업 공간 신뢰 켜기 | `security.workspace.trust.enabled` 기본 `true` | `false`면 제한 모드(Restricted Mode)가 사라져 작업·디버그·작업 공간 설정·확장이 모두 바로 동작한다 | https://code.visualstudio.com/docs/editor/workspace-trust |
| 시작 시 신뢰 확인 | `security.workspace.trust.startupPrompt` 값 `never`/`once`, 문서상 기본 `never` (다른 값 전체 목록은 문서에 없음) | 정보용 | 같은 출처 |
| 빈 창 신뢰 | `security.workspace.trust.emptyWindow` 기본 `true` | 폴더 없이 연 창은 신뢰된 상태 | 같은 출처 |
| 낱개 파일 | `security.workspace.trust.untrustedFiles` 값 `open`/`newWindow`/기본(prompt) | `open`이면 신뢰 밖 파일을 묻지 않고 신뢰 창에서 연다 | 같은 출처 |
| 배너 | `security.workspace.trust.banner` 기본 `untilDismissed` | 정보용 | 같은 출처 |
| 제한 모드에서 막히는 것 | AI 에이전트("disables agents in that workspace"), 터미널, 작업, 디버그, 일부 작업 공간 설정, 신뢰 미지원 확장 | 신뢰를 끄면 이 방어가 통째로 빠진다 | https://code.visualstudio.com/docs/editor/workspace-trust |
| 신뢰한 폴더 목록 | 저장 위치 공식 문서 **미확인** (관리 UI: Workspaces: Manage Workspace Trust) | 홈 디렉터리 전체 같은 넓은 상위 폴더를 신뢰했는지 보고 싶지만 파일 위치를 문서로 확인하지 못함 | — |
| 훅(hooks) | `chat.useHooks` 기본 `true`(Local), `chat.hookFilesLocations` 기본 `{}`. 문서: 훅은 에이전트 작업 중 특정 시점에 동작을 실행한다 | 저장소에 들어 있는 훅이 코드 실행 경로가 된다. 작업 공간 훅 파일의 정확한 경로는 **미확인** | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/docs/agent-customization/overview.md |

### 1.5 규칙·지시 파일 (프롬프트 인젝션 경로)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 저장소 지시 | `.github/copilot-instructions.md` (`github.copilot.chat.codeGeneration.useInstructionFiles` 기본 `true`) | 저장소에 든 글이 매 요청에 자동으로 붙는다. 문서: "Instructions guide the model; they aren't an enforcement boundary." | https://code.visualstudio.com/docs/agents/reference/custom-instructions-reference.md , https://code.visualstudio.com/docs/agents/reference/ai-settings |
| AGENTS.md | 루트 `AGENTS.md`(`chat.useAgentsMdFile` 기본 `true`), 하위 폴더 `AGENTS.md`(Copilot·Codex 하네스는 탐색, Local은 `chat.useNestedAgentsMdFiles` 기본 `false`) | 하위 폴더 깊은 곳에 숨긴 지시 파일도 읽힌다 | 같은 출처 |
| CLAUDE.md | `CLAUDE.md`, `.claude/CLAUDE.md` (`chat.useClaudeMdFile` 기본 `true`), `.claude/rules/` | Claude Code용 파일이 VS Code 에이전트에도 들어간다 | 같은 출처 |
| 조건부 지시 | `.github/instructions/**/*.instructions.md` (`applyTo` 글롭) | `applyTo: "**"`면 항상 붙는다 | 같은 출처 |
| 지시 위치 목록 | `chat.instructionsFilesLocations` 기본 `{ ".github/instructions": true, ".claude/rules": true, "~/.copilot/instructions": true, "~/.claude/rules": true }` | 작업 공간 설정으로 위치를 더 늘릴 수 있다 | https://code.visualstudio.com/docs/agents/reference/ai-settings |
| 프롬프트·에이전트·스킬 | `.github/prompts/*.prompt.md`, `.github/agents/*.agent.md`·`.claude/agents`, 스킬 `.agents/skills`·`.github/skills`·`.claude/skills` (각 `chat.*Locations` 기본값) | 커스텀 에이전트·스킬은 도구·스크립트를 끌어 쓸 수 있다 | https://code.visualstudio.com/docs/agents/reference/ai-settings , https://code.visualstudio.com/docs/agent-customization/overview.md |
| 사용자 전역 지시 | `~/.copilot/copilot-instructions.md`, `~/.copilot/instructions/**/*.instructions.md`, `~/.claude/CLAUDE.md` | 모든 프로젝트에 적용 | https://code.visualstudio.com/docs/agents/reference/custom-instructions-reference.md |
| 조직 지시 | `github.copilot.chat.organizationInstructions.enabled` 기본 On | GitHub 조직이 정한 지시가 붙는다(정보용) | 같은 출처 |

### 1.6 설치된 확장 목록

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 확장 폴더 | Windows `%USERPROFILE%\.vscode\extensions` / macOS·Linux `~/.vscode/extensions`. `--extensions-dir <dir>` 옵션이나 `VSCODE_EXTENSIONS` 환경 변수로 바뀐다 | 점검기가 기본 경로만 보면 놓친다 | https://code.visualstudio.com/docs/configure/extensions/extension-marketplace |
| 명령 | `code --list-extensions`, `code --list-extensions --show-versions` | 읽기 전용으로 버전까지 얻을 수 있다 | 같은 출처 |
| 확장 허용 목록 | `extensions.allowed`: 게시자 키(`"microsoft": true`), 확장 키(`"esbenp.prettier-vscode": true`), 버전 배열(`["3.0.0"]`, `"5.0.0@win32-x64"`), `"stable"`, `"*": false`. 더 구체적인 키가 이긴다 | 설정이 없으면 모든 확장이 허용된다. 로컬 VSIX는 패키지 안 ID로만 판정하고 출처를 검증하지 않는다 | https://code.visualstudio.com/docs/enterprise/extensions |

### 1.7 기업 정책 (VS Code 장치 정책 + Copilot 관리 설정)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| Windows 정책 위치 | 레지스트리 `Software\Policies\Microsoft\VSCode` (HKLM 또는 HKCU), ADMX/ADML | 사용자·작업 공간 설정을 덮어쓴다 | https://code.visualstudio.com/docs/enterprise/policies.md |
| macOS 정책 | 구성 프로파일(`.mobileconfig`). 앱 번들 `Contents/Resources/app/policies`에 샘플. 환경설정 도메인 이름은 문서에 없음 → **미확인** | 같은 출처 | https://code.visualstudio.com/docs/enterprise/policies.md |
| Linux 정책 | `/etc/vscode/policy.json` (1.106 이상) | 같은 출처 | https://code.visualstudio.com/docs/enterprise/policies.md |
| AI 관련 정책 이름 | `ChatAgentMode`(`chat.agent.enabled`), `ChatToolsAutoApprove`(`chat.tools.global.autoApprove`, 문서가 켜지 말라고 강하게 권고), `ChatToolsEligibleForAutoApproval`, `ChatToolsTerminalEnableAutoApprove`, `ChatMCP`(`chat.mcp.access`), `ChatAllowedMcpServers`, `ChatDeniedMcpServers`, `ChatAllowManagedMcpServersOnly`, `ChatAgentNetworkFilter`, `ChatAgentAllowedNetworkDomains`, `ChatAgentDeniedNetworkDomains`, `ChatAgentExtensionTools`, `ChatHooks`, `ChatAllowManagedHooksOnly`, `ChatPluginsEnabled`, `ChatDefaultConfiguration`, `Claude3PIntegration`, `Codex3PIntegration`, `ChatApprovedAccountOrganizations`, `ChatStrictPluginOnlyCustomization`, `BrowserChatTools` | 기업 PC에서 이 값이 비어 있으면 사용자가 자동 승인·MCP를 마음대로 켤 수 있다 | https://code.visualstudio.com/docs/enterprise/policies.md |
| 확장 정책 | `AllowedExtensions`(`extensions.allowed`), `ExtensionGalleryServiceUrl`, `ExtensionsAutoUpdate` | 같은 출처 | https://code.visualstudio.com/docs/enterprise/policies.md |
| 작업 공간 신뢰 정책 | VS Code 정책 표에 작업 공간 신뢰 항목이 **없다** | 신뢰 끄기를 VS Code 정책으로 막을 방법이 문서에 없음 | https://code.visualstudio.com/docs/enterprise/policies.md |
| Copilot 관리 설정 | `copilot/managed-settings.json`, `copilot/team-mappings.json`, `copilot/teams/` (서버·MDM·파일로 배포). 키 `allowedMcpServers`/`deniedMcpServers`(매처 `serverUrl`·`serverCommand`·`serverName`), `permissions.disableBypassPermissionsMode`, `permissions.disableAssistedPermissionsMode`, `permissions.defaultMode`, `sandbox.enabled`, `vscode.allowedHarnesses`. 우선순위 MDM > 서버 > 파일 > 사용자. 같은 항목이면 장치 정책보다 관리 설정이 이긴다. 파일 배포 시 장치 안 경로는 **미확인** | 정책 적용 여부는 **Developer: Policy Diagnostics**로 확인하라고 문서가 안내(읽기 전용 CLI로 재현하는 방법은 **미확인**) | https://code.visualstudio.com/docs/enterprise/manage-ai-settings.md , https://github.blog/changelog/2026-08-06-mcp-allowlists-in-enterprise-managed-settings |
| GitHub 조직·엔터프라이즈 정책 | "MCP servers in Copilot"(엔터프라이즈: AI controls > MCP, 조직: Copilot > Policies > Features), MCP 레지스트리 제한(공개 미리보기). 이 정책은 Cursor·Windsurf·Claude 같은 타사 호스트의 GitHub MCP 서버는 통제하지 않는다 | 서버 쪽 정책이라 PC에서 읽을 수 없다(정보용) | https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-mcp-usage/configure-mcp-server-access , https://docs.github.com/en/copilot/concepts/mcp-management |

---

## 2. Cursor

Cursor는 VS Code를 바탕으로 만든 편집기다. 그러나 VS Code 문서의 경로·기본값을 Cursor에 그대로 쓸 수 없다(작업 공간 신뢰 기본값부터 다르다는 보고가 있다).

### 2.1 설정 파일 위치

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 사용자 settings.json | macOS `~/Library/Application Support/Cursor/User/settings.json`, Windows `%APPDATA%\Cursor\User\`, Linux `~/.config/Cursor/User/` | Cursor 공식 문서에서 확인하지 못함 → **미확인 (비공식 출처에서만 확인)** | (비공식) https://forum.cursor.com/t/where-is-the-default-environment-settings-path/17269 |
| 작업 공간 설정 | `<프로젝트>/.vscode/settings.json` (VS Code 호환) | Cursor 문서 명시 **미확인** | — |
| 에이전트 승인 설정 저장 위치 | 실행 모드(Run Mode)·허용 목록은 UI(Settings > Agents > Approvals & Execution)에서 정한다. 이 값이 저장되는 파일은 문서에 없음 → **미확인** | 정적 점검으로 실행 모드를 읽을 방법이 문서로 확인되지 않음 | https://cursor.com/docs/agent/security/run-modes |
| 자동 검토 지침 | `~/.cursor/permissions.json`(전체), `<프로젝트>/.cursor/permissions.json`(프로젝트). 키 `autoRun.allow_instructions`, `autoRun.block_instructions`. 둘 다 있으면 합쳐지고, 팀 설정이 있으면 둘 다 무시 | 저장소가 `.cursor/permissions.json`으로 "이런 건 허용 쪽으로"라는 지침을 들고 올 수 있다. 문서: 분류기는 "not a security boundary" | https://cursor.com/docs/agent/security/run-modes |
| 샌드박스 설정 | `~/.cursor/sandbox.json`(Nightly는 `~/.cursor-nightly/sandbox.json`), `<프로젝트>/.cursor/sandbox.json`(프로젝트가 우선). 키 `readBoundary`, `additionalReadPaths`, `disableTmpWrite`, `privateTmp`, 네트워크 도메인 허용 목록 | 프로젝트 파일이 우선하므로 저장소가 샌드박스 네트워크·읽기 범위를 넓힐 수 있다. 관리자 정책과 Cursor 내장 규칙은 그 위에 얹혀 약화되지 않는다 | https://cursor.com/docs/agent/security/run-modes |
| CLI 권한 | `~/.cursor/cli-config.json`, `<프로젝트>/.cursor/cli.json`. `permissions.allow`/`deny` 배열, 토큰 `Shell(cmd)`·`Shell(curl:*)`, `Read(glob)`, `Write(glob)`, `WebFetch(domain)`, `Mcp(server:tool)`. 거부가 우선. 플래그 `--force` | `Shell(*)`·`Write(**)`·`Mcp(*:*)` 같은 넓은 허용. 프로젝트 `cli.json`이 허용을 늘릴 수 있는지는 문서에 없음 → **미확인** | https://cursor.com/docs/cli/reference/permissions |

### 2.2 위험한 자동 실행 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 실행 모드 | **Auto-review**(권장 기본: 허용 목록은 바로, 나머지 셸은 가능하면 샌드박스, 아니면 분류기), **Allowlist**, **Run Everything**(모든 도구 호출을 샌드박스·분류기 없이 자동 실행), Ask Every Time(3.5에서 사용 중단) | Run Everything이 흔히 말하는 "YOLO"에 해당. 파일 위치를 몰라 정적 점검 불가 → 기업 정책·팀 설정 점검으로 대신 | https://cursor.com/docs/agent/security/run-modes |
| 보호 기능 | Browser Protection, File-Deletion Protection(`rm` 포함), External-File Protection(작업 공간 밖 파일 생성·수정·삭제). 샌드박스는 `.git/config`, `.git/hooks`, `.vscode`, `.cursorignore`를 보호 | 보호를 끈 상태가 위험. 저장 위치 **미확인** | https://cursor.com/docs/agent/security/run-modes |
| 읽기 범위 | Read Access: System(기본, 작업 공간 밖 읽기도 승인 없음) / Workspace | 기본값이 작업 공간 밖(예: `~/.ssh`, `~/.aws`) 읽기를 묻지 않는다 | https://cursor.com/docs/agent/security/run-modes |
| 샌드박스 네트워크 | sandbox.json Only / sandbox.json + Defaults(기본) / Allow All | Allow All이면 샌드박스 안에서도 외부로 나간다 | https://cursor.com/docs/agent/security/run-modes |
| 플랫폼 조건 | Linux 샌드박스는 커널 6.2+·Landlock v3·비특권 user namespace 필요. 없으면 명령마다 승인 요청 | 점검기가 커널 조건을 함께 보고할 수 있다 | https://cursor.com/docs/agent/security/run-modes |

### 2.3 MCP

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 파일 | 프로젝트 `<프로젝트>/.cursor/mcp.json`, 전역 `~/.cursor/mcp.json` | 저장소가 MCP 서버(로컬 명령)를 들고 온다 | https://cursor.com/docs/context/mcp |
| 구조 | `mcpServers.<이름>`: stdio는 `type: "stdio"`(필수), `command`(필수), `args`, `env`, `envFile`. 원격은 `url`, `headers`, `auth`(`CLIENT_ID`, `CLIENT_SECRET`, `scopes`) | `env`·`headers`·`auth.CLIENT_SECRET`에 평문 비밀값 | 같은 출처 |
| 변수 | `${env:NAME}`, `${userHome}`, `${workspaceFolder}`, `${workspaceFolderBasename}`, `${pathSeparator}` | `${env:...}` 참조는 안전한 쪽 | 같은 출처 |
| 도구 승인 | 기본은 MCP 도구 실행 전 승인. MCP 도구도 실행 모드를 따른다(Auto-review에서는 허용 목록 도구는 바로 실행) | 실행 모드가 Run Everything이면 MCP도 전부 자동 | 같은 출처 |
| 팀 통제 | Team Settings > MCP Configuration의 MCP Allowlist(명령 항목·URL 항목·도구 허용 목록) | 서버 쪽 설정(정보용) | 같은 출처 |

### 2.4 자동 실행 위험 (작업 공간 신뢰)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 작업 공간 신뢰 기본값 | Cursor는 작업 공간 신뢰가 **기본으로 꺼진 채** 배포된다는 보안 업체 보고. 그래서 `.vscode/tasks.json`의 `runOn: "folderOpen"` 작업이 폴더를 열자마자 실행된다. Cursor 쪽 답변은 "사용자가 켤 수 있다" | 저장소 열기만으로 코드 실행. Cursor 공식 문서에서 기본값 확인은 **미확인** (비공식: 보안 업체 보고) | (비공식) https://www.oasis.security/blog/cursor-security-flaw |
| 신뢰 정책 | 기업 정책 `WorkspaceTrustEnabled` → `security.workspace.trust.enabled` | 정책이 있다는 사실 자체가 기본값이 꺼져 있을 수 있음을 뒷받침한다(해석) | https://cursor.com/docs/enterprise/deployment-patterns |
| 권장 완화 | `security.workspace.trust.enabled: true`, `task.allowAutomaticTasks: "off"`, 저장소의 `"runOn": "folderOpen"` 검색 | 같은 보고서 | (비공식) https://www.oasis.security/blog/cursor-security-flaw |

### 2.5 규칙·지시 파일

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 프로젝트 규칙 | `.cursor/rules/` 안 `.mdc` 파일(하위 폴더 허용). 문서: ".md"는 무시된다는 문서와 `.cursor/rules/`만 언급한 도움말이 공존 | `alwaysApply: true`면 모든 대화에 들어간다 | https://cursor.com/docs/context/rules , https://cursor.com/help/customization/rules |
| 머리말(frontmatter) | `alwaysApply`, `globs`, `description` | `globs`가 넓거나 `alwaysApply: true`인 규칙이 인젝션 위험이 크다 | https://cursor.com/docs/context/rules |
| `.cursorrules` | 프로젝트 루트. "legacy and will be deprecated" | 여전히 읽힐 수 있다(에이전트 모드에서 무시된다는 커뮤니티 보고 있음, 비공식) | https://cursor.com/help/customization/rules |
| AGENTS.md | 루트와 하위 폴더 | 하위 폴더 파일은 그 폴더 아래 작업에 적용 | https://cursor.com/docs/context/rules |
| CLAUDE.md | 루트. "always applied to every conversation, regardless of any alwaysApply" | Claude Code용 파일이 Cursor에도 무조건 들어간다 | https://cursor.com/help/customization/rules |
| 사용자 규칙 | `~/.cursor/rules` (Windows `%USERPROFILE%\.cursor\rules`), 계정 동기화 규칙, 팀 규칙(서버) | 전 프로젝트 적용 | https://cursor.com/help/customization/rules |

### 2.6 확장 목록

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 확장 폴더 | `~/.cursor/extensions/` (원격 SSH 호스트는 `~/.cursor-server/extensions/`) | Cursor 공식 문서 **미확인 (비공식 출처에서만 확인)** | (비공식) https://forum.cursor.com/t/extension-fail-to-install-if-cursor-server-is-deleted/153546 |
| CLI 목록 명령 | `cursor --list-extensions` | 공식 문서 **미확인** | — |

### 2.7 기업 정책

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| Windows | 레지스트리 기반 그룹 정책(ADMX/ADML: `AppData\Local\Programs\cursor\policies`). 레지스트리 키 경로는 문서에 없음 → **미확인**. 컴퓨터 수준이 사용자 수준보다 우선 | — | https://cursor.com/docs/enterprise/deployment-patterns |
| macOS | 구성 프로파일, `PayloadType` = `com.todesktop.230313mzl4w4u92`(정식) / `co.anysphere.cursor.nightly`(Nightly) | — | 같은 출처 |
| Linux | `~/.cursor/policy.json` (Cursor 2.0+). 없으면 제한 없음 | 사용자 홈에 있는 파일이라 사용자가 지울 수 있다(해석) | 같은 출처 |
| 정책 목록 | `AllowedExtensions`, `AllowedTeamId`, `ExtensionGalleryServiceUrl`, `NetworkDisableHttp2`, `UpdateMode`, `WorkspaceTrustEnabled` | 장치 정책으로는 실행 모드·MCP를 강제할 수 없다. 그건 팀 대시보드(서버) 몫 | 같은 출처 |
| 팀 설정(서버) | 실행 모드 제한, 샌드박스 네트워크 규칙, 읽기 정책, Auto-review 설정, MCP Allowlist. 팀 설정이 개인·프로젝트 설정을 덮어씀 | PC에서 읽을 수 없음(정보용) | https://cursor.com/docs/agent/security/run-modes , https://cursor.com/docs/context/mcp |

---

## 3. Windsurf → Devin Desktop

2026-06-02에 이름이 바뀌었다. 지금 공식 문서(docs.windsurf.com → docs.devin.ai로 넘어감)는 새 구조(Devin Local 에이전트)만 설명한다. 예전 Windsurf(Cascade) 키는 현재 문서에서 찾을 수 없어 따로 표시했다.

### 3.1 설정 파일 위치

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| `~/.codeium/` | 그대로 유지: `user_settings.pb`, `mcp_config.json`, `~/.codeium/windsurf/` 하위(전역 워크플로·스킬·CLI 실행 파일 `bin/`) | 옛 경로가 계속 살아 있다 | https://docs.devin.ai/desktop/devin-desktop-faq.md |
| IDE 사용자 settings.json | Windsurf 폴더 → Devin 폴더로 이동. macOS 예 `~/Library/Application Support/Devin/User/settings.json`. 옛 Windsurf 폴더의 정확한 경로와 Windows·Linux 경로는 **미확인** | 두 위치를 모두 봐야 한다 | 같은 출처 |
| 확장 폴더 | `~/.windsurf/extensions/` → `~/.devin/extensions/` (옛 경로는 읽기 전용) | 같은 출처 | https://docs.devin.ai/desktop/devin-desktop-faq.md |
| 실행 파일 | `Devin.app` / `Devin.exe` / `devin`. 셸 명령 `devin-desktop`(옛 `surf`·`windsurf`는 `~/.codeium/windsurf/bin/`) | 설치 판별에 쓴다 | 같은 출처 |
| Devin 설정(권한) | 사용자 `~/.config/devin/config.json`(Windows `%APPDATA%\devin\config.json`), 프로젝트 `.devin/config.json`(커밋용), `.devin/config.local.json`(git 제외), 관리자 정책 `system.json`(경로 **미확인**) | 프로젝트 파일이 권한을 들고 온다 | https://docs.devin.ai/cli/reference/configuration/config-file.md |

### 3.2 위험한 자동 실행 설정

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 권한 규칙 | `permissions.allow` / `deny` / `ask` (사용자·프로젝트 모두). 규칙 `Exec(git)`, `Read(**)`, `Write(**/.env*)`. 거부가 최우선 | 프로젝트 `.devin/config.json`에 `Exec(...)` 허용이 넓게 들어올 수 있다 | https://docs.devin.ai/cli/reference/configuration/config-file.md , https://docs.devin.ai/desktop/terminal |
| 세션 모드 | `permission_mode`(사용자 전용): `"normal"`(기본) / `"accept-edits"` / `"smart"` / `"dangerous"`. Desktop UI 이름: Code / Smart(빠른 모델이 안전하다 판단하면 자동 승인) / Bypass Permissions(조직 정책이 요구하지 않으면 묻지 않음) | `dangerous`·Bypass Permissions가 위험 | 같은 출처 |
| 원격 도구 우회 | `local_tools_bypass_permissions: true`(사용자 전용) | 모든 Local Hands 연결이 우회 상태로 시작. `deny`·`ask`는 여전히 적용 | https://docs.devin.ai/cli/reference/configuration/config-file.md |
| 다른 도구 설정 가져오기 | `read_config_from`: `agents_standard`, `cursor`, `windsurf`, `claude`, `copilot`, `codex`, `kiro`, `opencode`, `zed`, `cloud` 모두 기본 `true` | 다른 도구의 규칙·MCP가 기본으로 섞여 들어온다. 점검기는 출처 파일도 함께 봐야 한다 | 같은 출처 |
| (옛 Windsurf) 자동 실행 단계 | Disabled / Allowlist Only / Auto / Turbo(거부 목록 외 전부 자동). 설정 `windsurf.cascadeCommandsAllowList`, `windsurf.cascadeCommandsDenyList`. 팀 관리자가 최고 단계를 제한 | 현재 문서에서는 사라졌고 검색 결과 요약에서만 확인 → **문서 간 불일치**. 업데이트 안 한 PC에는 남아 있을 수 있다 | (검색 요약, 원문 현재 리디렉트) https://docs.windsurf.com/windsurf/terminal |

### 3.3 MCP

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 옛 Windsurf 경로 | `~/.codeium/windsurf/mcp_config.json` (이름 변경 뒤에도 유지) | 전역 MCP | https://docs.devin.ai/desktop/devin-desktop-faq.md , https://code.visualstudio.com/docs/agents/reference/mcp-configuration |
| 새 경로 | 프로젝트 `.devin/mcp_config.json`(커밋), `.devin/mcp_config.local.json`(git 제외), 사용자 `~/.config/devin/mcp_config.json` | 저장소가 MCP 서버를 들고 온다 | https://docs.devin.ai/desktop/cascade/mcp , https://docs.devin.ai/cli/reference/configuration/config-file.md |
| 구조 | `mcpServers.<이름>`: 로컬 `command`, `args`, `env` / 원격 `url`, `transport`(`"http"` 등). `headers` 필드는 문서에 없음 → **미확인** | `env` 평문 비밀값 | https://docs.devin.ai/cli/reference/configuration/config-file.md |
| 도구 승인 | 기본은 MCP 도구 호출 전마다 확인. 관리자가 신뢰 통합을 기본 허용할 수 있음 | 개별 자동 승인 키 이름 **미확인** | https://docs.devin.ai/desktop/cascade/mcp |

### 3.4 규칙·지시 파일

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 새 규칙 | `.devin/rules/*.md`, `.devin/global_rules.md`, 사용자 `~/.devin/global_rules.md`, `~/.devin/rules/*.md`. 머리말 `trigger`: `always_on`/`glob`/`model_decision`/`manual` | `always_on` 규칙 | https://docs.devin.ai/desktop/cascade/memories |
| 옛 규칙(기본으로 가져옴) | `.windsurf/rules/*.md`, `.windsurf/global_rules.md`, `.windsurfrules` | 이름이 바뀐 뒤에도 계속 읽힌다 | 같은 출처, https://docs.devin.ai/desktop/devin-desktop-faq.md |
| AGENTS 계열 | `AGENTS.md`, `AGENTS.local.md`, `AGENT.md` — 루트와 작업 폴더까지의 각 상위 폴더 | 하위 폴더에 숨은 지시 | https://docs.devin.ai/desktop/cascade/memories |
| `~/.codeium/windsurf/memories/global_rules.md` | 현재 문서에 없음 → **미확인** | — | — |

### 3.5 기업 정책

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 조직 규칙 | Teams·Enterprise 관리자가 Allow/Ask/Deny 규칙 강제, 샌드박스 강제, 선택 가능 모드 제한. 조직 Deny·Ask는 개인 규칙과 Bypass Permissions보다 우선 | 서버 쪽 설정 | https://docs.devin.ai/desktop/terminal |
| 장치 정책 파일 | `system.json`(관리자 관리). OS별 경로 **미확인** | — | https://docs.devin.ai/cli/reference/configuration/config-file.md |
| MCP 레지스트리 | 팀 설정 MCP & ACP > MCP registry(허용 목록 + 레지스트리 항목) | 서버 쪽 | https://docs.devin.ai/desktop/cascade/mcp |

---

## 4. Cline (VS Code 확장 `saoudrizwan.claude-dev`, CLI·SDK 공용)

### 4.1 설정 파일 위치

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 새 공용 경로 | `~/.cline/data/settings/` 아래 `providers.json`(API 키·공급자), `global-settings.json`, `cline_mcp_settings.json`. 환경 변수 `CLINE_DIR`(=`--config`), `CLINE_DATA_DIR`로 바뀜. MCP 파일만 `CLINE_MCP_SETTINGS_PATH`로도 바뀜 | `providers.json`에 API 키가 평문으로 있을 수 있다(문서: "API keys and provider configuration") | https://github.com/cline/cline/blob/main/docs/getting-started/config.mdx , https://docs.cline.bot/mcp/adding-and-configuring-servers.md |
| 옛 MCP 경로(이전 대상) | `<VS Code globalStorage>/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`, `~/Documents/Cline/MCP/cline_mcp_settings.json` | 이전이 끝나도 파일이 남아 있을 수 있다 | (소스) https://github.com/cline/cline/blob/main/apps/vscode/src/hosts/vscode/mcp-settings-legacy-migration.ts |
| 자동 승인 상태 | 키 `autoApprovalSettings`. 예전에는 VS Code globalState, 지금은 파일 기반 globalState로 옮김. 정확한 파일명은 **미확인**(CLI 테스트 자료에 `data/globalState.json`이 있음) | — | (소스) https://github.com/cline/cline/blob/main/apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts |
| 프로젝트 설정 | `.cline/` (rules, workflows, skills, hooks, agents, plugins), 옛 `.clinerules/` | 저장소가 훅·플러그인(코드)을 들고 온다. 문서: "Hooks and plugins can execute code." | https://github.com/cline/cline/blob/main/docs/getting-started/config.mdx |

### 4.2 위험한 자동 승인

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| UI 항목 | Read project files / Read all files / Edit project files / Edit all files / Execute safe commands / Execute all commands / Use the browser / Use MCP servers / Enable notifications | "safe" 판정은 고정 목록이 아니라 **모델이** `requires_approval` 플래그로 정한다. 인젝션으로 모델을 속이면 위험 명령도 "안전"으로 표시될 수 있다(해석) | https://docs.cline.bot/features/auto-approve.md |
| 저장 키 | `autoApprovalSettings.actions.readFiles`, `readFilesExternally`, `editFiles`, `editFilesExternally`, `executeSafeCommands`, `executeAllCommands`, `useBrowser`, `useMcp` | — | (소스) https://github.com/cline/cline/blob/main/apps/vscode/src/shared/AutoApprovalSettings.ts |
| 소스상 기본값 | `readFiles: true, readFilesExternally: true, editFiles: true, editFilesExternally: true, executeSafeCommands: false, executeAllCommands: true, useBrowser: true, useMcp: true` (v4.1.27 main 기준) | 문서는 "Read project files만 켜고 나머지는 꺼 두라"고 권하는데 소스 기본값은 편집·브라우저·MCP가 켜져 있다 → **문서와 소스 엇갈림**. `executeAllCommands`는 `executeSafeCommands`가 켜져야 의미가 있다 | (소스) 같은 파일, https://docs.cline.bot/features/auto-approve.md |
| YOLO 모드 | Settings → Features → "YOLO Mode". 파일 변경·명령·브라우저·MCP·모드 전환을 모두 자동 승인, 확인창 없음. 옛 토글 키 `yoloModeToggled`, `autoApproveAllToggled`는 새 버전에서 `autoApprovalSettings` 전체 켜기로 바뀌어 들어간다 | "dangerous", 모든 안전 점검 해제(문서 경고) | https://docs.cline.bot/features/auto-approve.md , (소스) https://github.com/cline/cline/blob/main/apps/vscode/src/hosts/vscode/vscode-to-file-migration.ts |
| CLI | `--yolo` / `-y` | 셸 별칭·스크립트에 박혀 있으면 위험 | (검색 요약) https://docs.cline.bot/features/yolo-mode |

### 4.3 MCP

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 구조 | `mcpServers.<이름>`: 로컬 `command`, `args`, `env`, `disabled`, `autoApprove: []` / 원격 `type`(`"streamableHttp"` 또는 `"sse"`, 생략 시 `sse`), `url`, `headers`, `disabled`, `autoApprove` | `headers`의 `Authorization: Bearer ...` 평문 | https://docs.cline.bot/mcp/adding-and-configuring-servers.md |
| 도구 자동 승인 | `autoApprove`(새 문서) / `alwaysAllow`(옛 문서·옛 파일) 배열 | 두 키 이름을 모두 봐야 한다 | 같은 출처, (검색 요약) https://docs.cline.bot/mcp/configuring-mcp-servers |

### 4.4 규칙·지시 파일

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 프로젝트 | `.clinerules/`, `.cline/rules/` (둘 다), 루트 `AGENTS.md` | 저장소 지시가 자동 주입 | https://docs.cline.bot/features/cline-rules.md |
| 다른 도구 파일 | `.cursorrules`, `.windsurfrules`도 읽는다 | 다른 도구용 파일이 Cline에도 들어간다 | 같은 출처 |
| 전역 | `~/Documents/Cline/Rules`, `~/.cline/rules`, `~/Cline/Rules`, `~/.agents/AGENTS.md`, Windows OneDrive 아래 `Documents\Cline\Rules` | 전 프로젝트 | 같은 출처, https://github.com/cline/cline/blob/main/docs/getting-started/config.mdx |
| 조건부 | 머리말 `paths`(글롭 배열) | — | https://docs.cline.bot/features/cline-rules.md |
| 훅·플러그인 | `.cline/hooks/`, `.clinerules/hooks/`, `~/.cline/hooks/`, `~/Documents/Cline/Hooks/`, 플러그인 `.js`·`.ts`, `CLINE_HOOKS_DIR` | 코드 실행 경로 | https://github.com/cline/cline/blob/main/docs/getting-started/config.mdx |

### 4.5 기업 정책

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| YOLO 금지 | 원격 설정 JSON의 `yoloModeAllowed: false` (인증 뒤 기업 설정 서버에서 내려받음) | 장치 파일 경로는 **미확인**. 다른 통제 항목 목록도 문서에서 **미확인** | https://docs.cline.bot/enterprise-solutions/configuration/infrastructure-configuration/control-other-cline-features/yolo-mode.md |

---

## 5. Roo Code (VS Code 확장 `RooVeterinaryInc.roo-cline`) — 개발 중단

저장소가 보관 처리됐다(마지막 push 2026-05-15). 아래 항목은 마지막 버전(3.53.0) 기준이다. 설치돼 있다는 것 자체가 점검 항목이다.

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 프로젝트 상태 | `archived: true`, `pushed_at: 2026-05-15` | 앞으로 보안 수정 없음 | https://github.com/RooCodeInc/Roo-Code |
| VS Code 설정 | `roo-cline.allowedCommands` 기본 `["git log", "git diff", "git show"]`, `roo-cline.deniedCommands` 기본 `[]`, `roo-cline.useAgentRules` 기본 `true`, `roo-cline.customStoragePath`(저장 위치 변경) | 허용 목록에 `*`·`bash`·`python` 같은 넓은 접두어 | (소스) https://github.com/RooCodeInc/Roo-Code/blob/main/src/package.json , https://roocodeinc.github.io/Roo-Code/features/auto-approving-actions |
| 자동 승인 키 | `autoApprovalEnabled`, `alwaysAllowReadOnly`, `alwaysAllowReadOnlyOutsideWorkspace`, `alwaysAllowWrite`, `alwaysAllowWriteOutsideWorkspace`, `alwaysAllowWriteProtected`, `alwaysAllowExecute`, `alwaysAllowMcp`, `alwaysAllowModeSwitch`, `alwaysAllowSubtasks`, `alwaysAllowFollowupQuestions`, `allowedMaxRequests` | 확장 전역 상태(VS Code globalState)에 저장되는 것으로 보이나 파일 위치 **미확인** → 정적 점검 어려움 | (소스) https://github.com/RooCodeInc/Roo-Code/blob/main/packages/types/src/global-settings.ts |
| 보호 파일 | `.roo/`, `.rooignore` — "Include protected files"(`alwaysAllowWriteProtected`)를 켜야 수정 가능 | 이걸 켜면 에이전트가 자기 규칙·MCP 설정을 고칠 수 있다(해석) | https://roocodeinc.github.io/Roo-Code/features/auto-approving-actions |
| 경고 | "Auto-approve settings bypass confirmation prompts, giving Roo direct access to your system." | 문서 경고 | 같은 출처 |
| 전역 MCP | `<globalStorage 또는 customStoragePath>/settings/mcp_settings.json` | — | (소스) https://github.com/RooCodeInc/Roo-Code/blob/main/src/shared/globalFileNames.ts , https://github.com/RooCodeInc/Roo-Code/blob/main/src/utils/storage.ts |
| 프로젝트 MCP | `<프로젝트>/.roo/mcp.json` — 같은 이름이면 프로젝트가 이긴다 | 저장소가 전역 서버를 같은 이름으로 바꿔치기할 수 있다(해석) | https://roocodeinc.github.io/Roo-Code/features/mcp/using-mcp-in-roo |
| MCP 구조 | stdio: `command`, `args`, `cwd`, `env`, `alwaysAllow`, `disabled`, `timeout`, `watchPaths`, `disabledTools`. HTTP: `type: "streamable-http"`, `url`, `headers`, … SSE: `type: "sse"` | `alwaysAllow`는 전역 "Use MCP servers" 자동 승인이 켜져 있을 때 그 도구를 묻지 않고 실행 | 같은 출처 |
| 규칙 | 전역 `~/.roo/rules/`, `~/.roo/rules-{modeSlug}/`. 작업 공간 `.roo/rules/`, `.roo/rules-{modeSlug}/`, 대체 `.roorules`, `.roorules-{modeSlug}`, 옛 `.clinerules`, `AGENTS.md`(없으면 `AGENT.md`) | 저장소 지시 주입 | https://roocodeinc.github.io/Roo-Code/features/custom-instructions |
| `.roomodes` | 문서에서 **미확인** | — | — |

---

## 6. Continue (VS Code·JetBrains 확장 + CLI `cn`)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| 전역 설정 | `~/.continue/config.yaml` (환경 변수 `CONTINUE_GLOBAL_DIR`로 변경). `config.json`은 사용 중단 | — | https://docs.continue.dev/reference , (소스) https://github.com/continuedev/continue/blob/main/core/util/paths.ts |
| 실행되는 설정 | `~/.continue/config.ts` (TypeScript 설정), `~/.continue/.continuerc.json` | `config.ts`는 코드다. 내용이 바뀌면 확장이 그 코드를 실행한다(해석, 소스에 경로 확인) | (소스) https://github.com/continuedev/continue/blob/main/core/util/paths.ts |
| 작업 공간 블록 폴더 | `.continue/rules`, `.continue/mcpServers`, `.continue/prompts`, `.continue/models`, `.continue/context`, `.continue/docs`, `.continue/data`, `.continue/assistants` | 저장소가 규칙·MCP를 들고 온다 | (검색 요약) https://docs.continue.dev/reference |
| 다른 도구 MCP 파일 | `.continue/mcpServers/`에 Claude Desktop·Cursor·Cline JSON 설정을 그대로 넣으면 읽는다 | 다른 도구용 파일이 복사돼 있을 수 있다 | (GitHub PR) https://github.com/continuedev/continue/pull/8021 |
| MCP 구조 | `mcpServers[]`: `name`(필수), `command`(필수), `args`, `env`, `cwd`, `requestOptions`(`headers` 포함), `connectionTimeout`. `type`·`url` 키 설명은 이번에 받은 문서에 없음 → **미확인** | `env`·`requestOptions.headers` 평문 비밀값. MCP는 에이전트 모드에서만 돈다 | https://docs.continue.dev/reference |
| 규칙 | `rules:` 블록(`uses:` 허브 슬러그 또는 `file://`), "Rules are concatenated into the system message for all Agent, Chat, and Edit requests." | 원격 허브 규칙도 시스템 메시지에 들어간다 | https://docs.continue.dev/reference |
| IDE 도구 정책 | 도구마다 Ask First(기본) / Automatic / Excluded. Automatic이면 승인 단계를 건너뜀. 읽기 전용이 아닌 도구를 Automatic으로 두지 말라는 경고 | 저장 위치 **미확인** → 정적 점검 어려움 | https://docs.continue.dev/ide-extensions/agent/how-it-works , https://docs.continue.dev/features/agent/how-to-customize |
| CLI 권한 | `~/.continue/permissions.yaml`: `allow`/`ask`/`exclude`, 패턴 `Tool`·`Tool(glob)` 예 `Bash(npm install*)`. 기본: 읽기 도구 `allow`, `Edit`·`MultiEdit`·`Write`·`Bash`는 `ask`. TUI에서 "Continue + don't ask again"을 누르면 파일에 추가됨. `cn --auto`는 전부 허용, 헤드리스 `--allow "*"` | `allow`에 인자 없는 `Bash`나 `*` | https://docs.continue.dev/cli/tool-permissions |

---

## 7. JetBrains AI Assistant · Junie (짧게)

| 항목 | 경로·키·값 | 위험한 이유 | 출처 URL |
|---|---|---|---|
| Junie 지시 파일 | 우선순위: 사용자 지정 경로 → `.junie/AGENTS.md`(있으면 이것만) → 루트 `AGENTS.md`(+ `.junie/playbook.md`, `.junie/rules/*.md`) → 옛 `.junie/guidelines.md`, `.junie/guidelines/` | 저장소 지시 주입. 설정 화면 문서는 기본값을 `.junie/guidelines.md`라고 적어 **문서 간 불일치** | https://junie.jetbrains.com/docs/junie-ide-plugin.html , (검색 요약) https://junie.jetbrains.com/docs/junie-plugin-settings.html |
| Junie MCP | 전역 `~/.junie/mcp/mcp.json`, 프로젝트 `.junie/mcp/mcp.json` | 저장소가 MCP 서버를 들고 온다 | https://junie.jetbrains.com/docs/junie-ide-plugin.html |
| Brave Mode | 작업 창 체크박스. 민감한 동작을 모두 승인 없이 실행. 문서가 권하지 않음 | 저장 위치 **미확인** | 같은 출처 |
| Action Allowlist | Settings \| Tools \| Junie \| Action Allowlist. 터미널은 정확한 명령이나 Java 정규식. MCP 규칙 하나가 **모든 MCP 도구**를 허용(서버·도구 단위 선택 불가). 기본: `ls`·`cd`·`pwd`만 무승인 | MCP 허용 한 줄이 전부 허용. 저장 파일 위치 **미확인** | https://junie.jetbrains.com/docs/action-allowlist.html |
| 접근 제한 파일 | 프로젝트 루트 `.aiignore` | 있으면 안전 쪽 | 같은 출처 |
| AI Assistant MCP | Settings \| Tools \| AI Assistant \| Model Context Protocol (MCP), `mcpServers` JSON(STDIO·Streamable HTTP). 파일 저장 위치 **미확인** | — | https://www.jetbrains.com/help/ai-assistant/configure-an-mcp-server.html |
| AI Assistant 규칙 | `.aiassistant/rules/` | 공식 문서 **미확인 (비공식 출처)** | (비공식) https://docs.bito.ai/ai-architect/integrating-ai-architect-with-your-tools/manual-mcp-integration-with-ai-coding-agents/guide-for-jetbrains-ai-assistant |

---

## 8. 도구끼리 서로 읽는 파일 (교차 주입 지도)

점검기는 한 파일이 여러 도구에 동시에 들어간다는 점을 알아야 한다. 아래는 문서로 확인한 것만 모았다.

| 파일 | 읽는 도구 | 출처 |
|---|---|---|
| `AGENTS.md` | VS Code(Copilot·Codex·Local), Cursor, Devin Desktop, Cline, Roo, Junie | 각 절 출처 |
| `CLAUDE.md` | VS Code, Cursor(무조건 적용) | 1.5, 2.5절 |
| `.cursorrules` | Cursor(레거시), Cline | 2.5, 4.4절 |
| `.windsurfrules`, `.windsurf/rules/` | Devin Desktop, Cline(`.windsurfrules`) | 3.4, 4.4절 |
| `.clinerules` | Cline, Roo(대체) | 4.4, 5절 |
| `~/.cursor/mcp.json`, `.cursor/mcp.json`, `~/.codeium/windsurf/mcp_config.json`, `claude_desktop_config.json` | VS Code(`chat.mcp.discovery.enabled` 켤 때) | 1.3절 |
| 다른 도구 규칙·MCP 전반 | Devin Desktop(`read_config_from` 기본 전부 `true`) | 3.2절 |

---

## 점검 규칙 후보

심각도: **상** = 사람 승인 없이 코드가 돌거나 비밀값이 노출됨, **중** = 공격 표면을 넓힘, **하** = 권장 미적용·정보.

| 규칙ID | 탐지 조건 | 심각도 |
|---|---|---|
| VSC-PERM-001 | 사용자·프로필·작업 공간 settings.json에 `chat.tools.global.autoApprove: true` | 상 |
| VSC-PERM-002 | `chat.tools.terminal.autoApprove`에 범용 실행기(`bash`, `sh`, `zsh`, `pwsh`, `powershell`, `cmd`, `python`, `node`, `npx`) 또는 `".*"`·`"/.*/"`류 정규식이 `true` | 상 |
| VSC-PERM-003 | `chat.tools.terminal.autoApprove`에서 기본 거부 항목(`rm`, `curl`, `wget`, `eval`, `chmod`, `chown`, `kill`, `del`, `rmdir`, `Remove-Item`)을 `true`로 뒤집음 | 상 |
| VSC-PERM-004 | `chat.tools.terminal.ignoreDefaultAutoApproveRules: true` | 중 |
| VSC-PERM-005 | `chat.tools.edits.autoApprove`에 `**`·`**/*` 같은 넓은 글롭이 `true` | 중 |
| VSC-PERM-006 | `chat.tools.urls.autoApprove`에 `*`·`https://*` 같은 넓은 패턴 | 중 |
| VSC-PERM-007 | `chat.defaultConfiguration.approvals`·`chat.permissions.default`가 Allow all·Autopilot·Bypass·Full Access 계열 | 상 |
| VSC-PERM-008 | `chat.tools.terminal.autoReplyToPrompts: true` | 중 |
| VSC-PERM-009 | `chat.agent.maxRequests`가 기본(25)보다 크게 설정되고 자동 승인 키도 켜짐 | 하 |
| VSC-WS-001 | 작업 공간 `.vscode/settings.json`에 `chat.tools.*autoApprove`·`chat.mcp.*`·`chat.*Locations`·`task.allowAutomaticTasks` 같은 AI·실행 관련 키가 들어 있음(저장소가 설정을 들고 옴) | 중 |
| VSC-TRUST-001 | `security.workspace.trust.enabled: false` | 상 |
| VSC-TRUST-002 | `security.workspace.trust.untrustedFiles: "open"` | 하 |
| VSC-TASK-001 | `task.allowAutomaticTasks: "on"` | 중 |
| VSC-TASK-002 | 점검 대상 저장소의 `.vscode/tasks.json`에 `"runOn": "folderOpen"` (VSC-TRUST-001·VSC-TASK-001·CUR-TRUST-001과 겹치면 상으로 올림) | 중 |
| VSC-MCP-001 | `.vscode/mcp.json`·`.mcp.json`(저장소)에 `stdio` 서버 존재 — 명령·인자 목록 보고 | 중 |
| VSC-MCP-002 | 어느 MCP 파일이든 `env`·`headers`에 `${input:...}`·`${env:...}`가 아닌 평문 값이 키·토큰 패턴과 맞음(값은 출력하지 않고 키 이름만 보고) | 상 |
| VSC-MCP-003 | `chat.mcp.discovery.enabled`가 켜져 있음 → 연결된 다른 도구 MCP 파일까지 점검 범위 확장 | 하 |
| VSC-MCP-004 | MCP `sandbox.network.allowedDomains`에 `*` 또는 `filesystem.allowWrite`에 홈 전체 | 중 |
| VSC-INST-001 | 저장소에 `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`(하위 포함), `CLAUDE.md`, `.claude/rules/` 존재 — 목록 보고 + 숨은 지시 의심 패턴(보이지 않는 유니코드 문자, "ignore previous", 셸 명령·URL) 검사 | 중 |
| VSC-INST-002 | 작업 공간 설정이 `chat.instructionsFilesLocations`·`chat.agentFilesLocations` 등에 저장소 밖 경로나 홈 경로를 추가 | 중 |
| VSC-HOOK-001 | `chat.hookFilesLocations`에 항목이 있거나 저장소에 훅 정의 존재(경로 미확인이라 키 존재만 보고) | 중 |
| VSC-EXT-001 | 설치 확장 중 보관·중단 프로젝트(예: `rooveterinaryinc.roo-cline`) | 중 |
| VSC-EXT-002 | 기업 PC인데 `extensions.allowed`·`AllowedExtensions` 정책 없음 | 하 |
| VSC-MGMT-001 | 기업 PC인데 정책 위치(Windows 레지스트리 `Software\Policies\Microsoft\VSCode`, Linux `/etc/vscode/policy.json`, macOS 프로파일)에 `ChatToolsAutoApprove=false`·`ChatMCP`/`ChatAllowedMcpServers` 등이 없음 | 중 |
| CUR-TRUST-001 | Cursor 설치 + Cursor 사용자 settings.json에 `security.workspace.trust.enabled: true`가 명시돼 있지 않음(기본 꺼짐 보고, 비공식) | 상 |
| CUR-PERM-001 | `~/.cursor/cli-config.json`·`.cursor/cli.json`의 `permissions.allow`에 `Shell(*)`, 인자 없는 범용 실행기, `Write(**)`, `Mcp(*:*)`, `WebFetch(*)` | 상 |
| CUR-PERM-002 | 저장소에 `.cursor/permissions.json` 존재(특히 `autoRun.allow_instructions`) — 분류기를 허용 쪽으로 미는 지침 | 중 |
| CUR-SBX-001 | `.cursor/sandbox.json`(저장소)이 네트워크·읽기 범위를 넓힘(`additionalReadPaths`에 홈·`~/.ssh`·`~/.aws` 등) | 중 |
| CUR-MCP-001 | `.cursor/mcp.json`(저장소)에 stdio 서버 존재 | 중 |
| CUR-MCP-002 | Cursor MCP 파일의 `env`·`headers`·`auth.CLIENT_SECRET` 평문 값 | 상 |
| CUR-RULE-001 | 저장소에 `.cursorrules`, `.cursor/rules/*.mdc`(`alwaysApply: true` 또는 `globs: **`), `AGENTS.md`, `CLAUDE.md` — 목록 + 숨은 지시 패턴 검사 | 중 |
| CUR-MGMT-001 | Linux 기업 PC인데 `~/.cursor/policy.json` 없음, 또는 `WorkspaceTrustEnabled` 정책 없음 | 하 |
| DV-PERM-001 | `~/.config/devin/config.json`에 `permission_mode: "dangerous"` 또는 `local_tools_bypass_permissions: true` | 상 |
| DV-PERM-002 | 사용자·프로젝트 `permissions.allow`에 `Exec(*)`·`Write(**)`류 넓은 규칙, 특히 저장소 `.devin/config.json` | 상 |
| DV-PERM-003 | `read_config_from`가 기본값(전부 `true`) 그대로 → 다른 도구 설정까지 점검 범위 확장 | 하 |
| DV-MCP-001 | `.devin/mcp_config.json`(저장소)·`~/.config/devin/mcp_config.json`·`~/.codeium/windsurf/mcp_config.json`에 stdio 서버·평문 `env` | 중(평문 비밀값이면 상) |
| DV-LEGACY-001 | 옛 Windsurf 설정에 `windsurf.cascadeCommandsAllowList`가 넓거나 Turbo 단계 흔적(현재 문서 미확인이라 존재만 보고) | 중 |
| DV-RULE-001 | 저장소에 `.devin/rules/`, `.devin/global_rules.md`, `.windsurf/rules/`, `.windsurfrules`, `AGENTS.local.md` 존재 | 중 |
| CL-PERM-001 | Cline `autoApprovalSettings.actions.executeSafeCommands`와 `executeAllCommands`가 둘 다 `true`(모든 명령 자동 실행) | 상 |
| CL-PERM-002 | 옛 키 `yoloModeToggled`/`autoApproveAllToggled`가 `true`이거나 `autoApprovalSettings.actions` 전 항목이 `true` | 상 |
| CL-PERM-003 | `editFilesExternally: true` 또는 `readFilesExternally: true`(작업 공간 밖 접근) | 중 |
| CL-MCP-001 | `cline_mcp_settings.json`(새 경로·옛 globalStorage·`~/Documents/Cline/MCP`)의 서버에 `autoApprove`/`alwaysAllow` 배열이 비어 있지 않음 — 도구 이름 보고 | 중 |
| CL-MCP-002 | 같은 파일의 `env`·`headers` 평문 비밀값 | 상 |
| CL-SEC-001 | `~/.cline/data/settings/providers.json` 존재 + 파일 권한이 넓음(내용은 읽지 않음) | 중 |
| CL-HOOK-001 | 저장소에 `.cline/hooks/`, `.clinerules/hooks/`, `.cline/plugins/` 존재(코드 실행) | 상 |
| CL-RULE-001 | 저장소에 `.clinerules/`, `.cline/rules/`, `.cursorrules`, `.windsurfrules`, `AGENTS.md` 존재 | 중 |
| ROO-EXT-001 | Roo Code 확장 설치됨(보관된 프로젝트, 보안 수정 없음) | 중 |
| ROO-PERM-001 | `roo-cline.allowedCommands`에 `*` 또는 범용 실행기 접두어 | 상 |
| ROO-MCP-001 | `.roo/mcp.json`(저장소) 존재, 특히 전역 `mcp_settings.json`과 같은 서버 이름(바꿔치기) | 중 |
| ROO-MCP-002 | Roo MCP 서버에 `alwaysAllow` 비어 있지 않음 | 중 |
| ROO-RULE-001 | 저장소에 `.roo/rules*/`, `.roorules*`, `.clinerules`, `AGENTS.md`/`AGENT.md` | 중 |
| CN-PERM-001 | `~/.continue/permissions.yaml`의 `allow`에 인자 없는 `Bash`, `Write`, `*` | 상 |
| CN-CODE-001 | `~/.continue/config.ts` 존재(코드로 된 설정) — 수정 시각·소유자 보고 | 하 |
| CN-MCP-001 | 저장소 `.continue/mcpServers/` 존재 또는 `config.yaml`의 `mcpServers` 평문 `env`·`headers` | 중(평문 비밀값이면 상) |
| CN-RULE-001 | 저장소 `.continue/rules/` 존재 | 중 |
| JB-PERM-001 | Junie Action Allowlist에 MCP 규칙(=모든 MCP 도구 허용) — 저장 위치 미확인이라 확인되면 활성화 | 중 |
| JB-MCP-001 | `.junie/mcp/mcp.json`(저장소)·`~/.junie/mcp/mcp.json` stdio 서버·평문 `env` | 중(평문 비밀값이면 상) |
| JB-RULE-001 | 저장소에 `.junie/AGENTS.md`, `.junie/guidelines.md`, `.junie/guidelines/`, `.junie/rules/`, `.junie/playbook.md` | 중 |
| ALL-RULE-001 | 위 모든 지시 파일에 대해 공통 검사: 보이지 않는 유니코드(U+200B–U+200F, U+E0000 태그 문자 등), base64 덩어리, 외부 URL, 셸 명령 문자열, "이전 지시 무시"류 문구 | 중 |
| ALL-CROSS-001 | 하나의 저장소에 서로 다른 도구용 지시 파일이 3종 이상(교차 주입 표면) — 정보 | 하 |
| ALL-MCP-001 | 여러 도구 MCP 파일에서 같은 서버 이름이 다른 `command`/`url`을 가리킴 | 중 |

---

## 확인하지 못한 것과 문서끼리 엇갈린 것 (요약)

- **Cursor**: 사용자 settings.json·확장 폴더 경로, 실행 모드·보호 기능이 저장되는 파일, Windows 정책 레지스트리 키 — 공식 문서 미확인. 작업 공간 신뢰 기본값 꺼짐은 보안 업체(Oasis) 보고뿐.
- **Windsurf → Devin Desktop**: 옛 자동 실행 단계(Turbo 등)와 `windsurf.cascadeCommandsAllowList/DenyList`는 현재 문서에서 사라졌다. `~/.codeium/windsurf/memories/global_rules.md` 미확인. Windows·Linux 사용자 데이터 경로, `system.json` 경로 미확인.
- **Cline**: 문서는 "읽기만 켜라"고 권하는데 소스 기본값은 편집·브라우저·MCP가 켜져 있다. MCP 자동 승인 키 이름이 `alwaysAllow`(옛)와 `autoApprove`(새)로 갈린다. 자동 승인 상태 파일 이름 미확인.
- **Roo Code**: 프로젝트 보관됨. 자동 승인 상태 저장 파일 미확인. `.roomodes` 미확인.
- **Continue**: IDE 도구 정책 저장 위치, `mcpServers`의 `type`·`url` 키 미확인.
- **VS Code**: `chat.tools.edits.autoApprove` 기본 보호 파일 목록, 신뢰 폴더 저장 위치, 훅 파일 경로, macOS 정책 도메인, Copilot 관리 설정의 장치 내 파일 경로, `/yolo` 명령의 본문 근거 미확인. 작업 공간 신뢰 정책은 VS Code 정책 표에 없다(Cursor에는 있다).
- **Junie**: 지시 파일 기본 위치를 두 문서가 다르게 적었다(`.junie/AGENTS.md` 우선 vs `.junie/guidelines.md` 기본). Brave Mode·Allowlist 저장 위치 미확인.
