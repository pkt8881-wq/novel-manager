"""
Neural Cave - ComfyUI Image Generator
ComfyUI가 실행 중인 상태에서 이 스크립트를 실행하세요 (포트 8188)
"""

import json
import time
import urllib.request
import urllib.parse
import os
import sys

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 이미지 목록 정의
IMAGES = [
    {
        "filename": "hero_bg.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 1920,
        "height": 1080,
        "seed": 42,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "futuristic underground mechanical cave, cyberpunk, dark cave walls with embedded glowing machine parts and gears, neon teal and orange lighting, holographic displays, steam and mist, ultra detailed, cinematic, dramatic lighting, 8k",
        "negative": "bright, daylight, simple, cartoon, anime, blur, people, human"
    },
    {
        "filename": "aria_android.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 768,
        "seed": 77,
        "steps": 28,
        "cfg": 7.5,
        "prompt": "full body android robot AI guide, feminine humanoid robot, glowing blue eyes, sleek chrome and black armor, neon teal highlights, holographic interface emanating from hands, futuristic cyberpunk style, transparent background, studio lighting, high detail",
        "negative": "human skin, organic, ugly, deformed, extra limbs, blurry, low quality, background clutter"
    },
    {
        "filename": "level1_beginner.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 800,
        "height": 500,
        "seed": 11,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "cave entrance with glowing runes and simple AI symbols, beginner path, soft neon blue lighting, floating holographic text ABCs of AI, welcoming atmosphere, futuristic cave, cinematic",
        "negative": "dark, scary, complex machinery, people"
    },
    {
        "filename": "level2_tools.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 800,
        "height": 500,
        "seed": 22,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "cyberpunk AI tool workshop inside a cave, holographic interfaces ChatGPT Claude Midjourney logos, glowing screens, neon orange tools, mechanical arms, high tech equipment, dramatic cave lighting",
        "negative": "people, human, simple, boring"
    },
    {
        "filename": "level3_vibe.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 800,
        "height": 500,
        "seed": 33,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "holographic code streams flowing through a cave, vibe coding concept, purple and cyan neon code waterfall, AI writing code autonomously, matrix-style symbols, futuristic programming environment",
        "negative": "people, simple, text only, boring"
    },
    {
        "filename": "level4_agents.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 800,
        "height": 500,
        "seed": 44,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "multiple AI agent robots working together in a futuristic cave control room, interconnected network nodes, autonomous robot agents, glowing neural network, cyberpunk command center, neon blue and orange",
        "negative": "humans, simple, boring"
    },
    {
        "filename": "level5_expert.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 800,
        "height": 500,
        "seed": 55,
        "steps": 25,
        "cfg": 7.0,
        "prompt": "summit of a futuristic AI cave mountain, master control room, massive holographic AI brain, expert level technology, golden and teal neon, triumphant atmosphere, ultra advanced cyberpunk technology",
        "negative": "people, simple, boring"
    },
    {
        "filename": "gallery_01.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 768,
        "height": 512,
        "seed": 201,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "AI neural network visualization, glowing brain synapses, deep blue purple light, abstract digital mindscape, cyberpunk",
        "negative": "people, text"
    },
    {
        "filename": "gallery_02.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 512,
        "seed": 202,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "robot hand touching human hand, AI meets humanity, neon teal and orange glow, cinematic, dramatic",
        "negative": "ugly, blurry"
    },
    {
        "filename": "gallery_03.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 768,
        "seed": 203,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "vertical holographic display showing AI code, floating in dark cave, cyan neon code, cyberpunk terminal",
        "negative": "people, boring"
    },
    {
        "filename": "gallery_04.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 768,
        "height": 512,
        "seed": 204,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "futuristic AI data center inside cave, server racks with neon lights, teal and orange glow, mist atmosphere, cinematic",
        "negative": "people, text"
    },
    {
        "filename": "gallery_05.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 512,
        "seed": 205,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "AI prompt engineering visualization, floating text particles forming shapes, magical neon cave, purple and cyan",
        "negative": "boring, simple"
    },
    {
        "filename": "gallery_06.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 768,
        "height": 512,
        "seed": 206,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "multiple autonomous AI agents as glowing orbs working together, network visualization, cyberpunk style, blue and orange neon",
        "negative": "people"
    },
    {
        "filename": "gallery_07.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 512,
        "seed": 207,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "AI image generation concept art, fractal digital art, vibrant colors, machine creativity, abstract cyberpunk",
        "negative": "boring, dull"
    },
    {
        "filename": "gallery_08.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 512,
        "height": 768,
        "seed": 208,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "vertical view of futuristic cave shaft going deep underground, glowing machinery, holographic ladder, neon teal light rays",
        "negative": "people, simple"
    },
    {
        "filename": "gallery_09.png",
        "model": "juggernautXL_v9Rundiffusionphoto2.safetensors",
        "width": 768,
        "height": 512,
        "seed": 209,
        "steps": 22,
        "cfg": 7.0,
        "prompt": "AI expert working with holographic displays in futuristic cave, silhouette against glowing screens, cinematic, cyberpunk orange and teal",
        "negative": "ugly, blurry"
    },
]

def build_workflow(img_config):
    """ComfyUI API 워크플로우 JSON 생성"""
    return {
        "3": {
            "inputs": {
                "seed": img_config["seed"],
                "steps": img_config["steps"],
                "cfg": img_config["cfg"],
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": img_config["model"]
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": img_config["width"],
                "height": img_config["height"],
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": img_config["prompt"],
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": img_config["negative"],
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": img_config["filename"].replace(".png", ""),
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }


def queue_prompt(workflow):
    """ComfyUI에 프롬프트 큐 추가"""
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_history(prompt_id):
    """히스토리 가져오기"""
    with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
        return json.loads(resp.read())


def download_image(filename, subfolder, folder_type, save_path):
    """이미지 다운로드"""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    })
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}") as resp:
        with open(save_path, "wb") as f:
            f.write(resp.read())


def wait_for_image(prompt_id, timeout=300):
    """이미지 생성 완료 대기"""
    start = time.time()
    while time.time() - start < timeout:
        history = get_history(prompt_id)
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    return node_output["images"]
        time.sleep(2)
    return None


def main():
    print(f"=== Neural Cave 이미지 생성기 ===")
    print(f"출력 폴더: {OUTPUT_DIR}")
    print(f"총 이미지 수: {len(IMAGES)}\n")

    # ComfyUI 연결 확인
    try:
        with urllib.request.urlopen(f"{COMFYUI_URL}/system_stats") as resp:
            stats = json.loads(resp.read())
            print(f"ComfyUI 연결 성공!")
            vram = stats.get("devices", [{}])[0].get("vram_total", 0) / (1024**3)
            print(f"GPU VRAM: {vram:.1f}GB\n")
    except Exception as e:
        print(f"ComfyUI 연결 실패: {e}")
        print("ComfyUI가 실행 중인지 확인하세요 (포트 8188)")
        sys.exit(1)

    success = 0
    failed = []

    for i, img_cfg in enumerate(IMAGES):
        save_path = os.path.join(OUTPUT_DIR, img_cfg["filename"])

        # 이미 존재하는 파일 스킵
        if os.path.exists(save_path):
            print(f"[{i+1}/{len(IMAGES)}] 건너뜀 (이미 존재): {img_cfg['filename']}")
            success += 1
            continue

        print(f"[{i+1}/{len(IMAGES)}] 생성 중: {img_cfg['filename']}")
        print(f"  프롬프트: {img_cfg['prompt'][:60]}...")

        try:
            # 워크플로우 큐에 추가
            workflow = build_workflow(img_cfg)
            result = queue_prompt(workflow)
            prompt_id = result["prompt_id"]
            print(f"  큐 ID: {prompt_id}")

            # 완료 대기
            images = wait_for_image(prompt_id, timeout=300)

            if images:
                # 첫 번째 이미지 다운로드
                img_info = images[0]
                dl_filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")
                folder_type = img_info.get("type", "output")

                download_image(dl_filename, subfolder, folder_type, save_path)
                file_size = os.path.getsize(save_path) / 1024
                print(f"  완료! 저장: {save_path} ({file_size:.0f}KB)\n")
                success += 1
            else:
                print(f"  실패: 타임아웃\n")
                failed.append(img_cfg["filename"])

        except Exception as e:
            print(f"  오류: {e}\n")
            failed.append(img_cfg["filename"])

    print(f"\n=== 완료 ===")
    print(f"성공: {success}/{len(IMAGES)}")
    if failed:
        print(f"실패: {', '.join(failed)}")
    else:
        print("모든 이미지 생성 완료!")
        print(f"\n다음 단계: update_html.py 실행하여 HTML 업데이트")


if __name__ == "__main__":
    main()
