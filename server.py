import urllib.parse
import os
import requests
import json
import datetime
import time
import threading
import re
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# 全域排程狀態
scheduler_status = {
    "last_crawl_time": "尚未執行",
    "next_crawl_time": "計算中...",
    "total_records": 0,
    "status": "Running"
}

# 爬取農業部新聞
def scrape_moa_news(limit=10):
    url = "https://www.moa.gov.tw/theme_list.php?theme=news&sub_theme=agri"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[Crawler] MOA fetch failed: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("div", class_="no-more-tables")
    if not table:
        return []
        
    tbody = table.find("tbody")
    if not tbody:
        return []
        
    rows = tbody.find_all("tr")
    news_items = []
    
    for row in rows:
        if len(news_items) >= limit:
            break
            
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
            
        doc_id = cells[0].text.strip()
        date = cells[1].text.strip()
        
        # 清理日期以符合 ROC YYY-MM-DD
        match = re.search(r'\d+-\d+-\d+', date)
        if match:
            date = match.group(0)
            
        title_cell = cells[2]
        a_tag = title_cell.find("a")
        if not a_tag:
            continue
            
        title = a_tag.get("title", "").strip() or a_tag.text.strip()
        rel_link = a_tag.get("href", "").strip()
        full_link = urllib.parse.urljoin("https://www.moa.gov.tw/", rel_link)
        
        news_items.append({
            "source": "農業部",
            "doc_id": doc_id,
            "date": date,
            "title": title,
            "link": full_link
        })
        
    return news_items

# 爬取農糧署新聞
def scrape_afa_news(limit=10):
    news_items = []
    page = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    while len(news_items) < limit:
        url = "https://www.afa.gov.tw/cht/index.php?code=list&ids=307"
        if page > 1:
            url += f"&page={page}"
            
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[Crawler] AFA page {page} fetch failed: {e}")
            break
            
        text = response.content.decode('utf-8', errors='ignore')
        soup = BeautifulSoup(text, "html.parser")
        
        items = soup.select("a.agricultural-news")
        if not items:
            break
            
        page_added = 0
        for item in items:
            if len(news_items) >= limit:
                break
                
            href = item.get("href", "")
            full_link = urllib.parse.urljoin("https://www.afa.gov.tw/cht/", href)
            
            title = item.get("title", "").strip()
            h3 = item.find("h3")
            if not title and h3:
                title = h3.get_text(strip=True)
                
            ribbon = item.find("div", class_="agricultural-news-ribbon")
            date_str = ""
            if ribbon:
                span = ribbon.find("span")
                if span and len(span.contents) > 0:
                    date_str = str(span.contents[0]).strip()
                    match = re.search(r'\d+-\d+-\d+', date_str)
                    if match:
                        date_str = match.group(0)
                    
            parsed_href = urllib.parse.urlparse(full_link)
            params = urllib.parse.parse_qs(parsed_href.query)
            article_id = params.get('article_id', [''])[0] or ""
            
            if title and full_link:
                news_items.append({
                    "source": "農糧署",
                    "doc_id": article_id,
                    "date": date_str,
                    "title": title,
                    "link": full_link
                })
                page_added += 1
                
        if page_added == 0:
            break
            
        page += 1
        
    return news_items

# 爬取 PTT Fruits 板文章
def scrape_ptt_fruits(limit=10):
    url = "https://www.ptt.cc/bbs/Fruits/index.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": "over18=1"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[Crawler] PTT Fruits fetch failed: {e}")
        return []
        
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 篩選掉置底公告（置底公告在 <div class="r-list-sep"></div> 之後）
    sep = soup.find("div", class_="r-list-sep")
    if sep:
        r_ents = sep.find_previous_siblings("div", class_="r-ent")
    else:
        r_ents = list(reversed(soup.find_all("div", class_="r-ent")))
        
    news_items = []
    
    for rent in r_ents:
        if len(news_items) >= limit:
            break
            
        title_div = rent.find("div", class_="title")
        if not title_div:
            continue
            
        a_tag = title_div.find("a")
        if not a_tag:
            continue
            
        title = a_tag.text.strip()
        href = a_tag.get("href", "")
        full_link = f"https://www.ptt.cc{href}"
        
        doc_id_match = re.search(r'\/bbs\/Fruits\/(M\.\d+\.A\.[A-Za-z0-9]+)\.html', href)
        doc_id = doc_id_match.group(1) if doc_id_match else ""
        
        date_div = rent.find("div", class_="date")
        date_list_str = date_div.text.strip() if date_div else ""
        
        # 抓取文章內頁以取得精確的完整發文時間（含年份）
        try:
            art_resp = requests.get(full_link, headers=headers, timeout=5)
            art_resp.encoding = 'utf-8'
            art_soup = BeautifulSoup(art_resp.text, "html.parser")
            
            meta_lines = art_soup.find_all("div", class_="article-metaline")
            date_parsed = None
            for line in meta_lines:
                tag = line.find("span", class_="article-meta-tag")
                val = line.find("span", class_="article-meta-value")
                if tag and val and tag.text == "時間":
                    date_parsed = val.text.strip()
                    break
            
            if date_parsed:
                months = {
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                }
                parts = re.split(r'\s+', date_parsed)
                if len(parts) >= 5:
                    month_name = parts[1]
                    day = parts[2]
                    year = parts[4]
                    
                    month = months.get(month_name, "01")
                    if len(day) == 1:
                        day = "0" + day
                    
                    try:
                        g_year = int(year)
                        roc_year = g_year - 1911
                        date_str = f"{roc_year}-{month}-{day}"
                    except ValueError:
                        date_str = date_list_str.replace("/", "-")
                else:
                    date_str = date_list_str.replace("/", "-")
            else:
                date_str = date_list_str.replace("/", "-")
        except Exception as e:
            print(f"[Crawler] PTT Fruits fetch article details failed for {full_link}: {e}")
            date_str = date_list_str.replace("/", "-")
            
        news_items.append({
            "source": "PTT Fruits",
            "doc_id": doc_id,
            "date": date_str,
            "title": title,
            "link": full_link
        })
        
    return news_items

# 爬取農傳媒新聞
def scrape_agriharvest_news(limit=10):
    url = "https://www.agriharvest.tw/archives/category/%E6%96%B0%E8%81%9E/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[Crawler] AgrHarvest fetch failed: {e}")
        return []
        
    html_content = response.content.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html_content, "html.parser")
    
    post_titles = soup.find_all("a", class_="post-title")
    news_items = []
    
    for a_tag in post_titles:
        if len(news_items) >= limit:
            break
            
        title = a_tag.get_text().strip()
        link = a_tag.get("href", "").strip()
        if not link:
            continue
            
        full_link = urllib.parse.urljoin("https://www.agriharvest.tw/", link)
        doc_id_match = re.search(r'/archives/(\d+)', full_link)
        doc_id = doc_id_match.group(1) if doc_id_match else ""
        
        # Locate the date element (could be in parent or grandparent)
        date_li = None
        parent = a_tag.parent
        if parent:
            date_li = parent.find("li", class_="post-date")
            if not date_li:
                grandparent = parent.parent
                if grandparent:
                    date_li = grandparent.find("li", class_="post-date")
                    
        date_str = ""
        if date_li:
            raw_date = date_li.get_text().strip()
            # Convert raw_date (e.g., "20260714") to ROC date (e.g., "115-07-14")
            if re.match(r'^\d{8}$', raw_date):
                try:
                    year = int(raw_date[:4])
                    month = raw_date[4:6]
                    day = raw_date[6:8]
                    roc_year = year - 1911
                    date_str = f"{roc_year}-{month}-{day}"
                except ValueError:
                    date_str = raw_date
            else:
                date_str = raw_date
                
        news_items.append({
            "source": "農傳媒",
            "doc_id": doc_id,
            "date": date_str,
            "title": title,
            "link": full_link
        })
        
    return news_items

# 匯整並存檔去重
def consolidate_and_save(new_items):
    file_path = os.path.join(os.path.dirname(__file__), "news_history.json")
    existing_items = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
        except Exception as e:
            print(f"[Consolidation] 讀取歷史檔案失敗: {e}")
            
    # 使用網址作為唯一識別碼進行去重
    existing_links = {item["link"] for item in existing_items}
    
    added_count = 0
    for item in new_items:
        if item["link"] not in existing_links:
            existing_items.append(item)
            existing_links.add(item["link"])
            added_count += 1
            
    # 依日期由新到舊排序 (ROC 民國日期如 115-07-06 排序規則相容)
    existing_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # 寫入檔案
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_items, f, ensure_ascii=False, indent=4)
        print(f"[Consolidation] 成功去重合併：新增 {added_count} 筆，總計 {len(existing_items)} 筆。")
        scheduler_status["total_records"] = len(existing_items)
        scheduler_status["last_crawl_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"[Consolidation] 寫入歷史檔案失敗: {e}")
        
    return existing_items

# 定時排程主迴圈 (每日 6:00 執行)
def scheduler_loop(stop_event: threading.Event):
    print("[Scheduler] 農業/農糧署新聞排程已啟動。每日 6:00 定時執行。")
    
    # 首次啟動時如果沒有歷史檔案，先爬取一次作為初始化
    file_path = os.path.join(os.path.dirname(__file__), "news_history.json")
    if not os.path.exists(file_path):
        print("[Scheduler] 偵測到歷史檔案不存在，執行首次爬取初始化...")
        try:
            afa_news = scrape_afa_news(10)
            moa_news = scrape_moa_news(10)
            ptt_news = scrape_ptt_fruits(10)
            agri_news = scrape_agriharvest_news(10)
            consolidate_and_save(afa_news + moa_news + ptt_news + agri_news)
        except Exception as e:
            print(f"[Scheduler] 首次初始化爬取失敗: {e}")
            
    while not stop_event.is_set():
        now = datetime.datetime.now()
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        
        # 若今天的 6:00 已過，則設定為明天的 6:00
        if target <= now:
            target += datetime.timedelta(days=1)
            
        delay = (target - now).total_seconds()
        scheduler_status["next_crawl_time"] = target.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Scheduler] 下次定時爬取時間：{target.strftime('%Y-%m-%d %H:%M:%S')}，距離現在還有 {delay:.1f} 秒")
        
        # 使用 event wait 進行可中斷的休眠
        if stop_event.wait(delay):
            print("[Scheduler] 收到停止訊號，排程執行緒退出。")
            break
            
        print("[Scheduler] 定時爬蟲觸發！開始執行每日新聞抓取...")
        try:
            afa_news = scrape_afa_news(10)
            moa_news = scrape_moa_news(10)
            ptt_news = scrape_ptt_fruits(10)
            agri_news = scrape_agriharvest_news(10)
            consolidate_and_save(afa_news + moa_news + ptt_news + agri_news)
            print("[Scheduler] 定時新聞爬取與匯整成功。")
        except Exception as e:
            print(f"[Scheduler] 定時爬取執行時發生錯誤: {e}")

# FastAPI Lifespan 生命週期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化歷史紀錄筆數
    file_path = os.path.join(os.path.dirname(__file__), "news_history.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                scheduler_status["total_records"] = len(data)
        except Exception:
            pass
            
    stop_event = threading.Event()
    thread = threading.Thread(target=scheduler_loop, args=(stop_event,), daemon=True)
    thread.start()
    yield
    # Shutdown
    stop_event.set()
    thread.join(timeout=1.0)

app = FastAPI(title="農業與農糧署新聞排程匯整系統", lifespan=lifespan)

# API: 取得新聞列表
@app.get("/api/news")
def get_news():
    file_path = os.path.join(os.path.dirname(__file__), "news_history.json")
    if not os.path.exists(file_path):
        # 檔案不存在則立即進行一次爬取
        afa_news = scrape_afa_news(10)
        moa_news = scrape_moa_news(10)
        ptt_news = scrape_ptt_fruits(10)
        agri_news = scrape_agriharvest_news(10)
        consolidate_and_save(afa_news + moa_news + ptt_news + agri_news)
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"error": None, "data": data}
    except Exception as e:
        return {"error": f"讀取新聞歷史失敗: {str(e)}", "data": []}

# API: 手動立即爬取
@app.post("/api/crawl")
def manual_crawl():
    try:
        print("[Manual Crawl] 收到手動爬取要求，開始爬取最新新聞...")
        afa_news = scrape_afa_news(10)
        moa_news = scrape_moa_news(10)
        ptt_news = scrape_ptt_fruits(10)
        agri_news = scrape_agriharvest_news(10)
        data = consolidate_and_save(afa_news + moa_news + ptt_news + agri_news)
        return {"error": None, "message": "手動爬取與匯整成功完成！", "data": data}
    except Exception as e:
        return {"error": f"手動爬取失敗: {str(e)}", "data": []}

# API: 取得排程與狀態
@app.get("/api/status")
def get_status():
    file_path = os.path.join(os.path.dirname(__file__), "news_history.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                scheduler_status["total_records"] = len(data)
        except Exception:
            pass
            
    # 計算下一次排程時間
    now = datetime.datetime.now()
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    scheduler_status["next_crawl_time"] = target.strftime("%Y-%m-%d %H:%M:%S")
    
    return scheduler_status

@app.get("/", response_class=HTMLResponse)
def read_root():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h3>index.html 檔案不存在，請確認路徑。</h3>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

