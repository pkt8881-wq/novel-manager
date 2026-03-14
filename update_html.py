"""
Neural Cave - HTML 이미지 경로 업데이트
generate_images.py 실행 후 이 스크립트를 실행하세요
"""

import os
import re

HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# Pollinations URL → 로컬 파일 매핑
REPLACEMENTS = [
    # Hero background
    (
        r"url\('https://image\.pollinations\.ai/prompt/[^']*seed=42[^']*'\)",
        "url('images/hero_bg.png')"
    ),
    # ARIA android image
    (
        r"https://image\.pollinations\.ai/prompt/android[^\"']*seed=77[^\"']*",
        "images/aria_android.png"
    ),
    # Level 1 image
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=11[^\"']*",
        "images/level1_beginner.png"
    ),
    # Level 2 image
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=22[^\"']*",
        "images/level2_tools.png"
    ),
    # Level 3 image
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=33[^\"']*",
        "images/level3_vibe.png"
    ),
    # Level 4 image
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=44[^\"']*",
        "images/level4_agents.png"
    ),
    # Level 5 image
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=55[^\"']*",
        "images/level5_expert.png"
    ),
    # Gallery images (seed 201-209)
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=201[^\"']*",
        "images/gallery_01.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=202[^\"']*",
        "images/gallery_02.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=203[^\"']*",
        "images/gallery_03.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=204[^\"']*",
        "images/gallery_04.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=205[^\"']*",
        "images/gallery_05.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=206[^\"']*",
        "images/gallery_06.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=207[^\"']*",
        "images/gallery_07.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=208[^\"']*",
        "images/gallery_08.png"
    ),
    (
        r"https://image\.pollinations\.ai/prompt/[^\"']*seed=209[^\"']*",
        "images/gallery_09.png"
    ),
]

def check_images():
    """생성된 이미지 파일 확인"""
    expected = [
        "hero_bg.png", "aria_android.png",
        "level1_beginner.png", "level2_tools.png", "level3_vibe.png",
        "level4_agents.png", "level5_expert.png",
        "gallery_01.png", "gallery_02.png", "gallery_03.png",
        "gallery_04.png", "gallery_05.png", "gallery_06.png",
        "gallery_07.png", "gallery_08.png", "gallery_09.png",
    ]
    missing = []
    for f in expected:
        path = os.path.join(IMAGES_DIR, f)
        if not os.path.exists(path):
            missing.append(f)
    return missing

def update_html():
    print("=== HTML 이미지 경로 업데이트 ===")

    # 이미지 파일 확인
    missing = check_images()
    if missing:
        print(f"경고: 다음 이미지가 없습니다:")
        for m in missing:
            print(f"  - {m}")
        answer = input("\n계속 진행하시겠습니까? (y/n): ").strip().lower()
        if answer != 'y':
            print("중단됨.")
            return

    # HTML 읽기
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content
    replace_count = 0

    # 치환 실행
    for pattern, replacement in REPLACEMENTS:
        new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
        if count > 0:
            print(f"  치환 {count}개: ...→ {replacement}")
            replace_count += count
            content = new_content

    if replace_count == 0:
        print("치환할 Pollinations URL을 찾지 못했습니다.")
        print("이미 업데이트되어 있거나 URL 형식이 다를 수 있습니다.")
        return

    # 백업 저장
    backup_path = HTML_FILE + ".backup"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(original_content)
    print(f"\n백업 저장: {backup_path}")

    # 업데이트된 HTML 저장
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n완료! 총 {replace_count}개 URL 치환됨")
    print(f"파일 저장: {HTML_FILE}")

if __name__ == "__main__":
    update_html()
