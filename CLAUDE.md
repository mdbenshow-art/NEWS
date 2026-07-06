# 農業與農糧署新聞排程匯整系統說明書 (CLAUDE.md)

本專案是一個基於 FastAPI 的自動化農業新聞爬蟲與去重匯整系統，負責每日定時爬取 **農業部** 與 **農糧署** 的最新新聞並整合存檔。

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
* 測試農糧署爬蟲邏輯：
  `python scratch/test_afa_crawl.py`
* 測試編碼探測邏輯：
  `python scratch/inspect_afa.py`

---

## 系統架構設計

### 1. 爬蟲模組
* **農業部爬蟲 (`scrape_moa_news`)**：抓取最新 10 筆新聞。
* **農糧署爬蟲 (`scrape_afa_news`)**：抓取 [農糧署農業新聞](https://www.afa.gov.tw/cht/index.php?code=list&ids=307) 最新 10 筆新聞。由於第一頁可能不足 10 筆，系統支援**跨分頁爬取**，會自動請求下一頁直到集滿 10 筆為止。

### 2. 歷史去重匯整
* 所有爬取到的新聞會與本地歷史存檔 [news_history.json](file:///c:/Users/User/Desktop/news/news_history.json) 進行去重合併。
* 去重機制以新聞的**唯一網址 (`link`)** 作為 Key 值。
* 合併後的資料會依據民國年日期（如 `115-07-06`）由新到舊排序後寫回檔案。

### 3. 背景排程器
* 在 FastAPI 的 `lifespan` 啟動時，會開啟一個後台 Daemon 執行緒。
* 排程器會計算當前時間距離**每日早上 6:00** 的秒數，並進行精準休眠。
* 時間到達時，自動抓取雙邊新聞並寫入 `news_history.json`。
* 伺服器關閉時，排程器會安全釋放，避免程序殘留。

---

## API 接口說明

| HTTP 方法 | 路由 | 說明 |
| :--- | :--- | :--- |
| `GET` | `/` | 系統前端 HTML 主頁面 |
| `GET` | `/api/news` | 讀取並回傳匯整後的新聞列表（若存檔不存在則自動初始化爬取） |
| `POST` | `/api/crawl` | 立即手動執行一次爬蟲並匯整，回傳最新的去重資料 |
| `GET` | `/api/status` | 取得排程器狀態（如最後執行時間、下次執行時間、總筆數） |

---

## 技術細節
* **網頁解碼**：由於農糧署網站回應之 HTML 有時編碼探測混亂，系統採用 `response.content.decode('utf-8', errors='ignore')` 強制 UTF-8 解碼，確保中文標題與日期解析無誤。
* **日期解析**：透過正則表達式 `\d+-\d+-\d+` 提取民國日期字串（如 `115-07-06`），此格式排序相容於標準字串排序。
