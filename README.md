# Combo Master Art (卡牌卡圖自動化流水線)

本專案專門用於管理與自動產出《連擊大師》(Combo Master) 遊戲卡圖。
透過「卡片資料庫（TOML）」+「統一風格指南（Style Guide）」驅動 AI 繪製卡圖，並自動裁切、縮放為符合遊戲卡面視窗的 **200×120 (5:3) `.avif`** 格式。

---

## 專案目錄結構

```text
combo-master-art/
├── data/
│   ├── cards.toml          # [核心] 卡片生圖資料庫 (含 51 張卡片及專屬 Prompt)
│   ├── cards.toml.bak      # 原始備份檔
│   └── prompts.json        # 自動編譯出的完整生圖提示詞檔
├── config/
│   └── style_guide.toml    # [視覺規範] 統一風格指南 (5:3 比例、多構圖分流)
├── raw_images/             # AI 產出的高解析度原始圖 (支援 .png / .jpg / .webp)
├── dist/                   # [最終成品] 200x120 .avif 格式卡圖 (以 UID 命名，如 A37.avif)
├── scripts/
│   ├── import_cards.py     # 自遊戲專案增量匯入卡片資料 (支援 --force)
│   ├── build_prompts.py    # 提示詞組裝腳本 (依 kind 混入動態/靜物/肖像構圖)
│   └── process_cards.py    # 批次裁切縮放與 AVIF 轉檔腳本 (自動產出 preview.html)
├── preview.html            # 本地卡圖預覽與圖鑑頁面
└── README.md               # 本指南
```

---

## 核心資料模型 (`data/cards.toml`)

全面對齊《連擊大師》領域架構：
```toml
[[cards]]
id = "A37"                    # 永久編號 UID (A=招式, E=裝備, C=角色, X=Ex狀態卡)
name = "魅影射擊"              # 遊戲中文名稱
kind = "move"                 # move | equip | character | ex
cls = "弓箭手"                # 職業：劍士 | 盜賊 | 商人 | 弓箭手 | 法師 | 共用
slot = "武器"                 # (僅裝備) 武器 | 防具 | 飾品
traits = ["攻擊"]             # 特徵標籤清單
text = "[追]：我方 +0+4。"     # 遊戲效果原文 (參考脈絡)
subject = "an ethereal archer in motion releasing a phantom translucent arrow..."
details = "ghostly cyan glow, blurred motion trail, dynamic archery release pose..."
```

---

## 標準操作工作流

### 1. 增量同步遊戲卡表
當遊戲本體有卡表更新或新增卡片時：
```bash
python scripts/import_cards.py
```
> **增量保護**：預設會比對 `id`，保留所有現有卡片已修改的 Prompt，只自動補齊新加入的卡片。若需全量重構可加上 `--force`。

### 2. 編譯生圖提示詞
```bash
python scripts/build_prompts.py
```
系統會根據卡片種類（招式採動態打擊視角、裝備採器物特寫、角色採英雄肖像），自動將 `style_guide.toml` 的畫風與各卡片的 `subject`/`details` 組裝成正向與負向 Prompt，並存入 `data/prompts.json`。

### 3. 生圖與轉檔 (兩種方式)

#### 方法 A：對話呼叫 Agent 全自動生成（最推薦）
直接在 Antigravity 聊天框告訴 Agent：
- `生圖 A37` 或 `幫我生 A37 的圖`
- `幫我生一張沒生過的圖`
- `幫我生接下來 3 張卡片`（**建議單次以 3～5 張為限**，方便分批檢視品質與避免超時）
Agent 會全自動讀取 Prompt、調用內建生圖引擎、將原圖存入 `raw_images/` 並執行轉檔腳本產出 `dist/`。

#### 方法 B：使用腳本或外部 AI 工具
1. 查詢缺圖與提示詞：
   ```bash
   # 查看尚未完成之卡片列表
   python scripts/generate_cards.py --missing

   # 查看單張卡片提示詞 (若設定好 API Key 或本機 SD WebUI 亦可直接自動生成)
   python scripts/generate_cards.py A37
   ```
2. 將生成的圖片存入 `raw_images/`，檔名使用卡片 ID（例如 `A37.png`、`E1.jpg`）。
3. 執行轉檔腳本：
   ```bash
   python scripts/process_cards.py A37
   ```

### 4. 預覽圖鑑
在瀏覽器打開 `preview.html` 即可直觀預覽所有卡圖與提示詞狀態！

---

## 常用指令速查

| 操作 | 指令 | 說明 |
| :--- | :--- | :--- |
| **Agent 自動生圖** | 對話中輸入 `生圖 A37` | 由 Agent 調用內建引擎全自動生圖+轉檔 |
| **同步遊戲卡表** | `python scripts/import_cards.py` | 增量比對並匯入卡片，保留現有 Prompt |
| **強制全量覆蓋** | `python scripts/import_cards.py --force` | 強制以內建設定全量重寫 cards.toml |
| **編譯所有提示詞** | `python scripts/build_prompts.py` | 讀取 cards.toml 生成 prompts.json |
| **生圖客戶端/查缺** | `python scripts/generate_cards.py --missing` | 列出所有缺圖卡片並引導生圖 |
| **批次後製與轉檔** | `python scripts/process_cards.py` | 將 raw_images/ 轉為 dist/{id}.avif (200x120) |
| **處理指定卡片轉檔** | `python scripts/process_cards.py A37` | 僅處理指定 UID 的卡圖後製 |

---

## Git 版控與素材管理規範

1. **AI 原圖管理 (`raw_images/`)**：
   - AI 生成的高解析度原圖（單張約 1MB）**由 `.gitignore` 自動忽略**，避免 Git 儲存庫體積急遽膨脹。
   - `raw_images/` 僅作為本機快取與轉檔來源，目錄透過 `.gitkeep` 保留。

2. **交付成品 (`dist/`)**：
   - 轉檔後的 200×120 `.avif` 卡圖（單張僅 2～6KB）以及 `preview.html` 納入版控，作為遊戲本體直接引用的交付成果。

3. **卡圖定案後清理 Git 歷史舊圖存檔 (SOP)**：
   - 在卡圖探索與試作期間，可正常 commit 疊代更新。
   - 當整套（51 張）卡圖風格確認「完全定案」時，可執行以下指令將歷史壓扁為正式發布版，徹底回收試作期間累積的舊圖 blob：
     ```bash
     git checkout --orphan temp-clean
     git add -A
     git commit -m "chore: production release with all finalized cards"
     git branch -D main
     git branch -m main
     git gc --prune=now --aggressive
     ```
   - 若為平時單張微調，可直接使用 `git commit --amend --no-edit` 覆蓋最近一次提交。

