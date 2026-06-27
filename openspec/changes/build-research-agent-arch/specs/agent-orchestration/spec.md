## ADDED Requirements

### Requirement: 協調者統籌研究流程

系統 SHALL 提供一個協調者 agent，作為統籌整條研究流程的決策者：它接收研究查詢與
session 識別碼，逐輪決定要把什麼任務派給哪些 sub-agent、或結束流程，並組出回覆給
使用者。流程的順序與方向由協調者決定，不寫死在圖的拓樸裡。

#### Scenario: 協調者驅動一次研究

- **WHEN** 協調者收到某個 session 的查詢
- **THEN** 它逐輪決定派工（如先搜尋、再生成報告），在判定完成後回覆使用者

### Requirement: 協調者調度通用 sub-agent

協調者 SHALL 透過一個通用調度機制把任務派給以名稱註冊的 sub-agent（web search 與
report generate 皆為 sub-agent），依各 sub-agent 的名稱與用途說明選擇要派誰。新增
sub-agent SHALL 只需註冊、不需更動協調流程。sub-agent 之間 SHALL NOT 互相溝通，只
從協調者接收任務、回傳成果。

#### Scenario: 並行派工給多個 sub-agent

- **WHEN** 協調者決定本輪要執行多個任務
- **THEN** 每個任務各派給其指定的 sub-agent 並行執行，成果合併回共用狀態供後續使用

#### Scenario: 新增 sub-agent 不動協調流程

- **WHEN** 一個新的 sub-agent 被註冊進系統
- **THEN** 協調者能把任務派給它，而圖的結構與既有流程不需改動

### Requirement: 協調者決定流程且有上限

協調者 SHALL 能依目前累積的成果逐輪重新決策（再派工或結束），使流程彈性而非固定步數。
重輪 SHALL 受一個上限約束，達到上限即結束、以現有成果回覆，不無限循環。

#### Scenario: 依成果再派工

- **WHEN** 協調者檢視本輪成果後判定還需要更多資訊
- **THEN** 它再派出新任務、進入下一輪

#### Scenario: 達上限即結束

- **WHEN** 輪數達到上限但協調者仍未結束
- **THEN** 協調者停止派工、以現有成果組出回覆

### Requirement: 協調者回覆使用者

協調者 SHALL 能在流程中輸出給使用者的文字（說明進度或結果）。一次流程結束時的回覆
SHALL 以協調者的文字為主；當本次有 report sub-agent 產出 HTML 報告時，該報告 SHALL
併入回覆。

#### Scenario: 研究結果含報告

- **WHEN** 協調者完成流程且本次產出了 HTML 報告
- **THEN** 回覆以協調者的文字為主，並附上該 HTML 報告

#### Scenario: 純文字回覆

- **WHEN** 協調者判定不需要產報告即可回應
- **THEN** 回覆只含協調者的文字

### Requirement: 圖狀態承載流程上下文

圖狀態 SHALL 承載查詢、session 識別碼、近期對話、跨 sub-agent 累積的成果、協調者本輪
的決策（要回覆的文字、要派的任務、是否結束）、輪數與已產出的報告；累積成果 SHALL 以
reducer 合併，使並行派工的寫入不互相覆蓋。

#### Scenario: 並行成果累積在圖狀態

- **WHEN** 多個 sub-agent 並行完成
- **THEN** 各自的成果都合併寫入共用狀態，後續 sub-agent 與協調者讀得到全部

### Requirement: 協調者整合 session 記憶

協調者 SHALL 在決策前讀取該 session 的近期上下文以延續對話，並在流程結束後把該輪
（查詢與回覆）追加進該 session 的完整聊天紀錄。

#### Scenario: 延續既有 session 的對話

- **WHEN** 協調者收到某既有 session 的後續查詢
- **THEN** 它在決策時參考近期上下文，流程結束後把該輪追加進紀錄

### Requirement: 子 agent 失敗會往上拋

協調者 SHALL 在 sub-agent 因基礎設施錯誤（LLM 或搜尋後端無法連線）而失敗時，把錯誤
往上拋，而不是悄悄改用空的或降級的結果；任一並行派工分支失敗即讓該次協調者流程失敗。

#### Scenario: 搜尋後端無法連線

- **WHEN** 某個 web search sub-agent 因搜尋後端無法連線而失敗
- **THEN** 該次協調者流程拋出錯誤、讓呼叫端知道失敗，而不是回覆一份空報告
