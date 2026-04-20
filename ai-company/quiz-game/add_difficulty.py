# -*- coding: utf-8 -*-
"""기존 문제 파일에 difficulty(1/2/3) 필드 추가"""
import json, glob, os

# 카테고리별 난이도 분포 [쉬움%, 보통%, 어려움%]
CATEGORY_BIAS = {
    'history':  [0.40, 0.40, 0.20],
    'common':   [0.40, 0.40, 0.20],
    'python':   [0.25, 0.45, 0.30],
    'server':   [0.25, 0.45, 0.30],
    'database': [0.25, 0.45, 0.30],
    'local_llm':[0.20, 0.40, 0.40],
    'agents':   [0.20, 0.40, 0.40],
    'ai_tools': [0.15, 0.40, 0.45],
}

Q_DIR = os.path.join(os.path.dirname(__file__), 'questions')

for path in sorted(glob.glob(Q_DIR + '/*.json')):
    name = os.path.basename(path).replace('.json', '')
    if name not in CATEGORY_BIAS:
        continue

    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    ratios = CATEGORY_BIAS[name]
    n = len(data)

    for i, item in enumerate(data):
        if 'difficulty' in item:
            continue
        pos = i / n
        if pos < ratios[0]:
            item['difficulty'] = 1
        elif pos < ratios[0] + ratios[1]:
            item['difficulty'] = 2
        else:
            item['difficulty'] = 3

    counts = [sum(1 for q in data if q.get('difficulty') == d) for d in [1, 2, 3]]

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'{name}({n}): 쉬움={counts[0]} 보통={counts[1]} 어려움={counts[2]}')

print('difficulty 추가 완료!')
