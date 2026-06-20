# 專案協作規範

## OpenSpec 變更的開發流程

本專案以 OpenSpec(`openspec/`)做規格驅動開發。每個 change 怎麼切 PR，先看它的範圍：

- **範圍小**：一個 PR 同時處理 spec 與實作即可，不必拆。
- **範圍大**：

  1. 規格先落地 —— proposal/design/specs/tasks 先以一個 docs PR 合進 `main`， 之後的實作分支都從 `main` 開
  2. 接著依 `tasks.md` 的 `## N.` 群組，逐一開 `feature/<name>` → PR → 由開發者 review、合併，一個群組一個 PR

  注意實作時邊做邊把對應的 `- [ ]` 勾成 `- [x]`

不論大小，**archive 都留到最後**：整個 change 的實作都合併後，再以一個獨立的小 commit 或 PR 跑
`openspec archive <change>`(把 change 搬進 `openspec/changes/archive/`，並將 delta
spec 併進 `openspec/specs/`)。實作途中不 archive。

> spec 只描述「系統做什麼」;上述「怎麼切 PR、何時 archive」屬團隊流程，不寫進`specs/` 或 `design.md`。

## 測試

每個實作 PR 須針對主要路徑與關鍵邊緣案例撰寫適量單元測試，涵蓋正常流程、預期的失敗
或拒絕、輸入驗證與例外傳播。不需窮舉，也不設覆蓋率門檻。
