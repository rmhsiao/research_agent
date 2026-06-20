## Why

我們需要一個通用型的技術研究助理：能接住一個技術問題、上網搜尋、彙整內容，再回傳一
份好讀的報告。目前尚無任何 agent 系統，這個 change 先把**端到端骨架**立起來
（multi-agent 圖 → API → UI → 部署），讓整條流程跑得通，各元件刻意維持最精簡、留待
後續迭代。

## What Changes

- 建立專案結構：結構上區分**核心套件**（`research_agent`）、**API 層**（`api`）、
  **UI 層**（`ui`）三類程式邏輯；以環境變數驅動的設定、與一個設定模型。
- 用 LangGraph 串起三個 agent：
  - **coordinator**：統籌整次流程、委派給子 agent、判斷搜尋是否足夠、何時生成報告。
  - **web search**：接收協調者的查詢、上網搜尋、回傳整理過的結果集。
  - **report generate**：接收收集到的結果、產出 HTML 報告給使用者。
- 給協調者一套 **session 範圍的記憶系統**：LLM 上下文只保留最近「近期保留輪數」、把較舊
  的輪次非同步壓縮成 session 層級的長期摘要、且記憶以 session 隔離並持久化（用 file
  storage，不用 DB）。
- 以 **FastAPI** 把整個圖對外提供服務，端點為 **OpenAI Chat Completions 相容**介面，
  session 等額外欄位走 `extra_body` 帶入。
- 提供串接 API 的 **Streamlit** 前端（以 OpenAI SDK 呼叫）。
- 用 **Docker / Docker Compose** 打包與部署。

各 agent 先用最精簡可行的 prompt／邏輯實作；目標是把架構串起來，而非功能深度。未來可能
的拆分（document-analyze agent、synthesize agent）明確列為**範圍外**。

## Capabilities

### New Capabilities
- `agent-orchestration`：LangGraph 圖與協調者，把一個研究請求路由過各子 agent 並組出
  最終結果。
- `web-search`：web search agent —— 查詢 → 網路結果 → 整理過的摘要。
- `report-generation`：report generate agent —— 結果 → HTML 報告。
- `coordinator-memory`：session 範圍的記憶，含近期保留輪數的視窗、非同步長期壓縮、以
  session 隔離並持久化。
- `api-service`：以 OpenAI Chat Completions 相容介面對外提供 agent 系統的 FastAPI 層。
- `web-ui`：串接 API 的 Streamlit 前端。
- `deployment`：把各服務帶起來的 Docker / Docker Compose 打包。

### Modified Capabilities
<!-- 無 —— 這是全新系統，沒有既有 spec。 -->

## Impact

- **新增程式碼**：核心套件 `src/research_agent/`（config、models、llm、search、memory、
  agents、graph）、API 層 `src/api/`、UI 層 `src/ui/`、`Dockerfile`、
  `docker-compose.yml`。
- **新增相依**：`langgraph`、`openai`（OpenAI 相容 LLM client）、`fastapi`、
  `tavily-python`（web 搜尋）、`streamlit`，以 `uv` 加進 `pyproject.toml`。
- **設定面**：新增環境變數（LLM 的 `base_url`／金鑰／逐 agent 模型、`recent_rounds`
  近期保留輪數、`compress_every_rounds` 壓縮間隔輪數、記憶資料目錄、`TAVILY_API_KEY`）與
  一個型別化設定模型。
- **執行時**：引入外部呼叫（LLM ＋ web search）、一個記憶壓縮的非同步背景任務、以及一個
  存放 session 記憶的 file storage 資料目錄。
