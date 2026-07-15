import os
import json
import datetime
from server import scrape_afa_news, scrape_moa_news, scrape_ptt_fruits, scrape_agriharvest_news, consolidate_and_save, scheduler_status

def main():
    print("==================================================")
    print(" 開始執行 GitHub Actions 自動化新聞爬取與更新...")
    print("==================================================")
    
    # 執行爬蟲，抓取最新新聞
    print("[1/4] 正在爬取農糧署新聞...")
    try:
        afa_news = scrape_afa_news(10)
        print(f" -> 農糧署新聞爬取完成，共 {len(afa_news)} 筆。")
    except Exception as e:
        print(f" -> [錯誤] 爬取農糧署新聞失敗: {e}")
        afa_news = []
        
    print("[2/4] 正在爬取農業部新聞...")
    try:
        moa_news = scrape_moa_news(10)
        print(f" -> 農業部新聞爬取完成，共 {len(moa_news)} 筆。")
    except Exception as e:
        print(f" -> [錯誤] 爬取農業部新聞失敗: {e}")
        moa_news = []
        
    print("[3/5] 正在爬取 PTT Fruits 板新聞...")
    try:
        ptt_news = scrape_ptt_fruits(10)
        print(f" -> PTT Fruits 新聞爬取完成，共 {len(ptt_news)} 筆。")
    except Exception as e:
        print(f" -> [錯誤] 爬取 PTT Fruits 新聞失敗: {e}")
        ptt_news = []
        
    print("[4/5] 正在爬取農傳媒新聞...")
    try:
        agri_news = scrape_agriharvest_news(10)
        print(f" -> 農傳媒新聞爬取完成，共 {len(agri_news)} 筆。")
    except Exception as e:
        print(f" -> [錯誤] 爬取農傳媒新聞失敗: {e}")
        agri_news = []
        
    # 合併並儲存
    all_news = afa_news + moa_news + ptt_news + agri_news
    if all_news:
        print("[5/5] 正在整合新聞資料並寫入歷史檔案...")
        consolidate_and_save(all_news)
    else:
        print("[5/5] 無法取得任何新聞資料，跳過整合步驟。")
        
    # 產生 status.json 狀態檔供靜態網頁讀取
    status_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")
    
    # 台北時間 (UTC+8) 轉換
    tz_utc8 = datetime.timezone(datetime.timedelta(hours=8))
    now_utc8 = datetime.datetime.now(datetime.timezone.utc).astimezone(tz_utc8)
    
    # 計算下一次爬取時間 (台北時間明天的早上 6 點)
    target_utc8 = now_utc8.replace(hour=6, minute=0, second=0, microsecond=0)
    if target_utc8 <= now_utc8:
        target_utc8 += datetime.timedelta(days=1)
        
    # 讀取當前歷史紀錄筆數 (以確保數字正確)
    total_records = scheduler_status["total_records"]
    history_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_history.json")
    if os.path.exists(history_file_path):
        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)
                total_records = len(history_data)
        except Exception:
            pass
            
    status_data = {
        "status": "GitHub Pages (自動更新)",
        "next_crawl_time": target_utc8.strftime("%Y-%m-%d %H:%M:%S") + " (UTC+8)",
        "last_crawl_time": now_utc8.strftime("%Y-%m-%d %H:%M:%S") + " (UTC+8)",
        "total_records": total_records
    }
    
    try:
        with open(status_file_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=4)
        print(f" -> 狀態檔 status.json 更新成功！(總筆數: {total_records} 筆)")
    except Exception as e:
        print(f" -> [錯誤] 更新 status.json 失敗: {e}")
        
    print("==================================================")
    print(" 爬取與狀態更新任務已完成。")
    print("==================================================")

if __name__ == "__main__":
    main()
