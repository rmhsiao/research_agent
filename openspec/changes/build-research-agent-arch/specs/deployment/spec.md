## ADDED Requirements

### Requirement: 服務容器化

系統 SHALL 為 API 服務與 Streamlit 前端各提供一份 Docker image，讓兩者各自在獨立
容器中執行。

#### Scenario: image 可建置

- **WHEN** 對 API 與前端執行 Docker 建置
- **THEN** 兩份 image 都建置成功，並能各自啟動對應服務

### Requirement: Compose 帶起整套服務

系統 SHALL 提供一份 Docker Compose 設定，同時啟動 API 與前端，前端設定為可連到 API，
機密則以環境變數注入。記憶用的檔案儲存體 SHALL 掛載成持久化磁碟區，使其在容器重建後
仍保留。

#### Scenario: 用 Compose 把整套帶起來

- **WHEN** 設好必要環境變數後執行 `docker compose up`
- **THEN** API 與前端啟動，且前端連得到 API

#### Scenario: 缺少必要設定就快速失敗

- **WHEN** 啟動時缺少某個必要環境變數（例如 LLM 金鑰）
- **THEN** 受影響的服務快速失敗並給出清楚錯誤，而不是以壞掉的狀態啟動
