## ADDED Requirements

### Requirement: 近期上下文視窗有上限

協調者的記憶 SHALL 在組裝給 LLM 的上下文時，只保留最近「近期保留輪數」（`recent_rounds`）
輪對話，該值由環境變數設定。

#### Scenario: 上下文只含近期保留輪數

- **WHEN** 某 session 的輪數超過近期保留輪數，協調者組裝 LLM 上下文
- **THEN** 只有最近近期保留輪數的對話會被放進提示上下文

#### Scenario: 近期保留輪數可用環境變數設定

- **WHEN** 近期保留輪數的環境變數被設成某值
- **THEN** 協調者以該值作為近期保留輪數，不需改動程式碼

### Requirement: 長期記憶非同步壓縮

超出近期視窗的輪次 SHALL 由一個非同步任務壓縮成 session 層級的長期摘要，該任務每「壓縮
間隔輪數」（`compress_every_rounds`）輪執行一次，該值由環境變數設定。壓縮 SHALL 不阻塞
觸發它的那次請求。

#### Scenario: 壓縮依週期執行

- **WHEN** 距上次壓縮已累積壓縮間隔輪數
- **THEN** 一個非同步壓縮任務把溢出的輪次摘要進該 session 的長期摘要

#### Scenario: 壓縮不阻塞回應

- **WHEN** 處理某次請求時觸發了壓縮任務
- **THEN** 該請求照常回傳回應，不等壓縮完成

#### Scenario: 長期摘要會餵進後續上下文

- **WHEN** 壓縮跑完後，協調者再次組裝上下文
- **THEN** 該 session 的長期摘要會與最近近期保留輪數的對話一起被納入

### Requirement: 記憶以 session 隔離

記憶 SHALL 以 session 識別碼分區，某個 session SHALL 不會讀到另一個 session 的近期
輪次或長期摘要。

#### Scenario: session 之間不共用記憶

- **WHEN** 協調者為 session A 組裝上下文
- **THEN** 屬於 session B 的任何輪次或摘要都不會出現在 session A 的上下文裡

### Requirement: 記憶以儲存體持久化

記憶 SHALL 以檔案儲存體（file storage）保存每個 session 的**完整聊天紀錄**、長期摘要與
組裝近期視窗所需的狀態，並在服務重啟後仍能讀回；本里程碑 SHALL NOT 使用資料庫。長期壓縮
只影響「帶給 LLM 的上下文」（近期視窗 ＋ 摘要），SHALL NOT 刪除已保存的完整聊天紀錄。

#### Scenario: 重啟後記憶仍在

- **WHEN** 服務重啟後協調者載入某個既有 session
- **THEN** 該 session 在重啟前的完整聊天紀錄與長期摘要仍可取得

#### Scenario: 壓縮不刪除完整紀錄

- **WHEN** 某 session 已發生長期壓縮
- **THEN** 被壓縮的輪次仍保留在完整聊天紀錄中，只是不再進入帶給 LLM 的上下文

### Requirement: 可列舉 session 與取回完整聊天紀錄

記憶 SHALL 能列舉目前所有 session 的識別碼，並依識別碼取回某 session 的完整聊天紀錄，
作為 API 對應端點的底層能力。

#### Scenario: 列舉 session

- **WHEN** 請求目前的 session 清單
- **THEN** 回傳所有已持久化 session 的識別碼

#### Scenario: 依 session 取回完整紀錄

- **WHEN** 以某個既有 session 識別碼請求其聊天紀錄
- **THEN** 回傳該 session 依序的完整查詢與回應
