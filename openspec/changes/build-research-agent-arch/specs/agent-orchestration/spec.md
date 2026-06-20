## ADDED Requirements

### Requirement: 協調者統籌一次研究流程

系統 SHALL 提供一個以 LangGraph 圖實作的協調者 agent，接收研究查詢與
session 識別碼，依序委派給 web search agent 與 report generate agent，並回傳
最終報告。協調者 SHALL 自行判斷已收集的資料是否足夠、可進入報告生成。

#### Scenario: 查詢走完整條流程

- **WHEN** 協調者收到某個既有 session 的查詢
- **THEN** 它先呼叫 web search agent、再呼叫 report generate agent，並回傳一份
  引用了搜尋結果的 HTML 報告

#### Scenario: 資料足夠就停止搜尋

- **WHEN** web search agent 回傳的資料已被協調者判定為足夠
- **THEN** 協調者直接進入報告生成，不再發動更多搜尋

### Requirement: 圖狀態承載流程上下文

圖狀態 SHALL 承載原始查詢、session 識別碼、累積的搜尋結果與已生成的報告，讓每個
agent 都能讀到自己需要的資料、並把產出寫回共用狀態。

#### Scenario: 搜尋結果累積在圖狀態

- **WHEN** web search agent 完成
- **THEN** 它整理出的結果被寫入圖狀態，且 report generate agent 讀得到

### Requirement: 子 agent 失敗會往上拋

協調者 SHALL 在子 agent 因基礎設施錯誤（LLM 或搜尋後端無法連線）而失敗時，把錯誤
往上拋，而不是悄悄改用空的或降級的結果。

#### Scenario: 搜尋後端無法連線

- **WHEN** web search agent 因搜尋後端無法連線而失敗
- **THEN** 該次協調者流程拋出錯誤、讓呼叫端知道失敗，而不是產出一份空報告
