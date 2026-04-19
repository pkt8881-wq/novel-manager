# -*- coding: utf-8 -*-
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'clients'))
from miro_client import ask_miro

QUESTIONS_DIR = os.path.join(os.path.dirname(__file__), 'questions')

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_json(text):
    import re
    text = text.strip()
    # Remove code fences
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    # Find JSON array
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1:
        return []
    text = text[start:end+1]
    try:
        return json.loads(text)
    except:
        # Try to fix incomplete last item
        last_comma = text.rfind(',', 0, end)
        if last_comma > 0:
            try:
                return json.loads(text[:last_comma] + ']')
            except:
                pass
    return []

TARGETS = {
    'agents': {
        'label': 'AI 에이전트',
        'topics': [
            ('LangChain LCEL 체인 구성, Runnable, pipe 연산자', 'agt'),
            ('RAG 파이프라인 - 청킹, 임베딩, 벡터DB, 리트리버', 'agt'),
            ('CrewAI 에이전트 역할/목표/백스토리 설계', 'agt'),
            ('ReAct 패턴 - Thought/Action/Observation 루프', 'agt'),
            ('MCP Tool 정의, Tool Use, 함수 호출 흐름', 'agt'),
            ('AutoGen 멀티에이전트 대화 패턴', 'agt'),
            ('프롬프트 인젝션 공격과 방어, Guardrail', 'agt'),
            ('LangGraph 상태 그래프, 조건부 엣지', 'agt'),
            ('임베딩 모델 - text-embedding-3, BGE, 차원', 'agt'),
            ('벡터 데이터베이스 - Chroma, Pinecone, FAISS 비교', 'agt'),
        ]
    },
    'python': {
        'label': '파이썬',
        'topics': [
            ('파이썬 데코레이터 - functools.wraps, 클래스 기반 데코레이터', 'py'),
            ('asyncio - gather, create_task, Event, Lock, Queue', 'py'),
            ('파이썬 타입 힌트 - TypeVar, Generic, Protocol, Literal', 'py'),
            ('파이썬 패키징 - pyproject.toml, uv, pip-tools', 'py'),
            ('파이썬 테스팅 - pytest, fixture, mock, parametrize', 'py'),
            ('파이썬 데이터클래스 고급 - field, InitVar, __post_init__', 'py'),
            ('파이썬 컨텍스트매니저 - contextlib, asynccontextmanager', 'py'),
            ('파이썬 멀티프로세싱 - Pool, Queue, shared memory', 'py'),
            ('파이썬 pydantic v2 - model_validator, field_validator, computed_field', 'py'),
            ('파이썬 이터레이터/제너레이터 고급 - send, yield from, itertools', 'py'),
        ]
    },
    'server': {
        'label': '서버 만들기',
        'topics': [
            ('FastAPI 라우터 구조화, APIRouter, prefix, tags', 'srv'),
            ('FastAPI 인증 - OAuth2PasswordBearer, JWT 검증 미들웨어', 'srv'),
            ('FastAPI 파일 업로드 - UploadFile, Form, multipart', 'srv'),
            ('FastAPI 스트리밍 응답 - StreamingResponse, Server-Sent Events', 'srv'),
            ('FastAPI 테스팅 - TestClient, pytest, dependency override', 'srv'),
            ('Nginx 리버스 프록시 설정, load_module, upstream', 'srv'),
            ('Docker 컨테이너화 - Dockerfile, docker-compose, healthcheck', 'srv'),
            ('HTTP/2, gRPC, WebSocket 비교와 사용 시나리오', 'srv'),
            ('Redis 캐싱 - SET/GET/EXPIRE, pub/sub, 세션 저장', 'srv'),
            ('Celery 비동기 태스크 큐 - broker, worker, chord, chain', 'srv'),
        ]
    },
    'database': {
        'label': '데이터베이스',
        'topics': [
            ('PostgreSQL vs SQLite vs MySQL 비교, 사용 시나리오', 'db'),
            ('SQL 고급 - CTE, 윈도우 함수, RANK, PARTITION BY', 'db'),
            ('SQLAlchemy 2.0 - select(), scalars(), execute(), async session', 'db'),
            ('데이터베이스 정규화 - 1NF/2NF/3NF, 역정규화', 'db'),
            ('트랜잭션 ACID, 격리 수준 - READ COMMITTED, SERIALIZABLE', 'db'),
            ('인덱스 전략 - 복합인덱스, 커버링인덱스, 실행계획 EXPLAIN', 'db'),
            ('Alembic 마이그레이션 - revision, upgrade, downgrade', 'db'),
            ('Redis 자료구조 - String, Hash, List, Set, Sorted Set', 'db'),
            ('MongoDB 도큐먼트 모델, 집계 파이프라인, $lookup', 'db'),
            ('데이터베이스 연결 풀 - pool_size, max_overflow, pool_recycle', 'db'),
        ]
    },
    'local_llm': {
        'label': '로컬 LLM',
        'topics': [
            ('llama.cpp 컴파일 플래그 - CUDA, Metal, CPU, threads', 'llm'),
            ('Ollama Modelfile - FROM, PARAMETER, TEMPLATE, SYSTEM', 'llm'),
            ('GGUF 양자화 비교 - Q2_K vs Q4_K_M vs Q8_0 품질/속도', 'llm'),
            ('Open WebUI 설치, Ollama 연동, 모델 관리', 'llm'),
            ('vLLM 서버 - tensor parallel, continuous batching, 처리량', 'llm'),
            ('RAG with Ollama - 임베딩 모델, nomic-embed-text, mxbai', 'llm'),
            ('Hugging Face transformers - pipeline, AutoModel, 토크나이저', 'llm'),
            ('KV Cache, Flash Attention, context window 관리', 'llm'),
            ('로컬 LLM 벤치마크 - MMLU, HumanEval, tokens/sec 측정', 'llm'),
            ('AnythingLLM, Jan, LM Studio 기능 비교', 'llm'),
        ]
    },
    'history': {
        'label': '역사',
        'topics': [
            ('한국 현대사 - 일제강점기, 광복, 한국전쟁', 'his'),
            ('세계 2차대전 주요 사건과 결과', 'his'),
            ('산업혁명 - 증기기관, 방직기, 사회변화', 'his'),
            ('프랑스혁명 - 원인, 전개, 나폴레옹 집권', 'his'),
            ('조선시대 - 세종대왕, 임진왜란, 당쟁', 'his'),
            ('냉전시대 - 마샬플랜, 쿠바 미사일 위기, 베를린 장벽', 'his'),
            ('동아시아 근대화 - 메이지유신, 청일전쟁, 의화단운동', 'his'),
            ('실크로드와 몽골 제국 팽창', 'his'),
            ('르네상스와 종교개혁', 'his'),
            ('미국 독립혁명과 남북전쟁', 'his'),
        ]
    },
    'common': {
        'label': '상식',
        'topics': [
            ('물리학 - 양자역학, 불확정성 원리, 슈뢰딩거 고양이', 'cmn'),
            ('화학 - 산화환원, pH, 촉매, 유기화합물 명명', 'cmn'),
            ('생물학 - 진화론, 자연선택, 유전자 돌연변이', 'cmn'),
            ('지구과학 - 판구조론, 지진, 화산, 대기권', 'cmn'),
            ('천문학 - 블랙홀, 중력파, 허블망원경', 'cmn'),
            ('경제학 - 수요공급 법칙, 탄력성, 기회비용', 'cmn'),
            ('심리학 - 인지 편향, 확증 편향, 더닝-크루거 효과', 'cmn'),
            ('언어학 - 촘스키, 보편문법, 언어 습득 이론', 'cmn'),
            ('철학 - 소크라테스, 데카르트, 칸트의 핵심 사상', 'cmn'),
            ('수학 - 소수, 페르마의 마지막 정리, 리만 가설', 'cmn'),
        ]
    },
}

def make_prompt(topic_desc, prefix, existing_count):
    return (
        "한국어 4지선다 퀴즈 10개를 JSON 배열로 출력하세요. "
        "설명은 반드시 한국어로 작성. "
        "주제: " + topic_desc + "\n"
        "형식 (JSON 배열만, 다른 텍스트 없이):\n"
        "[\n"
        "  {\n"
        '    "id": "' + prefix + '_' + str(existing_count + 1).zfill(3) + '",\n'
        '    "question": "질문 내용",\n'
        '    "choices": ["보기1", "보기2", "보기3", "보기4"],\n'
        '    "answer": 0,\n'
        '    "explanation": "상세한 한국어 설명",\n'
        '    "tag": "태그",\n'
        '    "image_prompt": "English image description"\n'
        "  },\n"
        "  ...\n"
        "]\n"
        "answer는 정답 인덱스(0~3). 반드시 JSON 배열만 출력."
    )

def fix_ids(items, prefix, start):
    for i, item in enumerate(items):
        item['id'] = f"{prefix}_{str(start + i).zfill(3)}"
    return items

def generate_for_category(key, info, target=80):
    path = os.path.join(QUESTIONS_DIR, f"{key}.json")
    existing = load_json(path)
    print(f"\n=== {info['label']} ({key}): {len(existing)} 문제 존재 ===")

    prefix = info['topics'][0][1]
    topic_list = info['topics']
    topic_idx = 0

    while len(existing) < target and topic_idx < len(topic_list):
        topic_desc, pfx = topic_list[topic_idx]
        topic_idx += 1
        print(f"  주제: {topic_desc}")

        prompt = make_prompt(topic_desc, pfx, len(existing))
        try:
            result = ask_miro(prompt)
            new_items = parse_json(result)
            if new_items:
                new_items = fix_ids(new_items, pfx, len(existing) + 1)
                existing.extend(new_items)
                save_json(path, existing)
                print(f"  +{len(new_items)} 추가 -> 총 {len(existing)}개")
            else:
                print(f"  파싱 실패. 응답: {result[:200]}")
        except Exception as e:
            print(f"  오류: {e}")

        time.sleep(2)

    print(f"  완료: {len(existing)}개")
    return len(existing)

if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        keys = args
    else:
        keys = list(TARGETS.keys())

    for key in keys:
        if key in TARGETS:
            generate_for_category(key, TARGETS[key], target=80)
        else:
            print(f"알 수 없는 카테고리: {key}")

    print("\n=== 생성 완료 ===")
    for key in TARGETS:
        path = os.path.join(QUESTIONS_DIR, f"{key}.json")
        data = load_json(path)
        print(f"  {key}: {len(data)}개")
