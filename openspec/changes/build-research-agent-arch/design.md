## Context

全新 repo：`src/research_agent/` 是空套件，跑在 Python 3.14 上，已設好 `uv`、`ruff`、
`mypy --strict` 與 `pytest`。這個 change 的目標是把端到端骨架串起來 —— multi-agent
圖 → API → UI → 部署 —— 各 agent 刻意維持最精簡。這是一個橫跨多模組、引入數個新相依與
一套非同步記憶子系統的 change，因此下列前置決策值得在動工前先定下來。

原始需求 brief 見 [`references/original-brief.md`](references/original-brief.md)。

## Goals / Non-Goals

**Goals：**

- 一個用 LangGraph 串起 coordinator ＋ web-search ＋ report-generate 的圖。
- session 範圍的協調者記憶：有上限的近期視窗 ＋ 非同步長期壓縮，以 session 隔離、可用
  環境變數調整。
- 一個架在圖之上的 FastAPI 服務，與一個架在 API 之上的 Streamlit UI。
- 能把整套帶起來的 Docker Compose。
- 一套後續迭代不需重構就能擴充的套件佈局與設定模式。

**Non-Goals：**

- 拆出 document-analyze／synthesize agent（未來工作）。
- 本地檔案匯入、跨 session 共用記憶、資料庫。
- 生產級強化（認證、限流、健康檢查以外的可觀測性）。
- 複雜的 agent 推理 —— prompt 維持 MVP 等級。

## Decisions

### 套件佈局 —— 區分核心套件 / api / ui 三類

結構上把三種程式邏輯切成三個獨立的頂層套件，讓「核心領域邏輯」「對外服務層」「前端」彼此
邊界清楚：

```
src/
  research_agent/        # 核心套件（library）：純邏輯，不依賴 fastapi/streamlit
    config.py            #   Settings（pydantic-settings），env 驅動
    dto.py               #   共用 Pydantic DTO（Findings、Round…）
    llm.py               #   LLMClient 介面 ＋ OpenAI 相容實作
    search.py            #   SearchClient 介面 ＋ Tavily 實作
    memory/              #   SessionStore 介面 ＋ file 實作、近期視窗、非同步壓縮器
    agents/              #   coordinator、web_search、report_generate
    graph/               #   狀態模型 ＋ 圖組裝
  api/                   # API 層：FastAPI 應用，import 核心套件
  ui/                    # UI 層：Streamlit 應用，只走 HTTP，不 import 核心套件
```

**相依方向（單向）**：`ui ──HTTP──> api ──import──> 核心套件`。核心套件不認識 api／ui；
ui 不直接 import 核心,只透過 HTTP 與 api 對話。如此核心可獨立測試與重用,api／ui 只是
它的兩種對外載體。memory 與 graph 各自成子套件,因為它們各有足夠獨立的邏輯。

### Agent 框架 —— LangGraph ＋ 共用型別化狀態

協調者是一個 `StateGraph`；web-search 與 report-generate 是協調者路由過去的節點。狀態
是一個型別化模型，承載 `query`、`session_id`、`findings`、`report`。一條條件邊讓協調者
能折返再搜尋、或前進到報告生成（即「資料是否足夠」的判斷）。曾考慮：不用 LangGraph、自
己手刻統籌 —— 否決，因為使用者指定用 LangGraph，且它的 checkpointer／狀態機制正是我們
需要的路由底座。

### LLM 介面 —— OpenAI 相容，可設定

LLM 走 **OpenAI 相容介面**：用 `openai` SDK，`base_url`／`api_key`／`model` 全部來自
設定，因此可指向任何 OpenAI 相容的端點（自架或各家 gateway），不綁單一供應商。協調者的
彙整／判斷步驟用較強的模型、子 agent 的摘要用較便宜的模型，兩者的模型 id 都在設定裡逐
agent 指定，不動程式碼即可抽換。一個輕薄的 `llm.py` 工廠集中建構 client、把金鑰存成
`SecretStr`，並暴露一個薄 `LLMClient` 介面（見下「抽換接縫」）讓 agent 依賴它。

### 抽換接縫（介面抽象化）

只把三個外部／儲存邊界抽成介面，其餘維持具體實作，等第二個需求出現再 refactor。三個介面
抽象化的共同目的都是**保持抽換彈性**（換實作不動上層），不是為了測試 mock。

- **`LLMClient`** —— 形狀 `complete(messages, model) -> str`。具體實作為 OpenAI 相容
  client。介面讓 LLM 供應商／端點可被抽換而不動 agent；維持薄，不包成厚抽象。
- **`SearchClient`** —— 形狀 `search(query) -> list[SearchResult]`，後端錯誤 raise 且與
  「查無結果」明確區分。具體實作為 Tavily；介面讓日後換別的搜尋後端時不動 agent。
- **`SessionStore`** —— 形狀 `load(session_id) -> SessionState` / `save(session_id,
  state)`。現為 file storage；介面讓日後換 Redis／DB 時不動 agent，也讓上層不認識儲存細節。

刻意**不抽**（premature abstraction）：報告輸出格式（目前只有 HTML，寫死在 report
generate agent）、記憶壓縮策略、上下文組裝策略、以及 agent 基底類別 —— 都等真有第二種
實作再抽。

### 資料模型 —— 全程 Pydantic v2

DTO 與服務型類別（記憶 store、壓縮器、各 agent 的 I/O）都用 Pydantic `BaseModel`。欄位
層級驗證（如 `memory_recent_rounds >= 1`、`memory_compress_every_rounds >= 1`）下沉到 schema 的
`Field(ge=...)`，而非寫在 method 裡。
設定用 `pydantic-settings` 讀 env。單一機制、免費拿到驗證與嚴格模式 —— 沒理由讓服務型
類別特別 opt-out。

### 記憶 —— 以檔案為底的 session store ＋ 非同步壓縮

- 一個以 `session_id` 為鍵的 `SessionStore`，每個 session 存：**完整聊天紀錄**、一段長期
  摘要字串、以及組裝近期視窗所需的狀態。以 **file storage** 為底（一 session 一檔，例如
  資料目錄下的 JSON），讓 session 能撐過重啟。本里程碑不用資料庫 —— store 維持為單一接
  縫，日後需要再換成 Redis／DB。
- 完整聊天紀錄與「帶給 LLM 的上下文」是**兩件事**:壓縮只把溢出輪次折成摘要、縮小餵給 LLM
  的內容,但**不刪**完整紀錄。完整紀錄供 UI 顯示與延續對話;`SessionStore` 另提供
  `list_sessions()` 與 `get_history(session_id)` 給 API 的 session 管理端點用。
- 上下文組裝器回傳 `長期摘要 ＋ 最近 memory_recent_rounds 輪`。
- 壓縮是一個 `asyncio` 背景任務，每 `memory_compress_every_rounds` 輪觸發一次；它用 LLM 把溢出
  的輪次摘要起來、折進該 session 的摘要。它不得阻塞請求 —— fire-and-forget 任務，錯誤要記
  log、不可被吞進回應路徑。
- `memory_recent_rounds`（env `MEMORY_RECENT_ROUNDS`，近期保留輪數）與 `memory_compress_every_rounds`
  （env `MEMORY_COMPRESS_EVERY_ROUNDS`，壓縮間隔輪數）是環境變數。曾考慮：溢出時同步壓縮
  —— 否決，因為那會把 LLM 延遲加到使用者請求上。

### API —— FastAPI，OpenAI Chat Completions 相容端點

研究服務本身對外提供 **OpenAI Chat Completions 相容**介面：`POST /v1/chat/completions`,
外加 `GET /health`、以及兩個 session 管理端點:`GET /sessions`（列出 session 清單）與
`GET /sessions/{session_id}/history`（取該 session 完整聊天紀錄）。後兩者是一般 JSON REST
（非 OpenAI 格式),底層接 `SessionStore` 的 `list_sessions()`／`get_history()`,供 UI 的
session 選單與延續對話用;未知 session 回 not found,而非空的 200。查詢取自 `messages`
最後一則 user 訊息;`session_id`（及未來的額外欄
位）走請求 body 的**額外欄位**帶入 —— client 端用 OpenAI SDK 的 `extra_body` 送、伺服端
從 body 取出,標準 schema 維持乾淨。回應是標準 ChatCompletion 物件,assistant 訊息的
content 即 HTML 報告。端點用 `async def`（圖與 LLM 呼叫都是 I/O 密集）。基礎設施錯誤回非
2xx 的 OpenAI 風格 error JSON,絕不收斂成「200 夾帶空報告」—— 與「失敗一律 raise、不隱
藏」一致。

理由:形成對稱 —— 系統**消費** LLM 走 OpenAI 相容介面,**對外**也以同一種介面提供,任何
OpenAI client（含我們的 Streamlit UI）可直接串接;session 這種非標準欄位走 `extra_body`,
不污染標準 schema。選它而非自訂 `POST /research` schema,是為了不另立一套 client 都要重學
的介面。

### Web 搜尋後端 —— Tavily，藏在 SearchClient 介面後面

具體後端定為 **Tavily**（`tavily-python`），實作 `SearchClient` 介面。保留這層薄介面是為
了**抽換彈性**——日後換別的搜尋後端時不動 agent。金鑰（`TAVILY_API_KEY`）來自設定。後端
錯誤要 raise，且與正當的「查無結果」明確區分，讓協調者分得出「搜尋壞了」與「沒找到」。

web search agent 回給協調者的 SHALL 是**固定結構化的 `Findings`**（型別化 Pydantic
schema:一組各帶摘要與來源的 finding 項目),而非自由格式文字;查無結果時回項目為空的同型別
`Findings`,讓協調者用穩定的形狀消費。

### 前端與部署

Streamlit 應用用 OpenAI SDK 呼叫 `/v1/chat/completions`（base URL 來自 env），把查詢放進
`messages`、`session_id` 經 `extra_body` 帶入，渲染回傳 content 的 HTML 報告;並在 API 出錯
時顯示錯誤而非空白報告。側邊提供 **session 選單**:內容來自 `GET /sessions`,選定既有
session 時以 `GET /sessions/{id}/history` 載入過往對話顯示、後續查詢延續同一 session,也能
開新 session。兩份 Docker image（api、ui）由
`docker-compose.yml` 編排；UI 經由 env 拿到 API URL，機密經由 env 注入，必要設定（如 LLM
金鑰）缺漏時服務快速失敗。記憶資料目錄掛成 named volume，讓以檔案為底的 session 能撐過
容器重建。

## Risks / Trade-offs

- **以檔案為底的 store：併發／寫一半** → 維持逐 session、原子寫入（先寫 temp 再
  rename）；單一實例的 MVP 足夠。藏在 `SessionStore` 後面，日後換 Redis／DB 不動
  agent。
- **fire-and-forget 壓縮可能默默出錯** → 明確記 log，日後再用 health／metrics 暴露；絕
  不把錯誤折進使用者回應（否則會誤報成功）。
- **外部 LLM ＋ 搜尋的延遲／成本** → 子 agent 摘要用較便宜的模型，`memory_recent_rounds`／
  `memory_compress_every_rounds` 可調以限制上下文大小。
- **LangGraph API 變動** → 在 `pyproject.toml` 鎖版本；實作時對照文件確認當前的
  graph／state API。

## Open Questions

- ~~Web 搜尋後端~~ **已決議**：採 Tavily（`tavily-python`），藏在 `SearchClient` 介面
  後面。
- ~~Session 持久化~~ **已決議**：session 以 file storage 持久化（資料目錄下一 session
  一檔），本里程碑不用資料庫。
