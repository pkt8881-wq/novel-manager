---
name: Novel Manager
slug: novel-manager
version: 1.0.0
description: 소설 관리 프로그램 — 별점수집/대시보드/TTS리더/GPU모니터링 관련 작업 시 자동 활성화. 경로·DB구조·포트·워크플로우를 모두 포함.
metadata: {"clawdbot":{"emoji":"📚","requires":{"bins":[]},"os":["win32"]}}
---

# Novel Manager 스킬

## 자동 트리거 조건

아래 상황 중 하나라도 해당되면 자동 활성화:

- "소설", "소설 관리", "소설 서버", "TTS", "소설 별점" 언급 시
- "소설 대시보드", "소설 리더", "소설 수집" 관련 작업 요청 시
- GPU 모니터링, 소설 작업 자동화 관련 요청 시

---

## 핵심 경로

| 항목 | 경로 |
|------|------|
| 소설 폴더 | `C:\Users\USER\소설\` |
| 소설 파일들 | `C:\Users\USER\소설\소설_정렬됨\가~하\기타\` |
| DB | `C:\Users\USER\소설\novels.db` |
| 웹 서버 | `C:\Users\USER\소설\novel_server.py` |
| 별점 수집 (전체) | `C:\Users\USER\소설\novel_rater_full.py` |
| 별점 수집 (테스트) | `C:\Users\USER\소설\novel_rater_test.py` |
| GPU 모니터 | `C:\Users\USER\소설\gpu_monitor.py` |
| PC 실행 | `C:\Users\USER\소설\start_novels.bat` |
| 출근전 자동실행 | `C:\Users\USER\소설\출근전_실행.bat` |
| 폰 설치 | `C:\Users\USER\소설\termux_setup.sh` |
| 폰 실행 | `C:\Users\USER\소설\start_phone.sh` |

---

## DB 구조 (novels 테이블)

```sql
id               INTEGER PRIMARY KEY
title            TEXT           -- 원본 파일명(제목)
title_normalized TEXT           -- 정규화 제목 (검색용)
folder           TEXT           -- 가/나/다.../기타
filepath         TEXT UNIQUE    -- 실제 파일 경로
file_hash        TEXT
genre            TEXT           -- 무협/게임/퓨전/현대판타지/판타지/로맨스/BL/기타
rating           REAL           -- 10점 만점
synopsis         TEXT           -- 2~3줄 줄거리
source           TEXT           -- 웹검색(사이트명)
rated_at         TIMESTAMP
bookmark_para    INTEGER        -- 북마크 단락 인덱스
bookmark_page    INTEGER        -- 북마크 페이지
added_at         TIMESTAMP
```

---

## 포트

| 서비스 | 포트 |
|--------|------|
| 소설 웹 서버 | **8902** |
| 미로 (별점 검색) | 8001 |

---

## 웹 서버 API

| 엔드포인트 | 설명 |
|------------|------|
| `GET /` | 대시보드 (랭킹/검색/장르필터) |
| `GET /read/<id>` | TTS 리더 |
| `GET /api/novels` | 소설 목록 (genre/sort/q/page 파라미터) |
| `GET /api/novel/<id>/content` | 소설 본문 (page/psize 파라미터) |
| `POST /api/bookmark` | 북마크 저장 |
| `GET /api/bookmark/<id>` | 북마크 조회 |
| `GET /api/genres` | 장르별 통계 |

---

## 별점 수집 워크플로우

```
1. 제목 정제 — 장르태그/화수/완결표시/저자명 제거
2. 미로(localhost:8001)에 웹검색 요청
3. 문피아/조아라/리디/네이버시리즈에서 별점+장르+줄거리 수집
4. 10점 만점 기준으로 저장 (5점 만점이면 ×2 환산)
5. 미발견 시 genre만 태그에서 추출해 저장
6. 중단 재시작 시 rated_at IS NOT NULL 인 것 건너뜀
```

---

## GPU 모니터링 기준

| 온도 | 동작 |
|------|------|
| ~74°C | 정상 진행 |
| 75°C 이상 | 수집 일시정지 + 텔레그램 알림 |
| 65°C 이하 | 수집 자동 재개 + 텔레그램 알림 |
| 체크 간격 | 30초 |

---

## TTS 리더 기능

- 재생/정지/이전/다음 문단
- 속도: 1.0× / 1.2× / 1.3× / 1.5×
- 북마크 저장 (이어읽기)
- 슬라이드 잠금화면 (실수 터치 방지)
- Wake Lock (화면 꺼짐 방지)
- 무음 오디오 루프 (백그라운드 TTS 유지)

---

## 폰 실행 (Termux)

```bash
# 최초 1회
cd /sdcard/소설 && bash termux_setup.sh

# 매번 실행
bash /sdcard/소설/start_phone.sh
# 크롬에서 localhost:8902 접속
```

---

## 텔레그램 알림

- 봇 토큰: `C:\Users\USER\.claude\channels\telegram\.env`
- 채팅 ID: `1313635210`
- 알림 시점: 수집 시작 / GPU 경고 / GPU 재개 / 수집 완료 / PC 종료 카운트다운

---

## 소설 현황 (2026-04-04 기준)

- 총 소설: 5,622편 (txt, 가~하/기타 폴더 정렬)
- 별점 수집: 진행 중 (미로 웹검색 방식)
- 평균 처리 속도: 18초/편 (3개 병렬)
