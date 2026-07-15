# 農業與農糧署新聞排程匯整系統說明書 (CLAUDE.md)

本專案是一個基於 FastAPI 的自動化農業新聞爬蟲與去重匯整系統，負責每日定時爬取 **農業部**、**農糧署**、**PTT Fruits 板**、**農傳媒** 與 **Yahoo 新聞（高麗菜搜尋）** 的最新新聞並整合存檔。

---

## 快速開始

### 1. 一鍵安裝並啟動
在專案根目錄下，使用 Python 執行引導腳本。此腳本會自動建立虛擬環境、安裝套件並啟動伺服器與開啟瀏覽器：
```bash
python run.py
```

### 2. 手動啟動伺服器
若已安裝必要套件，可直接使用虛擬環境執行伺服器主程式：
```bash
# Windows
.venv\Scripts\python.exe server.py

# macOS / Linux
.venv/bin/python server.py
```
啟動後服務網址為：`http://127.0.0.1:8000`

---

## 專案指令與依賴

### 依賴套件 (列於 `requirements.txt`)
* `fastapi`：Web API 框架
* `uvicorn`：ASGI 伺服器
* `requests`：網路請求庫
* `beautifulsoup4`：HTML 解析器

### 開發與測試常用指令
* 執行手動爬蟲 (無伺服器模式)：
  `python crawl.py`
* 測試農糧署爬蟲邏輯：
  `python scratch/test_afa_crawl.py`
* 測試編碼探測邏輯：
  `python scratch/inspect_afa.py`

---

## 系統架構設計

### 1. 爬蟲模組
* **農業部爬蟲 (`scrape_moa_news`)**：抓取最新 10 筆新聞。
* **農糧署爬蟲 (`scrape_afa_news`)**：抓取 [農糧署農業新聞](https://www.afa.gov.tw/cht/index.php?code=list&ids=307) 最新 10 筆新聞。由於第一頁可能不足 10 筆，系統支援**跨分頁爬取**，會自動請求下一頁直到集滿 10 筆為止。
* **PTT Fruits 板爬蟲 (`scrape_ptt_fruits`)**：抓取 PTT Fruits 板最新 10 筆文章，使用 `requests.Session()` 維持連線並加入 `0.2` 秒請求延遲，以防止 PTT 伺服器阻擋。
* **農傳媒爬蟲 (`scrape_agriharvest_news`)**：抓取農傳媒最新 10 筆新聞，並轉換為民國年日期格式。
* **Yahoo 新聞爬蟲 (`scrape_yahoo_news`)**：抓取 Yahoo 新聞「高麗菜」關鍵字搜尋結果前 10 筆，自動解析相對發布時間（如：X 小時前、X 天前），並在標題前標註原始來源媒體（如 `[三立新聞網] ...`）。

### 2. 歷史去重匯整
* 所有爬取到的新聞會與本地歷史存檔 [news_history.json](file:///c:/Users/User/Desktop/news/news_history.json) 進行去重合併。
* 去重機制以新聞的**唯一網址 (`link`)** 作為 Key 值。
* 合併後的資料會依據民國年日期（如 `115-07-06`）由新到舊排序後寫回檔案。

### 3. 背景排程器 (本地運行環境)
* 在 FastAPI 的 `lifespan` 啟動時，會開啟一個後台 Daemon 執行緒。
* 排程器會計算當前時間距離**每日早上 6:00** 的秒數，並進行精準休眠。
* 時間到達時，自動抓取雙邊新聞並寫入 `news_history.json`。

### 4. GitHub Actions 與 Pages 自動更新 (靜態託管環境)
* **自動爬蟲工作流 (`.github/workflows/crawl.yml`)**：設定於每天台北時間早上 **06:00 (UTC 22:00)** 自動執行 `crawl.py`。
* **GitOps 自動更新**：工作流執行完爬蟲後，若偵測到有新新聞，會自動將更新後的 `news_history.json` 與靜態狀態檔 `status.json` 推送回 GitHub 儲存庫，進而觸發 GitHub Pages 重新部署更新網頁。

---

## API 與靜態資源說明

| HTTP 方法/路徑 | 本地伺服器模式 | GitHub Pages 靜態模式 | 說明 |
| :--- | :--- | :--- | :--- |
| `GET /` | 路由至 `index.html` | 託管並載入 `index.html` | 前端主網頁 |
| `GET /api/news` | 讀取並回傳歷史新聞資料 | Fallback 讀取 `news_history.json` 靜態檔 | 取得匯整後新聞列表 |
| `POST /api/crawl` | 立即手動執行爬蟲與去重 | 提示僅支援本地環境，引導等待 Actions 自動更新 | 手動觸發即時爬網 |
| `GET /api/status` | 取得本地排程器運行狀態 | Fallback 讀取 `status.json` 靜態檔 | 取得最後/下次更新時間及總筆數 |

---

## 技術細節
* **網頁解碼**：由於農糧署網站回應之 HTML 有時編碼探測混亂，系統採用 `response.content.decode('utf-8', errors='ignore')` 強制 UTF-8 解碼，確保中文標題與日期解析無誤。
* **日期解析與轉換**：
  - 透過正則表達式 `\d+-\d+-\d+` 提取民國日期字串（如 `115-07-06`），此格式排序相容於標準字串排序。
  - 對於 Yahoo 新聞的相對時間描述（如 `21 小時前`、`1 天前` 等），系統會利用台北時間 (UTC+8) 的時間基準，自動回推並轉換為對應的民國年月日。
* **反阻擋機制 (PTT Scraper)**：
  - PTT 爬蟲在抓取看板文章時會利用 `requests.Session()` 維持 TCP/SSL 持續連接。
  - 進入文章內頁解析精確日期時，引入 `time.sleep(0.2)` 的微小休眠延遲，能有效防止 PTT 伺服器丟出 Connection Reset 阻斷連線。
* **GitHub Pages 部署必要設定**：
  - 必須在儲存庫的 **Settings** -> **Actions** -> **General** 下將 **Workflow permissions** 改為 **Read and write permissions**，允許 Actions 推送更新後的 JSON。
  - 在 **Settings** -> **Pages** 下將 **Build and deployment** 設定為從 `main` 分支的 `/ (root)` 部署。
