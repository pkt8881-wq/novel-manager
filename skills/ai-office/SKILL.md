---
name: AI Office
slug: ai-office
version: 1.1.0
description: 매니저(Claude/코난)가 로컬 AI 직원들(안다·미로·ComfyUI)에게 작업을 위임하여 Claude API 토큰 사용을 최소화하면서 협업으로 결과물을 만드는 스킬
metadata: {"clawdbot":{"emoji":"🏢","requires":{"bins":[]},"os":["win32"]}}
---

# AI Office — 로컬 AI 팀 협업 스킬

## 자동 트리거 조건

아래 상황 중 하나라도 해당되면 이 스킬을 **자동으로 활성화**한다:

- 사용자가 "안다", "미로", "ComfyUI", "이미지 생성", "팀", "직원" 중 하나라도 언급할 때
- "안다한테 시켜", "미로한테 맡겨", "이미지 뽑아줘", "팀으로 만들어줘" 같은 위임 표현
- "로컬 AI로", "토큰 아끼면서", "협업해서 만들어줘" 같은 표현
- "사용량 줄여서", "로컬로만" 처리 요청
- 이미지가 필요한 웹사이트/대시보드/홈페이지 작업 요청

**DO NOT TRIGGER**: 사용자가 Claude 혼자 처리하길 원할 때, 단순 질문·설명 요청일 때

## 팀 구조

```
사용자 → 코난(Claude, 매니저)
              ├─ 🤖 안다  (파일·코드·PC 제어)     localhost:18789  OpenClaw
              ├─ 🤖 미로  (검색·조사·뉴스)         localhost:8001   HTTP API
              └─ 🎨 ComfyUI (이미지 생성 외주)     localhost:8188   D:\AI\ComfyUI
```

**원칙**: 코난은 설계·판단·검수만. 무거운 작업은 로컬 AI에 위임 → 토큰 절약

---

## 사용법

```
/ai-office [작업 설명]
```

예시:
- `/ai-office 바이브 코딩 — 게임 런처에 정렬 기능 추가`
- `/ai-office 이미지 배경 — 사이버펑크 도시 느낌으로 웹 배경 생성`
- `/ai-office 조사 — 최신 Python 웹소켓 라이브러리 트렌드`
- `/ai-office 팀확인` — 전체 에이전트 상태 점검

---

## 직원별 역할 & 배정 기준

### 🤖 안다에게 시킬 것
- 파일/폴더 생성·수정·삭제
- 코드 파일 작성 (보일러플레이트, 반복 구조)
- 패키지 설치 (`pip install`, `npm install`)
- 테스트 실행, 빌드
- 시스템 정보 수집

**MCP 도구**: `delegate_to_anda(task)`

### 🤖 미로에게 시킬 것
- 웹 검색, 트렌드 조사
- 라이브러리·API 사례 수집
- 뉴스·정보 수집
- 참고 자료 리스트업

**MCP 도구**: `delegate_to_miro(task)`

### 🎨 ComfyUI에게 시킬 것
- 웹사이트 배경 이미지
- 썸네일, 배너, 일러스트
- UI 목업용 이미지

**MCP 도구**: `generate_image_tool(prompt, style, width, height)`

### 🧠 코난(Claude)이 직접 할 것
- 전체 설계·아키텍처 결정
- 핵심 비즈니스 로직 코딩
- 직원 결과물 검수·통합
- 복잡한 디버깅·판단

---

## 표준 워크플로우

```
1. 코난: 작업 분석 → 태스크 분해 → 담당자 배정
2. 미로: 사전 조사 (필요 시)
3. 안다: 환경 세팅 (폴더/파일 생성, 패키지 설치)
4. ComfyUI: 이미지 생성 (필요 시)
5. 코난: 핵심 로직 개발
6. 안다: 테스트 실행
7. 코난: 최종 검수 & 사용자 보고
```

---

## 에이전트 상태 확인

작업 전 항상 상태 확인:
```
check_all_agents()
```

- 안다 오프라인 → `C:\Users\USER\AppData\Roaming\npm\openclaw.cmd` 재실행
- 미로 오프라인 → `C:\Users\USER\ai-company\start_company.bat` 실행
- ComfyUI 오프라인 → `D:\AI\ComfyUI` 에서 실행 파일 구동

---

## 작업 디렉토리

- 기본 작업 폴더: `C:\Users\USER\ai-company`
- 이미지 저장: `C:\Users\USER\ai-company\images\`
- 프로젝트별 폴더를 ai-company 하위에 생성

---

## 토큰 절약 원칙

| 작업 유형 | 담당 | 이유 |
|-----------|------|------|
| 파일 대량 생성 | 안다 | 반복 작업, 코난 불필요 |
| 웹 검색/조사 | 미로 | 로컬 처리 가능 |
| 이미지 생성 | ComfyUI | 완전 로컬, 토큰 0 |
| 보일러플레이트 코드 | 안다 | 패턴 반복 |
| 핵심 설계·로직 | 코난 | 판단력 필요 |

**목표**: 코난의 직접 작업 비율 ≤ 30%, 로컬 AI 위임 ≥ 70%

---

## 운영 지침 참고

- 전체 상세 지침: `C:\Users\USER\ai-company\CLAUDE.md`
- 포트 현황: `~/.claude/projects/C--Users-USER/memory/reference_ports.md`
- 미로 명령 전 포트 8001 확인 필수
