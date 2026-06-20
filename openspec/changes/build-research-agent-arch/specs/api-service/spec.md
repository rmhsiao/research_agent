## ADDED Requirements

### Requirement: 以 OpenAI 相容介面對外提供 agent 系統

系統 SHALL 提供一個 OpenAI Chat Completions 相容的端點，從 `messages` 取得研究查詢、從
請求 body 的額外欄位取得 session 識別碼（client 端以 `extra_body` 帶入），執行協調者圖，
並把生成的 HTML 報告放在回應的 assistant 訊息 content 回傳。

#### Scenario: 研究請求成功

- **WHEN** 用戶端以 OpenAI Chat Completions 格式 POST 一筆含 user 訊息的請求，並用
  `extra_body` 帶入 session id
- **THEN** 服務執行協調者，並回傳一個標準 ChatCompletion 物件，其 assistant 訊息 content
  為 HTML 報告

#### Scenario: 缺少查詢被擋下

- **WHEN** 用戶端送出的請求沒有任何 user 訊息
- **THEN** 服務回傳驗證錯誤，且不執行協調者

#### Scenario: 額外欄位走 extra_body

- **WHEN** 用戶端以 `extra_body` 帶入 session id 等非標準欄位
- **THEN** 服務從 body 取出這些欄位，且標準 Chat Completions schema 不受污染

### Requirement: 基礎設施失敗以錯誤回應呈現

API SHALL 在協調者流程因基礎設施錯誤而失敗時，以非 2xx 的 OpenAI 風格 error 回應，而不是
回 200 卻夾帶一份空報告。

#### Scenario: 下游失敗回傳錯誤狀態

- **WHEN** 協調者流程拋出基礎設施錯誤
- **THEN** 服務以非 2xx 狀態回應 OpenAI 風格的 error，並說明該失敗

### Requirement: 列出 session 的端點

服務 SHALL 提供一個端點，回傳目前已存在的 session 清單，供前端讓使用者挑選既有 session
繼續對話。

#### Scenario: 取得 session 清單

- **WHEN** 用戶端請求 session 清單端點
- **THEN** 服務回傳目前所有 session 的識別碼清單（可含最後更新時間等簡短中繼資料）

#### Scenario: 尚無任何 session

- **WHEN** 還沒有任何 session 就請求清單
- **THEN** 服務回傳空清單，而非錯誤

### Requirement: 取得指定 session 聊天紀錄的端點

服務 SHALL 提供一個端點，依 session 識別碼回傳該 session 的完整聊天紀錄（依序的每一輪
查詢與回應），供前端載入後延續對話。

#### Scenario: 取得既有 session 的聊天紀錄

- **WHEN** 用戶端以某個既有 session 識別碼請求聊天紀錄端點
- **THEN** 服務回傳該 session 依時間排序的完整聊天紀錄

#### Scenario: 未知的 session

- **WHEN** 用戶端以不存在的 session 識別碼請求聊天紀錄
- **THEN** 服務回應 not found 錯誤，而非空的 200

### Requirement: 健康檢查端點

服務 SHALL 提供一個健康檢查端點，回報服務是否就緒。

#### Scenario: 健康檢查有回應

- **WHEN** 用戶端請求健康檢查端點
- **THEN** 服務回應健康狀態
