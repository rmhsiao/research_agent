
我想要建立一個 research agent system，用來作為通用型的 agent 技術搜尋助理

## Agents

須包含以下 agent
1. coordinator agent：系統的主 agent，負責協調任務進度、各項 sub agents 的協調溝通
2. web search agent：從 coordinator agent 接收指令，上網搜尋相關資料，初步整理摘要後，回傳給 coordinator
3. report generate agent：從 coordinator 接收搜尋結果後，進行整理與摘要，最後以 html 格式輸出報告給使用者

之後視系統效果，再考慮是否細一步切分 agent
- web search agent 再拆出 document analyze agent，專職負責文件內容分析，同時也開放支援 local 檔案讀取
- report generate agent 再拆出 synthesize agent，專職文件內容整理、比對、摘要，report generate agent 就專職負責報告的版面輸出

## Memory

coordinator 需有記憶系統
- 只保留最近 N 輪的聊天紀錄帶給 LLM (可用環境參數設定)
- 超過 N 輪的記憶，須被壓縮成 session-wise 的長期記憶 (每 3 輪跑非同步壓縮一次，但這也要設定為環境參數控制)
- 需可切分為多個不同 session，session 之間先設計為不共通記憶

## Tech Stacks

- python：主要語言
- langgraph：agent 的實作框架
- fastapi：在 agent 架構之上，以 api 層提供服務
- streamlit：提供前端介面，串接 api 使用
- docker / docker compose：打包整體服務，並提供部署方式


## Implemnetation Draft

想先初步建立 agent 架構，讓整套流程串起來，後續再細一步調整各個元件的功能，如：
- 建立專案架構，包含常見 config 模式
- 先用 langggraph 建立各 agent 的架構，其中各 agent 可先用最簡單的 prompt 或設定來實作
- 然後用 fastapi 套出 api 服務
- 建立 docker / compose 設定以部署
- 建立 streamlit 前端，並串接 fastapi

## Appendix

此專案主要是參考 `CCAF Exam Guide` 中的 `Scenario 3: Multi-Agent Research System` 進行發想
