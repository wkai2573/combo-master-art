#!/usr/bin/env python3
"""
卡圖後製裁切與格式轉換器 (process_cards.py)
將 raw_images/ 中的高解析度原圖，自動以「等比縮放 + 置中裁切」方式
調整為 200x100，並使用 ffmpeg 編碼匯出為 dist/{id}.avif，
最後自動更新 preview.html 圖鑑預覽頁。
"""

import sys
import subprocess
import tomllib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "raw_images"
DIST_DIR = BASE_DIR / "dist"
STYLE_FILE = BASE_DIR / "config" / "style_guide.toml"
CARDS_FILE = BASE_DIR / "data" / "cards.toml"
PREVIEW_FILE = BASE_DIR / "preview.html"

SUPPORTED_EXTS = [".png", ".jpg", ".jpeg", ".webp"]


def get_target_resolution() -> tuple[int, int]:
    if STYLE_FILE.exists():
        with open(STYLE_FILE, "rb") as f:
            cfg = tomllib.load(f)
            meta = cfg.get("meta", {})
            return (meta.get("target_width", 200), meta.get("target_height", 100))
    return (200, 100)


def find_raw_image(card_id: str) -> Path | None:
    for ext in SUPPORTED_EXTS:
        candidate = RAW_DIR / f"{card_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def convert_to_avif(input_path: Path, output_path: Path, width: int = 200, height: int = 100) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filter_chain = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vf", filter_chain,
        "-c:v", "libaom-av1",
        "-crf", "28",
        "-still-picture", "1",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] 轉換失敗 ({input_path.name}): {e.stderr.strip()}")
        return False


def generate_preview_html(cards: list, width: int, height: int):
    items_html = []
    for card in cards:
        cid = card["id"]
        cname = card.get("name", "")
        cls = card.get("cls", "")
        kind = card.get("kind", "")
        slot = card.get("slot", "")
        traits = card.get("traits", [])
        subject = card.get("subject", "")
        dist_file = DIST_DIR / f"{cid}.avif"

        tags = []
        if cls: tags.append(cls)
        if kind: tags.append(kind)
        if slot: tags.append(slot)
        if traits: tags.extend(traits)
        tag_str = " · ".join(tags)

        if dist_file.exists():
            preview_snippet = f'<img class="card-img-preview" src="dist/{cid}.avif" alt="{cid}">'
            status_text = f"成品: dist/{cid}.avif"
        else:
            preview_snippet = '<div class="no-img">尚無圖檔</div>'
            status_text = "等待生成"

        items_html.append(f"""
        <div class="card-item">
          <div class="card-header">
            <span class="card-title">{cname}</span>
            <span class="card-id">{cid} ({tag_str})</span>
          </div>
          <div class="preview-box">
            {preview_snippet}
            <span class="img-label">{status_text}</span>
          </div>
          <div class="prompt-box">
            <strong>主體描述:</strong> {subject}
          </div>
        </div>
        """)

    cards_grid_content = "\n".join(items_html)

    html_template = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Combo Master Art - 卡牌圖鑑預覽</title>
  <style>
    :root {{
      --bg: #121418;
      --card-bg: #1e222b;
      --border: #333a47;
      --accent: #d4a373;
      --text: #e6edf3;
      --text-muted: #8b949e;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    header {{
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }}
    h1 {{
      margin: 0 0 8px 0;
      color: var(--accent);
      font-size: 24px;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      background: #2a313d;
      border-radius: 4px;
      font-size: 12px;
      color: var(--text-muted);
      margin-right: 8px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }}
    .card-item {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .card-title {{
      font-size: 16px;
      font-weight: bold;
    }}
    .card-id {{
      color: var(--accent);
      font-family: monospace;
      font-size: 13px;
    }}
    .preview-box {{
      background: #0d1117;
      border: 1px dashed var(--border);
      border-radius: 6px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
    }}
    .card-img-preview {{
      width: {width}px;
      height: {height}px;
      object-fit: cover;
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .img-label {{
      font-size: 11px;
      color: var(--text-muted);
    }}
    .prompt-box {{
      background: #161b22;
      border-radius: 4px;
      padding: 10px;
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.4;
      max-height: 80px;
      overflow-y: auto;
    }}
    .no-img {{
      width: {width}px;
      height: {height}px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #181d24;
      color: var(--text-muted);
      font-size: 12px;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Combo Master Art - 卡牌圖鑑預覽</h1>
    <span class="badge">目標規格: {width} x {height} (.avif)</span>
    <span class="badge">已註冊卡片: {len(cards)} 張</span>
  </header>
  <div class="grid">
    {cards_grid_content}
  </div>
</body>
</html>"""

    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"[*] 圖鑑預覽頁面已自動更新: {PREVIEW_FILE.relative_to(BASE_DIR)}")


def main():
    width, height = get_target_resolution()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    target_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not CARDS_FILE.exists():
        print(f"[!] 找不到卡片資料檔: {CARDS_FILE}")
        return

    with open(CARDS_FILE, "rb") as f:
        cards_data = tomllib.load(f)

    all_cards = cards_data.get("cards", [])
    cards_to_process = all_cards
    if target_id:
        cards_to_process = [c for c in all_cards if c["id"] == target_id]
        if not cards_to_process:
            print(f"[!] 找不到卡片 ID: {target_id}")
            return

    print(f"[*] 準備處理卡圖，目標尺寸: {width}x{height} (.avif)\n")
    processed_count = 0

    for card in cards_to_process:
        cid = card["id"]
        raw_file = find_raw_image(cid)
        dist_file = DIST_DIR / f"{cid}.avif"

        if not raw_file:
            print(f"[-] 跳過 [{cid}] {card.get('name', '')}：尚未在 raw_images/ 找到對應原圖 ({cid}.png / .jpg)")
            continue

        print(f"[+] 正在處理 [{cid}] {card.get('name', '')}: {raw_file.name} -> {dist_file.name} ...")
        success = convert_to_avif(raw_file, dist_file, width, height)
        if success:
            file_size_kb = dist_file.stat().st_size / 1024
            print(f"    ✓ 成功生成！大小: {file_size_kb:.2f} KB ({dist_file.relative_to(BASE_DIR)})")
            processed_count += 1

    print(f"\n[*] 處理完成，共輸出 {processed_count} 張卡圖至: {DIST_DIR.relative_to(BASE_DIR)}")
    generate_preview_html(all_cards, width, height)


if __name__ == "__main__":
    main()
