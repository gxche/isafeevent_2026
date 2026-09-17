# 2026 全民數位素養自我評量助手

適用高中職以上學生與一般民眾。手動登入活動網站後，第一頁固定全部選「普通」，第二頁由 Gemini 或 OpenAI 回答，送出後確認結果頁。

## 安裝

以下指令適用 Windows，請在專案資料夾的 Terminal 中逐行執行，確認前一步成功後再繼續。

### 1. 安裝 Python 與 Chrome

- 安裝 [Python](https://www.python.org/downloads/windows/) 3.10 以上；本專案曾以 Python 3.14 驗證。
- 安裝 [Google Chrome](https://www.google.com/chrome/)。
- 準備可登入活動網站的帳號，以及 Gemini 或 OpenAI 其中一家的 API 金鑰。

安裝 Python 後，重新開啟 Terminal 並確認：

```text
py --version
```

若找不到 `py`，可先試 `python --version`。如果 `python` 可用，下面建立環境的 `py` 改用 `python` 即可；兩者都無法執行時，請先完成 Python 安裝並重新開啟 Terminal。

### 2. 建立專案 Python 環境

```text
py -m venv .venv
.\.venv\Scripts\python.exe --version
```

後續一律使用 `.\.venv\Scripts\python.exe`，確保套件安裝到本專案。不需要另外啟用虛擬環境。

### 3. 安裝套件

```text
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 包含 `selenium`、`google-genai`、`openai`、`python-dotenv`，只設定程式所需的最低版本。pip 會解析適用於目前 Python 的相依套件；已安裝且符合需求的套件可能直接沿用。

日後若要更新已安裝套件，執行：

```text
.\.venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

### 4. 檢查安裝結果

```text
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe bot_gemini.py --help
.\.venv\Scripts\python.exe bot_openai.py --help
```

`pip check` 顯示 `No broken requirements found.`，且兩支程式都能顯示參數說明，即代表基本安裝檢查通過。這些指令不會開啟活動網站或呼叫 API；模型連線需另用下方的 `--test-api` 檢查。

首次正式啟動會由 Selenium 自動下載相符的 ChromeDriver，請保持網路連線，不必另外安裝驅動程式。

## 設定金鑰

在程式所在資料夾自行建立 `.env`，可使用記事本：

```text
notepad .env
```

若檔案不存在，選擇建立新檔；另存時選「所有檔案」、UTF-8 編碼，確認檔名是 `.env` 而非 `.env.txt`。若已有 `.env`，只修改需要的設定，保留現有金鑰。

填入要使用的供應商金鑰，另一家可留空：

```dotenv
GEMINI_API_KEY=
OPENAI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
OPENAI_MODEL=gpt-5.4-nano
```



## 使用

選擇其中一支執行：

```text
.\.venv\Scripts\python.exe bot_gemini.py
# 或
.\.venv\Scripts\python.exe bot_openai.py
```

1. 在程式開啟的專用 Chrome 視窗，手動登入[活動網站](https://isafeevent.moe.edu.tw/)。
2. 登入完成後回 Terminal 按 **Enter**，才會開始填答與呼叫 API。
3. 等待兩頁填答、送出完成；執行期間請勿操作或重新整理這個瀏覽器視窗。
4. 看到「已確認結果頁：1/1」後可查看結果，再按 Enter 關閉瀏覽器。

預設執行一次。第二頁題目與選項會傳送給所選 AI 供應商。專用 Chrome 的登入狀態保存在本機，每次仍需按 Enter 才開始；一次只執行一支腳本。

### 選用指令

```text
# 完成兩次評量，每次間隔 15 秒
.\.venv\Scripts\python.exe bot_gemini.py --attempts 2 --delay 15

# 僅測試一次 API，不開啟網站、不提交評量（可能產生少量 API 費用）
.\.venv\Scripts\python.exe bot_gemini.py --test-api

# 出錯時顯示詳細錯誤，並將截圖與頁面 HTML 存到 .cache\debug（含個人頁面內容，請勿分享）
.\.venv\Scripts\python.exe bot_gemini.py --debug

# 查看參數
.\.venv\Scripts\python.exe bot_gemini.py --help
```

OpenAI 使用相同參數，將檔名換成 `bot_openai.py` 即可。

## 常見問題


| 狀況                      | 處理方式                                                                         |
| ------------------------- | -------------------------------------------------------------------------------- |
| 找不到`py`                | 安裝 Python 後重新開啟 Terminal；若已有`python`，可用 `python -m venv .venv`。 |
| 缺少套件                  | 使用`.\.venv\Scripts\python.exe`，重新執行上面的安裝指令。                       |
| 找不到`requirements.txt`  | 先切換到包含該檔案的專案資料夾，再執行安裝。                                     |
| 找不到`.venv` 中的 Python | 確認目前目錄正確，並已成功執行建立環境的步驟。                                   |
| 顯示`No module named pip` | 執行`.\.venv\Scripts\python.exe -m ensurepip --upgrade`，再重試安裝套件。        |
| 找不到金鑰                | 檢查`.env` 的位置、檔名及所選供應商欄位是否已填寫。                              |
| API 401／403／模型不可用  | 檢查金鑰、模型名稱與帳號權限。                                                   |
| API 429                   | 檢查配額或呼叫頻率，稍後再試。                                                   |
| Chrome 無法開啟           | 關閉之前由腳本開啟的專用 Chrome，確認沒有同時執行另一支腳本。                    |
| 登入失效                  | 在腳本開啟的 Chrome 重新手動登入。                                               |
| 題目格式錯誤或送出逾時    | 查看網站狀態；若已點擊最後送出，先確認是否完成，避免重複提交。                   |
| 搬移資料夾後無法執行      | 在新位置重新建立`.venv` 並安裝套件。                                             |

出錯時會停止，不會隨機作答或繼續送出未完成的頁面；第一頁可能已送出。可按 `Ctrl+C` 中止。

## 文件

- [專案架構與維護](plan.md)

請保留完整程式資料夾，兩支入口程式需要同目錄的 `quiz_runner.py` 與 `ai_answers.py`。專案不附已安裝的 Python 套件，請依上方步驟安裝並設定 `.env`。
