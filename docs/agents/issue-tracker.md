# 議題追蹤系統：本地 Markdown

這個倉庫的議題與規格以 markdown 檔案的形式存放在 `.scratch/`。

## 慣例

- 每個功能一個目錄：`.scratch/<feature-slug>/`
- 規格是 `.scratch/<feature-slug>/spec.md`
- 實作議題是每張票券一個檔案，位於 `.scratch/<feature-slug>/issues/<NN>-<slug>.md`，從 `01` 開始編號，絕不使用單一合併的票券檔案
- 分流狀態記錄在每個議題檔案最上方附近的 `Status:` 行（角色字串見 `triage-labels.md`）
- 留言與對話歷史附加在檔案底部的 `## Comments` 標題之下

## 當 skill 說「發佈到議題追蹤系統」

在 `.scratch/<feature-slug>/` 底下建立新檔案（必要時建立目錄）。

## 當 skill 說「取得相關票券」

讀取所參照路徑的檔案。使用者通常會直接傳入路徑或議題編號。

## 尋路操作（Wayfinding operations）

由 `/wayfinder` 使用。**地圖**是一個檔案，每張票券各有一個**子**檔案。

- **地圖**：`.scratch/<effort>/map.md`（備註／目前已做的決策／迷霧的內文）。
- **子票券**：`.scratch/<effort>/issues/NN-<slug>.md`，從 `01` 開始編號，問題寫在內文中。`Type:` 行記錄票券類型（`research`/`prototype`/`grilling`/`task`）；`Status:` 行記錄 `claimed`/`resolved`。
- **阻擋**：最上方附近的一行 `Blocked by: NN, NN`。當它所列出的每個檔案都是 `resolved` 時，票券就是未被阻擋。
- **前沿**：掃描 `.scratch/<effort>/issues/` 中開放、未被阻擋且未被領取的檔案；依編號排第一的勝出。
- **領取**：在任何工作之前，設定 `Status: claimed` 並存檔。
- **解決**：在 `## Answer` 標題之下附加答案，設定 `Status: resolved`，然後把情境指標（要旨 + 連結）附加到 `map.md` 中地圖的「目前已做的決策」。

