# Combo Master Art - Agent 指令規範

本專案專門管理與自動產出《連擊大師》卡牌卡圖。

## 自動生圖流水線 (Agent Auto-Gen Pipeline)

當使用者在對話中提出以下請求時：
- 「生圖 <ID>」（例如：生圖 A1、生圖 E2）
- 「幫我生 <ID> 的卡圖」
- 「幫我生一張沒生過的圖」
- 「幫我生成所有缺圖的卡片」/「批次生圖」

### ⚠️ 批次生圖原則（重要約束）
- **單次數量控管**：批次生圖時，**一次不要處理太多張，單次建議以 3～5 張為限**。
- **避免阻塞**：過多圖片同時或連續生成容易造成等待時間過長、模型限制或失敗率上升。
- **分批檢視**：每完成一批（3～5 張），應先回報成果與 [preview.html](preview.html) 預覽，讓使用者確認畫風與品質後，再詢問是否繼續下一批。

---

### 標準 5 步驟流水線

1. **取得提示詞**：
   - 讀取 `data/prompts.json`（若不存在則先執行 `python scripts/build_prompts.py`）。
   - 若為「生沒生過的卡片」，檢查 `dist/{id}.avif` 是否存在，篩選出缺圖的卡片清單（取前 3～5 張）。

2. **調用生圖 Subagent**：
   - 使用 `invoke_subagent` 呼叫 `image-generator`。
   - 角色設定：`Card Art Image Generator`。
   - 比例設定：`16:9`（橫向，最接近 5:3 目標比例）。
   - Prompt 傳入該卡片之 Positive Prompt。

3. **放置原圖**：
   - 從 Subagent 回傳的圖片路徑，複製/存檔至專案的 `raw_images/<ID>.jpg`（或 `.png`）。

4. **後製轉檔**：
   - 透過 `run_command` 執行：
     ```bash
     python scripts/process_cards.py <ID>
     ```
   - 系統會透過 ffmpeg 自動等比縮放 + 置中裁切輸出 `dist/<ID>.avif`（200×120），並自動更新 `preview.html`。

5. **回報完成**：
   - 向使用者回報生成結果，並附上 `dist/<ID>.avif` 與 `preview.html` 的檔案連結，標註剩餘缺圖進度。

---

## Agent skills

### 議題追蹤系統

議題存放在本地 markdown 檔案（`.scratch/`）。請見 `docs/agents/issue-tracker.md`。

### 領域文件

單一情境（根目錄 `GLOSSARY.md` + `docs/adr/`）。請見 `docs/agents/domain.md`。
