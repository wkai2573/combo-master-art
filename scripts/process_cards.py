#!/usr/bin/env python3
"""
卡圖後製裁切與格式轉換器 (process_cards.py)
將 raw_images/ 中的高解析度原圖，自動以「等比縮放 + 置中裁切」方式
調整為 200x100，並使用 ffmpeg 編碼匯出為 dist/{id}.avif，
最後自動更新 preview.html 圖鑑預覽頁。
"""

import sys
import io
import base64
import subprocess
import tomllib
from pathlib import Path
from typing import Optional

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


def get_card_data_uris(cid: str) -> tuple[Optional[str], Optional[str]]:
    """
    回傳 (avif_data_uri, jpeg_data_uri)。
    使用 Base64 內嵌，讓 preview.html 100% 獨立，在任何瀏覽器或 IDE 內建 Webview 中皆可直接顯示圖片。
    """
    avif_file = DIST_DIR / f"{cid}.avif"
    raw_file = find_raw_image(cid)

    avif_uri = None
    if avif_file.exists():
        try:
            b64 = base64.b64encode(avif_file.read_bytes()).decode("ascii")
            avif_uri = f"data:image/avif;base64,{b64}"
        except Exception:
            pass

    jpeg_uri = None
    if raw_file and raw_file.exists():
        try:
            from PIL import Image
            with Image.open(raw_file) as im:
                im = im.convert("RGB")
                im.thumbnail((400, 240), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=82, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                jpeg_uri = f"data:image/jpeg;base64,{b64}"
        except Exception:
            pass

    return avif_uri, jpeg_uri


CLS_COLORS = {
    "劍士": "#e63946",
    "弓箭手": "#2a9d8f",
    "法師": "#8338ec",
    "盜賊": "#0077b6",
    "商人": "#e09f3e",
    "狂戰士": "#c1121f",
    "武僧": "#f77f00",
    "共用": "#6c757d",
}

KIND_LABELS = {
    "character": "角色",
    "move": "招式",
    "equip": "裝備",
    "ex": "Ex狀態",
    "buff": "增益",
}


def generate_preview_html(cards: list, width: int, height: int):
    items_html = []
    done_count = 0

    for card in cards:
        cid = card["id"]
        cname = card.get("name", "")
        cls = card.get("cls", "共用")
        kind = card.get("kind", "move")
        slot = card.get("slot", "")
        traits = card.get("traits", [])
        subject = card.get("subject", "")
        text = card.get("text", "")
        dist_file = DIST_DIR / f"{cid}.avif"

        avif_uri, jpeg_uri = get_card_data_uris(cid)
        has_img = (avif_uri is not None) or (jpeg_uri is not None)
        if has_img:
            done_count += 1

        cls_color = CLS_COLORS.get(cls, "#6c757d")
        kind_label = KIND_LABELS.get(kind, kind)

        tags_html = [f'<span class="badge" style="background:{cls_color}33;color:{cls_color};border:1px solid {cls_color}66;">{cls}</span>']
        tags_html.append(f'<span class="badge" style="background:#263238;color:#90a4ae;">{kind_label}</span>')
        if slot:
            tags_html.append(f'<span class="badge" style="background:#212529;color:#adb5bd;">{slot}</span>')
        for t in traits:
            tags_html.append(f'<span class="badge" style="background:#1b263b;color:#778da9;">{t}</span>')
        tags_str = "".join(tags_html)

        if has_img:
            img_src = jpeg_uri if jpeg_uri else avif_uri
            file_size_kb = dist_file.stat().st_size / 1024 if dist_file.exists() else 0
            size_badge = f"{file_size_kb:.1f} KB (.avif)" if file_size_kb > 0 else "已就緒"
            escaped_text = text.replace('\n', '<br>').replace("'", "&#39;")
            escaped_subj = subject.replace("'", "&#39;")
            preview_snippet = f"""
            <picture class="card-picture">
              {f'<source srcset="{avif_uri}" type="image/avif">' if avif_uri else ''}
              <img class="card-img-preview" src="{img_src}" alt="{cid} {cname}" loading="lazy" onclick="openLightbox('{cid}', '{cname}', '{cls}', '{kind_label}', this.currentSrc || this.src, '{escaped_text}', '{escaped_subj}')">
            </picture>
            """
            status_html = f'<span class="status-done">✓ {size_badge}</span>'
        else:
            preview_snippet = f'<div class="no-img"><span>尚無圖檔</span><small style="color:#555;font-size:11px;">等待生成</small></div>'
            status_html = '<span class="status-pending">⏳ 待生成</span>'

        text_display = f'<div class="card-effect"><strong>效果:</strong> {text}</div>' if text else ""
        escaped_search = f"{cid} {cname} {cls} {kind} {kind_label} {' '.join(traits)} {subject}".lower()

        items_html.append(f"""
        <div class="card-item" data-id="{cid}" data-kind="{kind}" data-status="{'done' if has_img else 'pending'}" data-search="{escaped_search}">
          <div class="card-header">
            <div>
              <span class="card-title">{cname}</span>
              <span class="card-id">[{cid}]</span>
            </div>
            {status_html}
          </div>
          <div class="tag-row">
            {tags_str}
          </div>
          <div class="preview-box">
            {preview_snippet}
          </div>
          {text_display}
          <div class="prompt-box" title="{subject}">
            <strong>提示詞焦點:</strong> {subject}
          </div>
        </div>
        """)

    cards_grid_content = "\n".join(items_html)
    total_cards = len(cards)
    pending_count = total_cards - done_count
    progress_pct = (done_count / total_cards * 100) if total_cards > 0 else 0

    html_template = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Combo Master Art - 卡牌圖鑑預覽 (含內嵌圖片)</title>
  <style>
    :root {{
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --border-hover: #58a6ff;
      --accent: #d4a373;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --success: #2ea043;
      --warning: #d29922;
    }}
    * {{
      box-sizing: border-box;
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
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }}
    .header-top {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }}
    h1 {{
      margin: 0;
      color: var(--accent);
      font-size: 26px;
      letter-spacing: 0.5px;
    }}
    .progress-section {{
      background: #1c2128;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 18px;
      margin-bottom: 20px;
    }}
    .progress-stats {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 500;
    }}
    .progress-bar-bg {{
      background: #30363d;
      height: 10px;
      border-radius: 5px;
      overflow: hidden;
    }}
    .progress-bar-fill {{
      background: linear-gradient(90deg, #2ea043, #56d364);
      height: 100%;
      width: {progress_pct:.1f}%;
      transition: width 0.3s ease;
    }}
    .controls-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}
    .filter-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .filter-btn {{
      background: #21262d;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-btn:hover {{
      background: #30363d;
      color: var(--text);
    }}
    .filter-btn.active {{
      background: var(--accent);
      color: #121418;
      font-weight: bold;
      border-color: var(--accent);
    }}
    .search-box {{
      position: relative;
      min-width: 240px;
    }}
    .search-box input {{
      width: 100%;
      background: #21262d;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-box input:focus {{
      border-color: var(--accent);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 18px;
    }}
    .card-item {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }}
    .card-item:hover {{
      border-color: #484f58;
      transform: translateY(-2px);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .card-title {{
      font-size: 16px;
      font-weight: bold;
      color: #fff;
    }}
    .card-id {{
      color: var(--accent);
      font-family: monospace;
      font-size: 13px;
      margin-left: 6px;
    }}
    .tag-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
    }}
    .status-done {{
      color: #3fb950;
      font-size: 11px;
      font-weight: bold;
      background: rgba(46, 160, 67, 0.15);
      padding: 2px 8px;
      border-radius: 12px;
      border: 1px solid rgba(46, 160, 67, 0.3);
    }}
    .status-pending {{
      color: #e3b341;
      font-size: 11px;
      background: rgba(210, 153, 34, 0.15);
      padding: 2px 8px;
      border-radius: 12px;
      border: 1px solid rgba(210, 153, 34, 0.3);
    }}
    .preview-box {{
      background: #090d13;
      border: 1px solid #21262d;
      border-radius: 6px;
      padding: 8px;
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .card-picture {{
      display: block;
      width: {width}px;
      height: {height}px;
      max-width: 100%;
    }}
    .card-img-preview {{
      width: {width}px;
      height: {height}px;
      object-fit: cover;
      border-radius: 4px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.6);
      border: 1px solid rgba(255,255,255,0.08);
      cursor: zoom-in;
      transition: filter 0.2s, transform 0.2s;
    }}
    .card-img-preview:hover {{
      filter: brightness(1.08);
      transform: scale(1.02);
    }}
    .no-img {{
      width: {width}px;
      height: {height}px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: #111419;
      color: var(--text-muted);
      font-size: 12px;
      border-radius: 4px;
      border: 1px dashed #30363d;
    }}
    .card-effect {{
      font-size: 11.5px;
      color: #c9d1d9;
      background: #0d1117;
      padding: 6px 10px;
      border-radius: 4px;
      border-left: 3px solid var(--accent);
      line-height: 1.4;
      white-space: pre-line;
    }}
    .prompt-box {{
      background: #10141a;
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.4;
      max-height: 60px;
      overflow-y: auto;
      border: 1px solid #21262d;
    }}
    /* Lightbox Modal */
    .modal-overlay {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(6px);
      z-index: 1000;
      justify-content: center;
      align-items: center;
      padding: 20px;
    }}
    .modal-overlay.open {{
      display: flex;
    }}
    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      max-width: 680px;
      width: 100%;
      overflow: hidden;
      box-shadow: 0 10px 40px rgba(0,0,0,0.8);
      display: flex;
      flex-direction: column;
    }}
    .modal-img-wrap {{
      background: #000;
      text-align: center;
      padding: 10px;
    }}
    .modal-img-wrap img {{
      max-width: 100%;
      height: auto;
      max-height: 380px;
      object-fit: contain;
      border-radius: 6px;
    }}
    .modal-info {{
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .modal-close-btn {{
      align-self: flex-end;
      background: #30363d;
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-top">
      <h1>Combo Master Art - 卡牌圖鑑預覽</h1>
      <span class="badge" style="background:#21262d;color:#8b949e;font-size:12px;padding:6px 12px;">規格: {width} × {height} (.avif) · 100% 內嵌圖片獨立預覽</span>
    </div>

    <div class="progress-section">
      <div class="progress-stats">
        <span>全套進度：<strong style="color:var(--accent);">{done_count}</strong> / {total_cards} 張卡片</span>
        <span>完成度：<strong style="color:#56d364;">{progress_pct:.1f}%</strong></span>
      </div>
      <div class="progress-bar-bg">
        <div class="progress-bar-fill"></div>
      </div>
    </div>

    <div class="controls-row">
      <div class="filter-pills">
        <button class="filter-btn active" onclick="setFilter('all', this)">全部 ({total_cards})</button>
        <button class="filter-btn" onclick="setFilter('done', this)">已生成 ({done_count})</button>
        <button class="filter-btn" onclick="setFilter('pending', this)">待生成 ({pending_count})</button>
        <button class="filter-btn" onclick="setFilter('character', this)">角色卡 (7)</button>
        <button class="filter-btn" onclick="setFilter('move', this)">招式卡 (37)</button>
        <button class="filter-btn" onclick="setFilter('equip', this)">裝備卡 (8)</button>
      </div>
      <div class="search-box">
        <input type="text" id="searchInput" placeholder="搜尋卡名、ID、職業..." oninput="handleSearch()">
      </div>
    </div>
  </header>

  <div class="grid" id="cardsGrid">
    {cards_grid_content}
  </div>

  <div class="modal-overlay" id="lightboxModal" onclick="closeLightbox(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
      <div class="modal-img-wrap">
        <img id="modalImg" src="" alt="Card Art">
      </div>
      <div class="modal-info">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <h2 id="modalTitle" style="margin:0;font-size:20px;color:var(--accent);"></h2>
          <button class="modal-close-btn" onclick="closeLightbox()">關閉 (Esc)</button>
        </div>
        <div id="modalTags" style="font-size:13px;color:var(--text-muted);"></div>
        <div id="modalEffect" style="font-size:13px;background:#0d1117;padding:10px;border-radius:6px;border-left:3px solid var(--accent);white-space:pre-line;"></div>
        <div id="modalSubject" style="font-size:12px;color:var(--text-muted);background:#10141a;padding:8px 10px;border-radius:4px;"></div>
      </div>
    </div>
  </div>

  <script>
    let currentFilter = 'all';

    function setFilter(filter, btn) {{
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilters();
    }}

    function handleSearch() {{
      applyFilters();
    }}

    function applyFilters() {{
      const query = document.getElementById('searchInput').value.trim().toLowerCase();
      const cards = document.querySelectorAll('.card-item');

      cards.forEach(card => {{
        const status = card.getAttribute('data-status');
        const kind = card.getAttribute('data-kind');
        const search = card.getAttribute('data-search') || '';

        let matchFilter = true;
        if (currentFilter === 'done') matchFilter = (status === 'done');
        else if (currentFilter === 'pending') matchFilter = (status === 'pending');
        else if (currentFilter === 'character') matchFilter = (kind === 'character');
        else if (currentFilter === 'move') matchFilter = (kind === 'move');
        else if (currentFilter === 'equip') matchFilter = (kind === 'equip');

        const matchQuery = !query || search.includes(query);

        if (matchFilter && matchQuery) {{
          card.style.display = '';
        }} else {{
          card.style.display = 'none';
        }}
      }});
    }}

    function openLightbox(id, name, cls, kind, imgSrc, effect, subject) {{
      document.getElementById('modalImg').src = imgSrc;
      document.getElementById('modalTitle').textContent = name + ' [' + id + ']';
      document.getElementById('modalTags').textContent = cls + ' · ' + kind;
      document.getElementById('modalEffect').innerHTML = effect ? '<strong>效果:</strong> ' + effect : '';
      document.getElementById('modalEffect').style.display = effect ? 'block' : 'none';
      document.getElementById('modalSubject').innerHTML = '<strong>主體焦點:</strong> ' + subject;
      document.getElementById('lightboxModal').classList.add('open');
    }}

    function closeLightbox(e) {{
      document.getElementById('lightboxModal').classList.remove('open');
      document.getElementById('modalImg').src = '';
    }}

    document.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeLightbox();
    }});
  </script>
</body>
</html>"""

    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"[*] 圖鑑預覽頁面已自動更新 (含內嵌圖片): {PREVIEW_FILE.relative_to(BASE_DIR)}")


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
