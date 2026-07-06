import os
import sys
import subprocess
import webbrowser
import time
import threading

def open_browser():
    # 延遲兩秒等待伺服器啟動完成後再開啟瀏覽器
    time.sleep(2.5)
    print("正在開啟網頁瀏覽器...")
    webbrowser.open("http://127.0.0.1:8000")

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(workspace, ".venv")
    
    # 1. 建立虛擬環境 (.venv)
    if not os.path.exists(venv_dir):
        print("正在建立 Python 虛擬環境 (.venv)，請稍候...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True, cwd=workspace)
            print("虛擬環境建立成功。")
        except subprocess.CalledProcessError as e:
            print(f"建立虛擬環境時發生錯誤: {e}")
            sys.exit(1)
            
    # 2. 決定 Windows 環境下的執行檔路徑
    pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    
    # 若為非 Windows 系統之相容處理
    if not os.path.exists(pip_exe):
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")
        
    # 3. 安裝 requirements.txt 所列套件
    requirements_path = os.path.join(workspace, "requirements.txt")
    if os.path.exists(requirements_path):
        print("正在透過虛擬環境安裝必要套件 (fastapi, uvicorn, requests, beautifulsoup4)...")
        try:
            subprocess.run([pip_exe, "install", "-r", "requirements.txt"], check=True, cwd=workspace)
            print("必要套件安裝成功！")
        except subprocess.CalledProcessError as e:
            print(f"安裝套件時發生錯誤: {e}")
            sys.exit(1)
            
    # 4. 啟動非同步執行緒以自動開啟瀏覽器
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 5. 啟動 FastAPI 伺服器
    print("\n" + "="*50)
    print(" 正在啟動 FastAPI 新聞爬蟲伺服器...")
    print(" 服務網址: http://127.0.0.1:8000")
    print(" 按 Ctrl + C 可停止伺服器。")
    print("="*50 + "\n")
    
    try:
        # 使用虛擬環境的 python 執行 server.py
        subprocess.run([python_exe, "server.py"], check=True, cwd=workspace)
    except KeyboardInterrupt:
        print("\n伺服器已手動停止。")
    except Exception as e:
        print(f"\n伺服器執行過程中發生錯誤: {e}")

if __name__ == "__main__":
    main()
