#!/usr/bin/env python3
"""
卡圖自動生成引導與生圖客戶端 (generate_cards.py)
支援多種生圖後端 (Google Imagen / OpenAI DALL-E / 本地 Stable Diffusion / ComfyUI)，
並支援檢索缺圖清單、串接 process_cards.py 自動完成裁切轉檔。
"""

import os
import sys
import json
import base64
import tomllib
import argparse
import subprocess
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = BASE_DIR / "raw_images"
DIST_DIR = BASE_DIR / "dist"
CARDS_FILE = DATA_DIR / "cards.toml"
PROMPTS_FILE = DATA_DIR / "prompts.json"
PROCESS_SCRIPT = BASE_DIR / "scripts" / "process_cards.py"
BUILD_SCRIPT = BASE_DIR / "scripts" / "build_prompts.py"


def load_prompts() -> list[dict]:
    if not PROMPTS_FILE.exists():
        print("[*] 尚未發現 prompts.json，正在自動編譯提示詞...")
        subprocess.run([sys.executable, str(BUILD_SCRIPT)], check=True)
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_card_prompt(card_id: str) -> Optional[dict]:
    prompts = load_prompts()
    for item in prompts:
        if item["id"].upper() == card_id.upper():
            return item
    return None


def check_cdp_browser(host: str = "http://127.0.0.1:9222") -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(f"{host}/json/version", method="GET")
        with urllib.request.urlopen(req, timeout=1.0) as response:
            return response.status == 200
    except Exception:
        return False


def generate_with_gemini_browser(prompt_info: dict, host: str = "http://127.0.0.1:9222") -> Path | None:
    card_id = prompt_info["id"]
    print(f"[*] 正在透過已登入的 Chrome 瀏覽器 (Gemini Pro) 生成卡圖...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] 尚未安裝 playwright，請先執行 pip install playwright。")
        return None

    if prompt_info.get("kind") != "character":
        prompt_text = (
            f"請生成一張 16:9 橫向卡牌插畫：\n"
            f"【核心構圖約束】：畫面中絕對不要出現任何人物、角色、人類肢體、全身或半身人物（strictly no humans, no people, no characters, no faces）。視覺焦點必須 100% 集中於武器本體、斬擊劍氣、魔法衝擊波、道具物件、金幣或戰場靜物本身。\n"
            f"【插畫內容描述】：{prompt_info['positive_prompt']}\n"
            f"完全不要出現文字、文字標籤或外框。"
        )
    else:
        prompt_text = (
            f"請生成一張 16:9 橫向卡牌插畫：\n"
            f"【插畫內容描述】：{prompt_info['positive_prompt']}\n"
            f"完全不要出現文字、文字標籤或外框。"
        )

    try:
        import time
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(host)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            # Ensure clean chat page
            page.keyboard.press("Escape")
            time.sleep(0.3)
            
            # Click '新對話' if on chat page
            new_chat_btn = page.locator('button:has-text("新對話"), a:has-text("新對話")').first
            if new_chat_btn.is_visible():
                try:
                    new_chat_btn.click(force=True)
                    time.sleep(1)
                except Exception:
                    pass
            elif page.url != "https://gemini.google.com/app":
                page.goto("https://gemini.google.com/app")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1.5)

            # Close any leftover backdrop
            page.keyboard.press("Escape")
            time.sleep(0.3)

            # Ensure 3.1 Pro mode
            picker = page.locator('button[aria-label*="開啟模式挑選器"]').first
            if picker.is_visible() and "Pro" not in picker.inner_text():
                try:
                    picker.click(force=True)
                    time.sleep(0.8)
                    page.locator('text="3.1 Pro"').first.click(force=True)
                    time.sleep(0.8)
                except Exception:
                    pass

            # Fill editor
            editor = page.locator('div[contenteditable="true"]').first
            editor.click(force=True)
            time.sleep(0.3)
            editor.fill(prompt_text)
            time.sleep(0.5)

            # Send prompt
            send_btn = page.locator('button[aria-label="傳送訊息"]').first
            if send_btn.is_visible():
                send_btn.click(force=True)
            else:
                editor.press("Enter")

            print("[*] 提示詞已送出，正在等待 Gemini 生成圖片...")
            start_time = time.time()
            max_wait = 90
            found_b64 = None

            while time.time() - start_time < max_wait:
                imgs = page.locator('img').all()
                for img in imgs:
                    src = img.get_attribute('src') or ''
                    if 'blob:' in src or 'googleusercontent' in src:
                        box = img.bounding_box()
                        if box and box['width'] > 200 and box['height'] > 120:
                            found_b64 = page.evaluate('''(selector) => {
                                const img = document.querySelector(selector);
                                if (!img) return null;
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth || img.width;
                                canvas.height = img.naturalHeight || img.height;
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0);
                                return canvas.toDataURL('image/jpeg', 0.95).split(',')[1];
                            }''', f'img[src="{src}"]')
                            if found_b64:
                                break
                if found_b64:
                    break
                time.sleep(3)

            if not found_b64:
                print("[!] 等待生成逾時或未偵測到產出圖片。")
                return None

            out_file = RAW_DIR / f"{card_id}.jpg"
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            with open(out_file, "wb") as f:
                f.write(base64.b64decode(found_b64))

            print(f"[✓] 成功由 Gemini 瀏覽器生成大圖: {out_file.name}")
            return out_file
    except Exception as e:
        print(f"[!] 瀏覽器生圖過程發生錯誤: {e}")
        return None


def check_local_sd_webui(host: str = "http://127.0.0.1:7860") -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(f"{host}/sdapi/v1/options", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as response:
            return response.status == 200
    except Exception:
        return False


def generate_with_sd_webui(prompt_info: dict, host: str = "http://127.0.0.1:7860") -> Path | None:
    import urllib.request
    card_id = prompt_info["id"]
    print(f"[*] 正在連線至本機 Stable Diffusion WebUI ({host})...")
    payload = {
        "prompt": prompt_info["positive_prompt"],
        "negative_prompt": prompt_info["negative_prompt"],
        "width": 1024,
        "height": 600,  # 近似 5:3
        "steps": 25,
        "cfg_scale": 7.0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/sdapi/v1/txt2img",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            images = result.get("images", [])
            if not images:
                print("[!] SD WebUI 未回傳圖片資料。")
                return None
            img_bytes = base64.b64decode(images[0])
            out_file = RAW_DIR / f"{card_id}.png"
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            with open(out_file, "wb") as f:
                f.write(img_bytes)
            print(f"[✓] 成功由 SD WebUI 生成大圖: {out_file.name}")
            return out_file
    except Exception as e:
        print(f"[!] SD WebUI 請求失敗: {e}")
        return None


def generate_with_gemini(prompt_info: dict, api_key: str) -> Path | None:
    card_id = prompt_info["id"]
    print("[*] 正在透過 Google GenAI (Imagen 3) 生成卡圖...")
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"
    payload = {
        "instances": [{"prompt": prompt_info["positive_prompt"]}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "16:9",
            "outputMimeType": "image/jpeg"
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode("utf-8"))
            preds = res.get("predictions", [])
            if preds and "bytesBase64Encoded" in preds[0]:
                img_data = base64.b64decode(preds[0]["bytesBase64Encoded"])
                out_file = RAW_DIR / f"{card_id}.jpg"
                RAW_DIR.mkdir(parents=True, exist_ok=True)
                with open(out_file, "wb") as f:
                    f.write(img_data)
                print(f"[✓] 成功由 Imagen 生成大圖: {out_file.name}")
                return out_file
    except Exception as e:
        print(f"[!] Google Imagen 生成失敗: {e}")
    return None


def generate_with_openai(prompt_info: dict, api_key: str) -> Path | None:
    card_id = prompt_info["id"]
    print("[*] 正在透過 OpenAI DALL-E 3 生成卡圖...")
    import urllib.request
    url = "https://api.openai.com/v1/images/generations"
    payload = {
        "model": "dall-e-3",
        "prompt": prompt_info["positive_prompt"],
        "n": 1,
        "size": "1792x1024",
        "response_format": "b64_json"
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res = json.loads(response.read().decode("utf-8"))
            b64_str = res["data"][0]["b64_json"]
            out_file = RAW_DIR / f"{card_id}.png"
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            with open(out_file, "wb") as f:
                f.write(base64.b64decode(b64_str))
            print(f"[✓] 成功由 DALL-E 生成大圖: {out_file.name}")
            return out_file
    except Exception as e:
        print(f"[!] OpenAI DALL-E 生成失敗: {e}")
    return None


def show_missing_summary(prompts: list[dict]):
    missing = []
    completed = []
    for item in prompts:
        cid = item["id"]
        dist_path = DIST_DIR / f"{cid}.avif"
        raw_candidates = [RAW_DIR / f"{cid}{ext}" for ext in [".png", ".jpg", ".jpeg", ".webp"]]
        has_raw = any(p.exists() for p in raw_candidates)
        has_dist = dist_path.exists()

        if has_dist:
            completed.append(item)
        else:
            missing.append((item, has_raw))

    print("=" * 60)
    print(f"卡圖完成度統計：共 {len(prompts)} 張卡片")
    print(f"  ✓ 已完成轉檔 (dist/): {len(completed)} 張")
    print(f"  [-] 尚未完成: {len(missing)} 張")
    print("=" * 60)

    if missing:
        print("\n【尚未完成之卡片清單】:")
        for item, has_raw in missing:
            raw_tag = "[已有 raw 圖，等待轉檔]" if has_raw else "[無原圖]"
            print(f"  - [{item['id']:<4}] {item['name']:<8} ({item['cls']}/{item['kind']}) {raw_tag}")
        print("\n提示：你可以直接在對話中對 Agent 說：「生圖 A1」或「批次生成缺圖卡片」。")


def process_card_flow(card_id: str):
    prompt_info = get_card_prompt(card_id)
    if not prompt_info:
        print(f"[!] 找不到卡片 ID: {card_id}，請檢查 data/cards.toml。")
        return

    cid = prompt_info["id"]
    cname = prompt_info["name"]
    print(f"\n==================================================")
    print(f"  目標卡片: [{cid}] {cname}")
    print(f"  類別: {prompt_info['cls']} · {prompt_info['kind']}")
    print(f"==================================================")

    # 1. 偵測可用的生圖後端
    cdp_ready = check_cdp_browser()
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    sd_ready = check_local_sd_webui()

    generated_path = None
    if cdp_ready:
        generated_path = generate_with_gemini_browser(prompt_info)
    elif sd_ready:
        generated_path = generate_with_sd_webui(prompt_info)
    elif gemini_key:
        generated_path = generate_with_gemini(prompt_info, gemini_key)
    elif openai_key:
        generated_path = generate_with_openai(prompt_info, openai_key)

    # 2. 若自動後端生成成功，直接呼叫後製腳本
    if generated_path:
        print(f"\n[*] 正在呼叫後製轉檔腳本 process_cards.py {cid} ...")
        subprocess.run([sys.executable, str(PROCESS_SCRIPT), cid], check=True)
        print(f"[✓] 全流程完成！請開啟 preview.html 預覽。")
        return

    # 3. 若無外部 API，輸出引導提示
    print("[*] 目前未偵測到外部生圖 API 或本機 SD WebUI。")
    print("\n▶ Positive Prompt:\n" + prompt_info["positive_prompt"])
    print("\n▶ Negative Prompt:\n" + prompt_info["negative_prompt"])
    print("\n" + "-" * 50)
    print("💡 如何自動生成卡圖：")
    print("  1. 【最推薦 - Agent 自動生圖】:")
    print(f"     直接在對話框對 Agent 說：「生圖 {cid}」或「幫我生 {cname} 的圖」")
    print("     Agent 會調用內建生圖引擎自動產出原圖並執行 process_cards.py！")
    print("  2. 【使用本機 Stable Diffusion WebUI】:")
    print("     啟動 SD WebUI (加入 --api 參數)，腳本將自動連線 127.0.0.1:7860 生成。")
    print("  3. 【使用 API】:")
    print("     設定環境變數 GEMINI_API_KEY 或 OPENAI_API_KEY 即可全自動生成。")
    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Combo Master Art 卡圖生成客戶端")
    parser.add_argument("card_id", nargs="?", help="卡片 UID (如 A37, E1, C3)")
    parser.add_argument("--missing", action="store_true", help="列出所有尚未完成的卡片清單")
    parser.add_argument("--prompt", action="store_true", help="僅顯示該卡片的提示詞")

    args = parser.parse_args()
    prompts = load_prompts()

    if args.missing or not args.card_id:
        show_missing_summary(prompts)
        if not args.card_id:
            print("\n使用方式：python scripts/generate_cards.py <卡片ID>")
            return

    if args.prompt:
        p = get_card_prompt(args.card_id)
        if p:
            print(f"[{p['id']}] {p['name']} 提示詞：")
            print("▶ Positive:\n" + p["positive_prompt"] + "\n")
            print("▶ Negative:\n" + p["negative_prompt"])
        return

    process_card_flow(args.card_id)


if __name__ == "__main__":
    main()

