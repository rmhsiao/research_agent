## ADDED Requirements

### Requirement: report generate agent 產出 HTML 報告

系統 SHALL 提供一個 report generate agent，接收收集到的結果與原始查詢，加以整理
彙整後，回傳一份可獨立開啟的 HTML 報告給使用者。

#### Scenario: 把結果渲染成 HTML 報告

- **WHEN** report generate agent 收到非空的結果
- **THEN** 它回傳合法 HTML，內含針對查詢整理出的回答，以及所用來源的清單

#### Scenario: 結果為空

- **WHEN** report generate agent 收到空的結果
- **THEN** 它回傳一份說明「查無相關資訊」的 HTML 報告，而不捏造內容
