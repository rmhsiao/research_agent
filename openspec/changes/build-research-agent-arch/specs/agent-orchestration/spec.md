## ADDED Requirements

### Requirement: 協調者統籌一次研究流程

系統 SHALL 提供一個協調者 agent，作為規劃整條研究流程「下一步往哪走」的決策者，架在
LangGraph 圖上實作（graph 是底座，協調者是居中決策的節點）。它接收研究查詢與 session
識別碼，自行決定步驟的順序與方向：把查詢拆解／改寫成一組子查詢、平行委派給多個 web
search agent，判斷收集的資料是否足夠，足夠時委派 report generate agent 並回傳最終報告。

#### Scenario: 查詢走完整條流程

- **WHEN** 協調者收到某個既有 session 的查詢
- **THEN** 它先把查詢拆成子查詢並平行搜尋、彙整後再呼叫 report generate agent，並
  回傳一份引用了搜尋結果的 HTML 報告

### Requirement: 協調者拆解查詢並平行委派搜尋

協調者 SHALL 用較強的模型把研究查詢拆解／改寫成一組子查詢，並對每個子查詢平行委派
一個 web search agent；各分支的搜尋結果 SHALL 合併進共用的累積結果，供後續判斷與
報告生成使用。

#### Scenario: 多子查詢並行搜尋並合併

- **WHEN** 協調者把一個查詢拆成多個子查詢
- **THEN** 每個子查詢各起一個 web search agent 平行搜尋，所有分支的 finding 合併進
  同一份累積結果，沒有任何一個分支的結果被覆蓋

### Requirement: 資料不足時改寫查詢重搜（有上限）

協調者 SHALL 在彙整搜尋結果後判斷資料是否足夠：足夠則進入報告生成、不再搜尋；不足則
依缺口改寫子查詢、再搜一輪。重搜 SHALL 受一個上限約束，達到上限即以現有結果進入報告
生成，不無限折返。

#### Scenario: 資料足夠就停止搜尋

- **WHEN** 協調者判定累積的資料已足夠
- **THEN** 它直接進入報告生成，不再發動更多搜尋

#### Scenario: 資料不足則改寫重搜

- **WHEN** 協調者判定資料不足且尚未達重搜上限
- **THEN** 它依缺口改寫子查詢、再平行搜尋一輪，新結果併入累積結果

#### Scenario: 達到重搜上限即停

- **WHEN** 重搜次數達到上限但資料仍被判為不足
- **THEN** 協調者停止搜尋、以現有結果進入報告生成，而非無限折返

### Requirement: 圖狀態承載流程上下文

圖狀態 SHALL 承載原始查詢、session 識別碼、當輪的子查詢、跨平行分支累積的搜尋結果、
重搜輪數與已生成的報告，讓每個節點都能讀到自己需要的資料、並把產出寫回共用狀態；累積
的搜尋結果 SHALL 以 reducer 合併，使並行分支的寫入不互相覆蓋。

#### Scenario: 搜尋結果累積在圖狀態

- **WHEN** 多個 web search agent 平行完成
- **THEN** 各自整理出的結果都被合併寫入圖狀態的累積結果，且 report generate agent
  讀得到全部

### Requirement: 協調者整合 session 記憶

協調者 SHALL 在拆解查詢前讀取該 session 的近期上下文以延續對話，並在流程結束後把該輪
（查詢與回傳的報告）追加進該 session 的完整聊天紀錄。

#### Scenario: 延續既有 session 的對話

- **WHEN** 協調者收到某既有 session 的後續查詢
- **THEN** 它在拆解查詢時參考該 session 的近期上下文，流程結束後把該輪追加進紀錄

### Requirement: 子 agent 失敗會往上拋

協調者 SHALL 在子 agent 因基礎設施錯誤（LLM 或搜尋後端無法連線）而失敗時，把錯誤往上
拋，而不是悄悄改用空的或降級的結果；任一平行搜尋分支失敗即讓該次協調者流程失敗。

#### Scenario: 搜尋後端無法連線

- **WHEN** 某個 web search agent 因搜尋後端無法連線而失敗
- **THEN** 該次協調者流程拋出錯誤、讓呼叫端知道失敗，而不是產出一份空報告
