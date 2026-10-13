# 領域文件

工程 skills 在探索程式碼庫時，應如何讀取這個倉庫的領域文件。

## 探索之前，先讀這些

- 倉庫根目錄的 **`GLOSSARY.md`**，或
- 倉庫根目錄的 **`GLOSSARY-MAP.md`**（若存在）：它指向每個情境各一份 `GLOSSARY.md`。閱讀與主題相關的每一份。
- **`docs/adr/`**：閱讀觸及你即將工作區域的 ADR。在多情境倉庫中，也要檢查 `src/<context>/docs/adr/` 中特定情境的決策。

如果這些檔案有任何一個不存在，就**默默繼續**。不要標示它們的缺席；不要預先建議建立它們。`/domain-modeling` skill（透過 `/grill-with-docs` 和 `/improve-codebase-architecture` 觸及）會在術語或決策真的被確定時，延遲建立它們。

## 檔案結構

單一情境倉庫（大多數倉庫）：

```
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

多情境倉庫（根目錄存在 `GLOSSARY-MAP.md`）：

```
/
├── GLOSSARY-MAP.md
├── docs/adr/                          ← 全系統層級的決策
└── src/
    ├── ordering/
    │   ├── GLOSSARY.md
    │   └── docs/adr/                  ← 特定情境的決策
    └── billing/
        ├── GLOSSARY.md
        └── docs/adr/
```

## 使用詞彙表的詞彙

當你的輸出提到某個領域概念時（議題標題、重構提案、假設、測試名稱），使用 `GLOSSARY.md` 中定義的術語。不要漂移到詞彙表明確避免的同義詞。

如果你不需要的概念還不在詞彙表中，那就是一個訊號：要嘛你在發明專案沒在用的語言（重新考慮），要嘛有真正的缺口（把它記下來，留給 `/domain-modeling`）。

## 標示 ADR 衝突

如果你的輸出與既有的 ADR 矛盾，就明確把它浮現出來，而不是默默覆寫：

> _與 ADR-0007（事件溯源的訂單）矛盾，但值得重新開啟，因為……_

