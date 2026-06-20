## ADDED Requirements

### Requirement: Streamlit 前端驅動 API

系統 SHALL 提供一個 Streamlit 應用：使用者輸入研究查詢，前端以 OpenAI 相容介面呼叫 API
的 chat completions 端點，並渲染回傳 content 的 HTML 報告。

#### Scenario: 使用者送出查詢並看到報告

- **WHEN** 使用者在 Streamlit 應用輸入查詢並送出
- **THEN** 前端以 OpenAI 相容介面呼叫 API，並把回傳的 HTML 報告渲染在頁面上

#### Scenario: 把 API 錯誤顯示給使用者

- **WHEN** API 回應錯誤狀態
- **THEN** 前端顯示錯誤訊息，而不是空白或壞掉的報告

### Requirement: 前端以 session 選單延續既有對話

前端 SHALL 提供一個 session 選單,內容來自 API 的 session 清單端點;使用者選定某個既有
session 後,前端 SHALL 載入該 session 的完整聊天紀錄並顯示,使後續查詢延續在同一 session
之上。前端 SHALL 也能開新的 session。

#### Scenario: 選既有 session 延續對話

- **WHEN** 使用者從選單選定某個既有 session
- **THEN** 前端呼叫聊天紀錄端點載入並顯示該 session 過往對話,之後送出的查詢以 `extra_body`
  帶上同一 session 識別碼

#### Scenario: 開新 session

- **WHEN** 使用者選擇開新對話
- **THEN** 前端以一個新的 session 識別碼開始,並把它一起送往 API

#### Scenario: 請求帶上 session id

- **WHEN** 使用者在所選 session 內送出查詢
- **THEN** 前端以 `extra_body` 把該 session 的識別碼一起送往 API
