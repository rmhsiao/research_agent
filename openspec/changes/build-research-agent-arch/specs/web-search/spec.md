## ADDED Requirements

### Requirement: web search agent 回傳固定結構化的結果

系統 SHALL 提供一個 web search agent，接收協調者給的查詢，透過設定好的搜尋後端上網搜尋，
並以**固定結構化的 `Findings`**（型別化 schema）回傳給協調者：一組 finding 項目，每項含
摘要與來源出處（標題／網址）。回應形狀 SHALL 維持穩定，不因有無結果而改變型別。

#### Scenario: 查詢產出結構化結果

- **WHEN** web search agent 收到查詢
- **THEN** 它回傳一個 `Findings` 物件，內含多個 finding 項目，每項都帶摘要與來源
  （標題／網址）

#### Scenario: 查無結果

- **WHEN** 搜尋後端對該查詢沒有任何結果
- **THEN** agent 回傳一個 finding 項目為空的 `Findings`（同一型別），而不捏造來源

### Requirement: 搜尋後端錯誤會往上拋

web search agent SHALL 在設定好的搜尋後端回傳錯誤或無法連線時把錯誤往上拋，而不是
當作搜尋成功、回傳空結果。

#### Scenario: 後端回傳錯誤

- **WHEN** 搜尋後端回應錯誤或逾時
- **THEN** web search agent 拋出基礎設施錯誤，與「查無結果」明確區分
