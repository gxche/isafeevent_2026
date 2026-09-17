# 專案架構

使用方式見 [README.md](README.md)。本專案支援高中職以上學生與一般民眾的兩頁評量，第一頁固定選「普通」，第二頁由所選 API 作答。

## 檔案配置

```text
isafeevent_2026/
├── bot_gemini.py
├── bot_openai.py
├── quiz_runner.py
├── ai_answers.py
├── requirements.txt
├── README.md
├── plan.md
└── .gitignore
```

| 檔案 | 職責 |
| --- | --- |
| `bot_gemini.py` | Gemini 執行入口 |
| `bot_openai.py` | OpenAI 執行入口 |
| `quiz_runner.py` | 命令列參數、Chrome、手動登入、解析題目、選取答案與確認結果頁 |
| `ai_answers.py` | 讀取設定、API 呼叫、答案格式驗證、有限次重試與執行期間快取 |
| `requirements.txt` | 只設最低版本的直接依賴清單，供使用者安裝；更新已安裝套件需加 `--upgrade` |

`.env` 由使用者在本機建立，Git 會忽略它。安裝後的 `.venv/`、執行產生的 `.browser-profile/`、`.cache/` 與 Python 快取也不提交。

## 執行流程

1. 選擇 Gemini 或 OpenAI 入口，開啟專用 Chrome。
2. 等待使用者手動登入並在終端按 Enter。
3. 讀取專案 `.env`、建立 API client；同名系統環境變數優先。
4. 第一頁逐題選「普通」，確認全數選取才送出。
5. 等待第二頁，逐題將題目文字與選項送至所選 API。
6. 驗證模型回傳的選項編號，再選取對應 radio。
7. 全部作答後送出；確認結果頁才計入完成。

正常執行預設一次。`--attempts` 指定次數，`--delay` 指定間隔；`--test-api` 僅呼叫一題 API，不開啟活動網站；`--debug` 在出錯時印出 traceback，並存截圖與頁面 HTML 至 `.cache/debug/`（含個人頁面內容，勿分享；API 例外內容仍不顯示）。出錯後等待按 Enter 時，Ctrl+C 或輸入中斷只結束等待，不覆蓋原本的停止原因。

## API 與答案處理

- Gemini：`google-genai` 的 `models.generate_content`，預設 `gemini-3.5-flash-lite`；未使用工具，明確關閉自動函式呼叫（AFC），避免 SDK 警告。
- OpenAI：Responses API，預設 `gpt-5.4-nano`，`store=False`。
- 回傳格式為 `{"choice": N}`，使用從 1 開始的選項編號；JSON Schema 與程式共同驗證範圍。
- 不使用推理模型；輸出上限 `MAX_OUTPUT_TOKENS = 1024`。
- 空回覆、拒答、截斷或無效答案會停止，不隨機作答；超過 token 上限會明確提示，其他未完成情況附上原因（OpenAI `incomplete_details.reason`、Gemini `finish_reason`）。
- 暫時性網路錯誤、429 與指定 5xx 最多嘗試三次，退避等待 2、4 秒；永久錯誤不重試。
- 以題目與選項順序作為記憶體快取 key，不保存題庫檔案。

## 網頁相容性

題目容器使用 `[id^="div_q_"]`，標題使用 `h4`。radio 的題庫編號不等於顯示題號，必須在各題內以 CSS 選擇器 `label[for="<radio id>"]` 找到對應選項（id 中的引號與反斜線會跳脫），每個 radio 須恰好對應一個 label。

題數依頁面取得，目前支援第一頁五點量表、第二頁單選題。頁面變動、未作答完整或送出後無法確認結果時停止，不自動重送。

## 依賴版本下限

| 套件 | 下限 | 原因 |
| --- | --- | --- |
| `selenium` | 4.12 | selenium-manager 支援 `SE_CACHE_PATH` |
| `google-genai` | 1.39 | `Client.close`；`response_json_schema`、`retry_options` 自 1.21 起 |
| `openai` | 1.66 | Responses API 的 `output_text` |
| `python-dotenv` | 1.0 | 保守下限 |

## 維護

Gemini 曾完成一次實站評量；OpenAI 僅做過模擬測試。結果頁代表提交流程完成，不保證每題正確或取得抽獎資格。

測試檔案與開發工具已移除。後續改動 API、套件或網站解析邏輯時，需重新驗證功能；`--test-api` 會產生真實 API 呼叫，可能收費。

2026-09-17 穩健性修正（label 查找、截斷提示、`--debug`、版本下限）已以最新版套件與無頭 Chrome 離線驗證（本機 HTML 頁面、模擬 API 回覆）；尚未於實站與真實 API 重新驗證。

目前 repo 資料夾以正式程式與文件為主，未附虛擬環境、快取或歸檔壓縮檔。舊備份已移至同層 `isafeevent_archives/isafeevent_2026-history/`；本機 `.git` 歷史保留，未設定遠端，也未發布。
