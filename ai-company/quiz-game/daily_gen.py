# -*- coding: utf-8 -*-
"""
매일 실행 - 미로로 난이도별 50개 문제 생성
사용법: python daily_gen.py
"""
import sys, os, json, time, random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'clients'))
from miro_client import ask_miro

Q_DIR = os.path.join(os.path.dirname(__file__), 'questions')

# 오늘 생성할 계획: 카테고리 × 난이도 조합
DAILY_PLAN = [
    # (카테고리, 난이도, 주제, 개수)
    ('agents',    1, 'LangChain 기초: 체인, 프롬프트 템플릿, LLM 연결 개념', 6),
    ('agents',    2, 'RAG 파이프라인: 청킹 전략, 임베딩, 리트리버 설정', 6),
    ('agents',    3, 'LangGraph 상태 그래프, 조건부 엣지, 멀티에이전트 오케스트레이션', 6),
    ('python',    1, '파이썬 기초: 리스트/딕셔너리 조작, 컴프리헨션, 기본 내장함수', 6),
    ('python',    2, '파이썬 데코레이터, 컨텍스트 매니저, 제너레이터 yield', 6),
    ('python',    3, '파이썬 asyncio 고급: gather, TaskGroup, 동시성 패턴', 6),
    ('server',    1, 'HTTP 기초: 상태코드, GET/POST 차이, 헤더의 역할', 7),
    ('server',    2, 'FastAPI 의존성 주입, 미들웨어, 응답 모델 설계', 7),
]

def load_json(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_json(text):
    import re
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    text = re.sub(r'```\s*$', '', text).strip()
    start, end = text.find('['), text.rfind(']')
    if start == -1 or end == -1:
        return []
    chunk = text[start:end+1]
    try:
        return json.loads(chunk)
    except:
        last = chunk.rfind(',', 0, end)
        if last > 0:
            try:
                return json.loads(chunk[:last] + ']')
            except:
                pass
    return []

DIFF_LABEL = {1: '쉬운(입문)', 2: '보통(중급)', 3: '어려운(전문가)'}

def make_prompt(topic, difficulty, prefix, start_idx, count):
    diff_str = DIFF_LABEL[difficulty]
    return (
        f"한국어 4지선다 퀴즈 {count}개. JSON 배열만 출력. "
        f"난이도: {diff_str}. 주제: {topic}.\n"
        "형식:\n"
        "[\n"
        "  {\n"
        f'    "id": "{prefix}_{str(start_idx).zfill(3)}",\n'
        f'    "difficulty": {difficulty},\n'
        '    "question": "질문",\n'
        '    "choices": ["보기1","보기2","보기3","보기4"],\n'
        '    "answer": 0,\n'
        '    "explanation": "상세 설명(한국어)",\n'
        '    "tag": "태그",\n'
        '    "image_prompt": "English description"\n'
        "  }\n"
        "]\n"
        f"answer는 0~3 정답 인덱스. {diff_str} 수준에 맞게. JSON 배열만."
    )

PREFIX_MAP = {
    'agents': 'agt', 'ai_tools': 'ai', 'python': 'py',
    'server': 'srv', 'database': 'db', 'local_llm': 'llm',
    'history': 'his', 'common': 'cmn',
}

def fix_ids(items, prefix, start):
    for i, item in enumerate(items):
        item['id'] = f"{prefix}_{str(start + i).zfill(3)}"
    return items

def check_duplicate(new_q, existing):
    existing_texts = {q['question'][:30] for q in existing}
    return new_q['question'][:30] in existing_texts

total_added = 0

for (category, difficulty, topic, count) in DAILY_PLAN:
    path = os.path.join(Q_DIR, f'{category}.json')
    existing = load_json(path)
    prefix = PREFIX_MAP.get(category, category[:3])
    start_idx = len(existing) + 1

    print(f"\n[{category} / 난이도{difficulty}] {topic[:40]}")
    prompt = make_prompt(topic, difficulty, prefix, start_idx, count)

    try:
        result = ask_miro(prompt)
        items = parse_json(result)
        if not items:
            print(f"  파싱 실패. 응답: {result[:150]}")
            time.sleep(2)
            continue

        # 중복 제거
        unique = [q for q in items if not check_duplicate(q, existing)]
        if len(unique) < len(items):
            print(f"  중복 {len(items)-len(unique)}개 제거")

        if unique:
            unique = fix_ids(unique, prefix, start_idx)
            for q in unique:
                q['difficulty'] = difficulty  # 확실히 세팅
            existing.extend(unique)
            save_json(path, existing)
            total_added += len(unique)
            print(f"  +{len(unique)}개 추가 (총 {len(existing)}개)")
        else:
            print("  추가할 문제 없음")

    except Exception as e:
        print(f"  오류: {e}")

    time.sleep(3)

print(f"\n=== 오늘 총 {total_added}개 추가 완료 ===")
for cat in set(c for c, *_ in DAILY_PLAN):
    path = os.path.join(Q_DIR, f'{cat}.json')
    data = load_json(path)
    by_diff = {d: sum(1 for q in data if q.get('difficulty') == d) for d in [1,2,3]}
    print(f"  {cat}: 총{len(data)} (쉬움:{by_diff[1]} 보통:{by_diff[2]} 어려움:{by_diff[3]})")
