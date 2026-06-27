## 1. 專案骨架與設定

- [x] 1.1 用 `uv add` 加入執行期相依（`langgraph`、`openai`、`fastapi`、`uvicorn`、`pydantic-settings`、`streamlit`、`tavily-python`）並在 `pyproject.toml` 鎖版本
- [x] 1.2 建立三個頂層套件:核心 `src/research_agent/`（`config`、`dto`、`llm`、`search`、`agents/`、`graph/`、`memory/`）、API 層 `src/api/`、UI 層 `src/ui/`;設定 `uv` 建置能涵蓋三者。維持單向相依:ui ─HTTP→ api ─import→ 核心,核心不 import api／ui
- [x] 1.3 實作 `config.py`，用 `pydantic-settings` 寫 `Settings` 模型（LLM `base_url`、金鑰存 `SecretStr`、逐 agent 的模型 id、`memory_recent_rounds`(env `MEMORY_RECENT_ROUNDS`)≥1、`memory_compress_every_rounds`(env `MEMORY_COMPRESS_EVERY_ROUNDS`)≥1、`MEMORY_DATA_DIR`、`TAVILY_API_KEY` 存 `SecretStr`、API base URL），並做欄位層級驗證
- [x] 1.4 新增 `.env.example`，記錄所有環境變數
- [x] 1.5 測試：設定能從 env 載入；`memory_recent_rounds`／`memory_compress_every_rounds` 無效與必要金鑰缺漏時拋 `ValidationError`

## 2. 共用模型與 LLM client

- [x] 2.1 在 `dto.py` 定義共用 Pydantic DTO（`Finding`：摘要＋關鍵原文片段＋來源標題／網址;`Findings`：固定結構化的 finding 集合;`Report`、對話 `Round`）
- [x] 2.2 實作 `llm.py`：定義薄 `LLMClient` 介面（async、ABC），並以 OpenAI 相容（`openai` SDK 的 `AsyncOpenAI`，`base_url`／金鑰來自設定）實作，逐 agent 選模型 id
- [x] 2.3 測試：模型驗證；llm 工廠串接（mock OpenAI 相容 client）

## 3. web search agent

- [x] 3.1 定義 `SearchClient` 介面，並以 Tavily（`tavily-python`）實作；後端錯誤要 raise，與「查無結果」的空回應明確區分
- [x] 3.2 實作 web search agent：查詢 → 後端搜尋 → LLM 摘要 → 回傳**固定結構化的 `Findings`**（查無結果回項目為空的同型別）
- [x] 3.3 測試：回傳結構化 `Findings`（pass）／查無結果回空 `Findings`／後端錯誤會 raise（mock 後端＋LLM）
- [ ] 3.4 不受信輸入淨化（信任邊界）：web_search 回傳前以 nh3 把 snippet 洗成安全文字；`Finding.source_url` 加 http(s) 不變式（DTO），擋掉 `javascript:`／`data:` 等 URI；一併決定壞 URL 要 skip 還是 raise

## 4. report generate agent

- [x] 4.1 實作 report generate agent：`Findings` ＋ 查詢 → 可獨立開啟的 HTML 報告
- [x] 4.2 處理空結果：說明「查無資訊」、不捏造內容
- [x] 4.3 測試：非空結果渲染出含來源的 HTML／空結果路徑（mock LLM）
- [x] 4.4 報告本體刻意產出未過濾的 HTML（保留互動效果、不接 sanitizer）：留惡意內容偵測 TODO、`design.md` 記為 accepted risk；來源清單依 `Finding` 決定性渲染並 escape，URL 合法性交給 web_search／DTO（見 3.4）

## 5. 協調者記憶子系統

- [x] 5.1 實作 `SessionStore`（每 session 存**完整聊天紀錄**＋長期摘要＋近期視窗狀態，以 `session_id` 隔離），以 file storage 為底（資料目錄下一 session 一檔、原子寫入：先寫 temp 再 rename），重啟後可讀回
- [x] 5.2 實作上下文組裝器，回傳最近 `memory_recent_rounds` 輪（長期摘要的併入延後至 `## 10`）
- [x] 5.3 實作 `list_sessions()` 與 `get_history(session_id)`,供 API session 管理端點取用
- [x] 5.4 測試：視窗上限為 `memory_recent_rounds`／session 隔離／重啟後能從 storage 重載狀態／`list_sessions`＋`get_history` 正確

## 6. 協調者圖（orchestration）

- [ ] 6.1 定義圖狀態模型（`query`、`session_id`、`findings`、`report`）
- [ ] 6.2 組裝 LangGraph `StateGraph`，串起 web-search 與 report-generate 節點，並用條件邊做「資料是否足夠」的判斷
- [ ] 6.3 整合記憶：搜尋前讀上下文、流程後追加該輪
- [ ] 6.4 確保子 agent 的基礎設施失敗會往上拋出該次流程
- [ ] 6.5 測試：完整流程（pass）／資料足夠就停止搜尋／子 agent 失敗會往上拋（mock 各 agent）

## 7. FastAPI 服務（`api`，OpenAI 相容）

- [ ] 7.1 實作 FastAPI app，含 OpenAI Chat Completions 相容端點 `POST /v1/chat/completions`（query 取自 `messages`、`session_id` 從 body 額外欄位取出）與 `GET /health`
- [ ] 7.2 回應組成標準 ChatCompletion 物件,assistant content 放 HTML 報告;基礎設施錯誤對應成非 2xx 的 OpenAI 風格 error（絕不回 200 夾帶空報告）
- [ ] 7.3 加 session 管理端點：`GET /sessions`（接 `list_sessions()`）與 `GET /sessions/{session_id}/history`（接 `get_history()`,未知 session 回 not found）
- [ ] 7.4 測試：研究請求成功／缺 user 訊息 → 驗證錯誤／`extra_body` 帶 session 被正確取出／下游失敗 → 錯誤狀態／健康檢查／`GET /sessions` 含空清單／`GET /sessions/{id}/history` 取得紀錄與未知 session → not found（TestClient、mock 協調者與 store）

## 8. Streamlit 前端（`ui`）

- [ ] 8.1 實作 `ui/streamlit_app.py`：查詢輸入,用 OpenAI SDK 呼叫 `/v1/chat/completions`、`session_id` 經 `extra_body` 帶入,渲染回傳 content 的 HTML
- [ ] 8.2 加 session 選單：內容來自 `GET /sessions`,選既有 session 時以 `GET /sessions/{id}/history` 載入並顯示過往對話、後續查詢延續同一 session,並支援開新 session
- [ ] 8.3 API 回錯誤狀態時顯示錯誤訊息
- [ ] 8.4 手動驗證註記：對著執行中的 API 端到端送一次查詢,並驗證 session 選單能延續既有對話

## 9. 部署（Docker／Compose）

- [ ] 9.1 為 API 服務寫 Dockerfile（以 uv 建置、跑 uvicorn）
- [ ] 9.2 為 Streamlit 前端寫 Dockerfile
- [ ] 9.3 寫 `docker-compose.yml`，串起 api ＋ ui，經 env 注入機密與 API URL，把記憶資料目錄掛成 named volume，必要設定缺漏時快速失敗
- [ ] 9.4 驗證 `docker compose up` 能帶起兩個服務、且 UI 連得到 API

## 10. 非同步壓縮（長期記憶摘要）

- [ ] 10.1 實作非同步壓縮器：用 LLM 把溢出輪次摘要折進 session 的長期摘要，為 fire-and-forget 的不阻塞任務,錯誤記 log、不吞掉;壓縮**不刪**完整聊天紀錄
- [ ] 10.2 上下文組裝器納入長期摘要：把 `5.2` 的組裝結果擴充為 `長期摘要 ＋ 最近 memory_recent_rounds 輪`
- [ ] 10.3 把壓縮觸發接進流程：每 `memory_compress_every_rounds` 輪(於追加輪次的路徑)觸發一次,不得阻塞請求
- [ ] 10.4 測試：壓縮每 `memory_compress_every_rounds` 輪觸發且不阻塞且不刪完整紀錄／摘要折進 session 摘要並經組裝器餵進後續上下文（mock LLM）
