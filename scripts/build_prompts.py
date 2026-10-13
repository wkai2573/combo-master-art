#!/usr/bin/env python3
"""
提示詞組合器 (build_prompts.py)
讀取 data/cards.toml 與 config/style_guide.toml，
支援依卡片類型 (kind: move / equip / character / ex / buff) 混入專屬構圖視角，
組裝出精確的生圖 Prompt。
"""

import sys
import json
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CARDS_FILE = BASE_DIR / "data" / "cards.toml"
STYLE_FILE = BASE_DIR / "config" / "style_guide.toml"
PROMPTS_OUT = BASE_DIR / "data" / "prompts.json"


def load_toml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"找不到檔案: {path}")
    with open(path, "rb") as f:
        return tomllib.load(f)


def build_card_prompt(card: dict, style_cfg: dict) -> dict:
    style = style_cfg.get("style", {})
    kind = card.get("kind", "move")

    # 依卡片種類選取專屬構圖詞
    composition_key = f"composition_{kind}"
    composition = style.get(composition_key) or style.get("composition_move", "")

    # 組合正向提示詞
    prompt_segments = [
        card.get("subject", "").strip(),
        card.get("details", "").strip(),
        style.get("aesthetic", "").strip(),
        style.get("lighting", "").strip(),
        style.get("colors", "").strip(),
        style.get("atmosphere", "").strip(),
        composition.strip(),
    ]
    positive_prompt = ", ".join(seg for seg in prompt_segments if seg)
    negative_prompt = style.get("negative_prompt", "").strip()

    return {
        "id": card["id"],
        "name": card.get("name", ""),
        "kind": kind,
        "cls": card.get("cls", ""),
        "slot": card.get("slot", ""),
        "traits": card.get("traits", []),
        "text": card.get("text", ""),
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "target_output": f"{card['id']}.avif",
    }


def main():
    cards_data = load_toml(CARDS_FILE)
    style_data = load_toml(STYLE_FILE)

    cards = cards_data.get("cards", [])
    if not cards:
        print("[!] cards.toml 中沒有任何卡片資料。")
        return

    results = []
    theme = style_data.get("meta", {}).get("theme", "預設")
    aspect = style_data.get("meta", {}).get("aspect_ratio", "5:3")
    print(f"[*] 載入成功：共 {len(cards)} 張卡片，主題「{theme}」，比例「{aspect}」\n")

    for card in cards:
        item = build_card_prompt(card, style_data)
        results.append(item)
        tags = []
        if item["cls"]:
            tags.append(item["cls"])
        if item["kind"]:
            tags.append(item["kind"])
        if item["slot"]:
            tags.append(item["slot"])
        tag_str = f" ({'/'.join(tags)})" if tags else ""

        print(f"===== [{item['id']}] {item['name']}{tag_str} =====")
        print(f"▶ Positive Prompt:\n  {item['positive_prompt']}\n")
        print(f"▶ Negative Prompt:\n  {item['negative_prompt']}\n")

    # 將組合結果輸出成 json 備查
    with open(PROMPTS_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[*] 已輸出完整提示詞列表至: {PROMPTS_OUT.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
