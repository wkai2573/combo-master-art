---
name: generate-card-art
description: 自動呼叫生圖引擎並執行後製裁切轉檔流水線，為指定卡片產出卡圖。當使用者說「生圖」、「幫我生圖」、「生 A1 的圖」、「批次生圖」、「生沒生過的圖」時使用。
---

# Generate Card Art Skill

此技能負責串接《連擊大師》卡圖自動生成到後製轉檔的完整流水線。

## 批次生圖防護規則 (重要)

- **單次數量上限**：當使用者要求批次生圖（例如「生沒生過的圖」、「幫我生所有缺圖的卡片」）時，**單次批次最多處理 3～5 張**，切勿一次發起過多張，以免等待時間過長、生成中斷或品質不易把關。
- **階段回報與確認**：每完成一批（3～5 張），必須更新 `preview.html` 並回報當前進度與成品連結，確認使用者滿意畫風後，再詢問是否繼續生成下一批。

## 執行流程

1. **查表與篩選**：
   - 讀取 `data/prompts.json`。
   - 若為「生沒生過的卡片」，檢查 `dist/{id}.avif` 是否存在，挑選尚未完成的目標（批次時取前 3～5 張）。
2. **生圖**：調用 `image-generator` subagent 生成 16:9 橫向卡圖。
3. **搬移原圖**：將產出的圖檔複製至 `raw_images/<id>.jpg`（或 `.png`）。
4. **轉檔後製**：執行 `python scripts/process_cards.py <id>`，輸出 200×120 AVIF 至 `dist/<id>.avif` 並自動更新 `preview.html`。
5. **通知使用者**：提供 `dist/<id>.avif` 與 `preview.html` 預覽，並回報剩餘缺圖數量。

## 版控與資產注意事項

- **素材不入庫**：`raw_images/`、`dist/` 與 `preview.html` 皆已被 `.gitignore` 排除，Agent 執行 git 指令時切勿使用 `-f` 強制加入任何圖片或預覽檔案。
- **成果提交**：本專案 Git 僅追蹤代碼、Prompt 資料庫 (`data/cards.toml`) 與設定。若生圖流程中有調整 prompt，只提交 `data/cards.toml` 與相關配置檔。
