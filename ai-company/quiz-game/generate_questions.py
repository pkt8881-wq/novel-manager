"""
미로(Miro)에게 퀴즈 문제 대량 생성을 위임하는 스크립트.
각 카테고리별로 미로가 웹검색 + Gemini로 문제를 생성해 JSON에 추가.
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from clients.miro_client import ask_miro

Q_DIR = os.path.join(os.path.dirname(__file__), 'questions')

TOPICS = {
    'ai_tools': {
        'name': 'AI 도구 (Claude Code, Cursor, MCP, GitHub Copilot, Windsurf)',
        'subtopics': [
            'Claude Code 슬래시명령어, hooks, CLAUDE.md, 서브에이전트, 권한설정',
            'Cursor IDE 기능, Agent모드, Context, .cursorrules',
            'MCP(Model Context Protocol) 서버, Resource, Tool, Prompt',
            'GitHub Copilot, Windsurf Cascade, Aider, Continue.dev 비교',
            'AI 코딩 도구 활용 팁, 프롬프트 엔지니어링, 시스템 프롬프트',
        ]
    },
    'agents': {
        'name': 'AI 에이전트 (LangChain, CrewAI, MCP, RAG, Tool Use)',
        'subtopics': [
            'Tool Use 작동방식, Function Calling, JSON 스키마 정의',
            'RAG 파이프라인, 벡터 임베딩, ChromaDB, FAISS, 청킹 전략',
            'LangChain LCEL, RunnableSequence, PromptTemplate, Memory',
            'CrewAI Agent/Task/Crew 구조, 역할분담, 다중에이전트 협업',
            'ReAct 패턴, Chain-of-Thought, 프롬프트 인젝션 방어',
            'AutoGen, LangGraph, 에이전트 상태관리, 오류복구 전략',
        ]
    },
    'local_llm': {
        'name': '로컬 LLM (Ollama, GGUF, llama.cpp, LM Studio)',
        'subtopics': [
            'Ollama 명령어, 모델 관리, API 엔드포인트, Modelfile',
            'GGUF 양자화 레벨(Q2~Q8), K방식, 품질vs메모리 트레이드오프',
            'llama.cpp, llamafile, koboldcpp 차이와 활용',
            'LM Studio, Jan, Open WebUI 비교 및 활용',
            '모델 선택 기준 (파라미터 크기, VRAM, 용도별 추천)',
            '로컬 LLM API 서버, OpenAI 호환 엔드포인트, LiteLLM 연동',
        ]
    },
    'python': {
        'name': '파이썬 프로그래밍',
        'subtopics': [
            '기본 문법: 타입힌트, f-string, 구조적 패턴매칭(match-case)',
            '함수: *args, **kwargs, 데코레이터, 클로저, 람다',
            '클래스: @dataclass, __slots__, 프로퍼티, 추상클래스',
            '비동기: async/await, asyncio, aiohttp, 이벤트루프',
            '파일/경로: pathlib, json, csv, pickle, 컨텍스트매니저',
            '성능: GIL, multiprocessing, generator, itertools, lru_cache',
            '패키지 관리: pip, venv, uv, pyproject.toml, requirements.txt',
        ]
    },
    'server': {
        'name': '서버 만들기 (Flask, FastAPI, REST API, 배포)',
        'subtopics': [
            'Flask 라우팅, Blueprint, request/response, Jinja2 템플릿',
            'FastAPI 경로 파라미터, Pydantic 모델, 의존성 주입, 미들웨어',
            'REST API 설계: HTTP 메서드, 상태코드, URL 설계 원칙',
            '인증/보안: JWT, OAuth2, CORS, API 키, 세션',
            'WSGI vs ASGI, uvicorn, gunicorn, 배포 설정',
            'WebSocket, SSE(Server-Sent Events), 실시간 통신',
            'Docker 기본, 컨테이너화, 환경변수 관리, .env',
        ]
    },
    'database': {
        'name': '데이터베이스 (SQLite, PostgreSQL, SQL, ORM)',
        'subtopics': [
            'SQL 기초: SELECT, WHERE, ORDER BY, GROUP BY, HAVING',
            'SQL 중급: JOIN(INNER/LEFT/RIGHT), 서브쿼리, WITH(CTE)',
            'DDL: CREATE TABLE, PRIMARY KEY, FOREIGN KEY, INDEX, UNIQUE',
            'SQLite 특징, sqlite3 모듈, WAL 모드, VACUUM',
            'SQLAlchemy ORM: 모델 정의, 세션, 관계(relationship), 쿼리',
            'N+1 문제, eager loading, 인덱스 최적화, EXPLAIN',
            '트랜잭션, ACID, 격리 수준, commit/rollback',
        ]
    },
    'history': {
        'name': '한국사 및 세계사',
        'subtopics': [
            '한국 고대사: 삼국시대, 고려, 조선 주요 사건',
            '한국 근현대사: 일제강점기, 독립운동, 6.25, 경제발전',
            '세계사: 르네상스, 산업혁명, 세계대전, 냉전',
            '동양사: 중국 왕조, 일본 역사, 실크로드',
            '역사 인물: 세종대왕, 이순신, 나폴레옹, 링컨 등',
        ]
    },
    'common': {
        'name': '상식 (과학, 수학, 지리, 경제)',
        'subtopics': [
            '기초 과학: 물리(상대성이론, 양자역학 개념), 화학 원소',
            '생물: DNA, 진화론, 세포, 인체 기관',
            '수학 개념: 집합, 확률, 통계 기초, 알고리즘 복잡도',
            '지리: 세계 수도, 지형, 기후, 인구',
            '경제: GDP, 인플레이션, 금리, 주식 기초 개념',
        ]
    },
}

PROMPT_TEMPLATE = """
당신은 교육용 퀴즈 문제 전문가입니다. 아래 주제로 **한국어** 4지선다 퀴즈 문제 15개를 만들어주세요.

주제: {topic_name}
세부 항목: {subtopic}
현재 날짜: 2026년 4월 20일 기준

규칙:
1. 문제는 실무에서 실제로 중요한 내용 위주
2. 해설은 3줄 이상, 왜 그게 답인지 + 실무 맥락 포함
3. 선택지는 그럴듯하게 (너무 쉬운 오답 금지)
4. 반드시 아래 JSON 배열 형식으로만 출력 (마크다운, 설명 없이 JSON만)

출력 형식 (JSON 배열):
[
  {{
    "id": "{prefix}_{start_num:03d}",
    "question": "질문",
    "choices": ["보기1", "보기2", "보기3", "보기4"],
    "answer": 0,
    "explanation": "상세 해설 (왜 이게 답인지, 실무 활용법 포함)",
    "tag": "태그명",
    "image_prompt": "영어로 된 이미지 생성 프롬프트"
  }}
]

answer는 0~3 사이 정수 (0=첫번째 보기가 정답).
지금 바로 JSON 배열만 출력하세요.
"""

def load_existing(genre):
    path = os.path.join(Q_DIR, f'{genre}.json')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return []

def save_questions(genre, questions):
    path = os.path.join(Q_DIR, f'{genre}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"  [{genre}] {len(questions)}문제 저장 완료")

def parse_json_from_miro(text):
    """미로 응답에서 JSON 배열 추출 (코드블록 포함 처리)"""
    import re
    # 코드블록 안에 있으면 추출
    block = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if block:
        text = block.group(1)
    # JSON 배열 패턴
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        raw = match.group()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 불완전한 마지막 객체 제거 후 재시도
            raw2 = re.sub(r',?\s*\{[^}]*$', '', raw).rstrip(',') + ']'
            try:
                return json.loads(raw2)
            except Exception:
                pass
    return []

def generate_for_topic(genre, topic_info, target=100):
    """미로에게 특정 주제 문제 생성 위임"""
    existing = load_existing(genre)
    existing_ids = {q['id'] for q in existing}
    all_questions = list(existing)
    subtopics = topic_info['subtopics']

    print(f"\n{'='*50}")
    print(f"[{genre}] 목표: {target}문제 (현재: {len(existing)}개)")

    sub_idx = 0
    attempt = 0

    while len(all_questions) < target and attempt < 30:
        subtopic = subtopics[sub_idx % len(subtopics)]
        sub_idx += 1
        attempt += 1

        start_num = len(all_questions) + 1
        prompt = PROMPT_TEMPLATE.format(
            topic_name=topic_info['name'],
            subtopic=subtopic,
            prefix=genre[:3],
            start_num=start_num
        )

        print(f"  [{genre}] 미로에게 요청 중... (현재 {len(all_questions)}개, 목표 {target}개)")
        miro_task = f"다음 지시사항대로 퀴즈 문제를 생성해주세요. ask_gemini 도구를 사용해서 문제를 만들어주세요:\n\n{prompt}"

        result = ask_miro(miro_task)
        new_qs = parse_json_from_miro(result)

        added = 0
        for q in new_qs:
            if q.get('id') and q['id'] not in existing_ids:
                # ID 중복 방지
                q['id'] = f"{genre[:3]}_{len(all_questions)+1:03d}"
                all_questions.append(q)
                existing_ids.add(q['id'])
                added += 1

        print(f"  → {added}개 추가됨 (누적: {len(all_questions)}개)")

        # 중간 저장
        if added > 0:
            save_questions(genre, all_questions)

        time.sleep(2)

    save_questions(genre, all_questions)
    return len(all_questions)

if __name__ == '__main__':
    # 실행할 장르 선택 (인자 없으면 전체)
    genres_to_run = sys.argv[1:] if len(sys.argv) > 1 else list(TOPICS.keys())

    print(f"퀴즈 문제 생성 시작: {genres_to_run}")

    for genre in genres_to_run:
        if genre not in TOPICS:
            print(f"알 수 없는 장르: {genre}")
            continue
        count = generate_for_topic(genre, TOPICS[genre], target=100)
        print(f"[완료] {genre}: 총 {count}문제")

    print("\n모든 생성 완료!")
