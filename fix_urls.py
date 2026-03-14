import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

mapping = {
    42:  'hero_bg',
    77:  'aria_android',
    11:  'level1_beginner',
    22:  'level2_tools',
    33:  'level3_vibe',
    44:  'level4_agents',
    55:  'level5_expert',
    201: 'gallery_01',
    202: 'gallery_02',
    203: 'gallery_03',
    204: 'gallery_04',
    205: 'gallery_05',
    206: 'gallery_06',
    207: 'gallery_07',
    208: 'gallery_08',
    209: 'gallery_09',
}

total = 0
for seed, name in mapping.items():
    pattern = r'https://image\.pollinations\.ai/prompt/[^\'"]*seed=' + str(seed) + r'[^\'"]*'
    matches = re.findall(pattern, content)
    if matches:
        print(f'seed={seed} -> {name}.png: {len(matches)}개 교체')
        total += len(matches)
    content = re.sub(pattern, f'images/{name}.png', content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n총 {total}개 교체 완료!')
