#需安裝ffmpeg https://ffmpeg.org/download.html
#記得將 bin 加入系統環境變數 (例如 C:\ffmpeg\bin)

import yt_dlp
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def check_ffmpeg_installed():
    return shutil.which("ffmpeg") is not None

class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 音樂轉換mp3")
        self.root.geometry("600x600")
        self.root.resizable(False, False)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TLabelframe.Label", font=("標楷體", 12, "bold"))  # 更改所有 LabelFrame 的標題字體

        
        self.download_thread = None
        self.stop_download = False
        
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(
            main_frame, 
            text="YouTube 音樂轉換mp3", 
            font=("Helvetica", 20, "bold"),
            foreground="#2c3e50"
        )
        title_label.pack(pady=(0, 20))
        
        # URL 輸入框
        url_frame = ttk.LabelFrame(main_frame, text="YouTube 影片網址", padding=10)
        url_frame.pack(fill=tk.X, pady=5)
        
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(fill=tk.X)
        self.url_entry.bind("<FocusOut>", self.on_url_input)
        self.url_entry.bind("<Return>", self.on_url_input)
        self.url_entry.insert(0, "輸入 YouTube 網址")
        
        # 檔案名稱輸入框
        filename_frame = ttk.LabelFrame(main_frame, text="自訂檔名（輸入網址後點擊下方空格）", padding=10)
        filename_frame.pack(fill=tk.X, pady=5)

        self.filename_var = tk.StringVar()
        self.filename_entry = ttk.Entry(filename_frame, textvariable=self.filename_var)
        self.filename_entry.pack(fill=tk.X)
        
        # 下載設定
        settings_frame = ttk.LabelFrame(main_frame, text="下載設定", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 音質選擇
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(quality_frame, text="音質 : (KBPS)").pack(anchor=tk.W)
        self.quality_var = tk.StringVar(value="320")
        quality_options = ["320 (最佳)", "256", "192", "128", "96 (最低)"]
        self.quality_combo = ttk.Combobox(
            quality_frame, 
            textvariable=self.quality_var,
            values=quality_options,
            state="readonly"
        )
        self.quality_combo.pack(fill=tk.X)
        
        # 採樣率選擇
        sample_rate_frame = ttk.Frame(settings_frame)
        sample_rate_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(sample_rate_frame, text="採樣率 : (Hz)").pack(anchor=tk.W)
        self.sample_rate_var = tk.StringVar(value="44100")
        sample_rate_options = ["48000", "44100 (CD 品質)", "32000", "22050", "16000", "8000 (電話音質)"]

        self.sample_rate_combo = ttk.Combobox(
            sample_rate_frame, 
            textvariable=self.sample_rate_var,
            values=sample_rate_options,
            state="readonly"
        )
        self.sample_rate_combo.pack(fill=tk.X)
        
        # 保存位置
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Label(save_frame, text="保存位置:").pack(anchor=tk.W)
        
        self.save_path_var = tk.StringVar(value=os.path.expanduser("C:/Users/user/OneDrive/Desktop"))
        save_path_entry = ttk.Entry(save_frame, textvariable=self.save_path_var)
        save_path_entry.pack(fill=tk.X)
        
        browse_btn = ttk.Button(
            save_frame, 
            text="瀏覽", 
            command=self.browse_directory
        )
        browse_btn.pack(pady=5)
        
        # 進度條
        self.progress = ttk.Progressbar(
            main_frame, 
            orient=tk.HORIZONTAL, 
            length=400, 
            mode='determinate'
        )
        self.progress.pack(pady=20)
        
        # 狀態標籤
        self.status_var = tk.StringVar(value="準備就緒")
        status_label = ttk.Label(
            main_frame, 
            textvariable=self.status_var,
            foreground="#7f8c8d",
            font=("Arial", 16, "bold")
        )
        status_label.pack()
        
        # 下載按鈕
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        self.download_btn = ttk.Button(
            btn_frame, 
            text="開始下載", 
            command=self.start_download,
            style="Accent.TButton"
        )
        self.download_btn.pack(side=tk.LEFT, padx=10)
        
        self.cancel_btn = ttk.Button(
            btn_frame, 
            text="取消", 
            command=self.cancel_download,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=10)
        
        # 按鈕樣式
        self.style.configure('Accent.TButton', foreground='white', background='#3498db')
        self.style.map('Accent.TButton', 
                      background=[('active', '#2980b9'), ('disabled', '#bdc3c7')])
    
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if directory:
            self.save_path_var.set(directory)
            
    def fetch_video_title(self, url):
        try:
            # 先檢查是否是播放清單中的單一影片
            if "&list=" in url and "&index=" in url:
                # 提取影片ID部分（移除播放清單參數）
                video_id = url.split("&list=")[0].replace("https://www.youtube.com/watch?v=", "")
                # 重新構建只包含影片ID的URL
                video_url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                video_url = url

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'noplaylist': True,  # 強制只處理單一影片
                'extract_flat': False,  # 獲取完整資訊
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                if info is None:
                    return "unknown_title"
                
                # 直接返回影片標題
                return info.get('title', 'unknown_title')
                
        except Exception as e:
            print("抓取標題錯誤：", e)
            return "unknown_title"
    
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url or ("youtube.com" not in url and "youtu.be" not in url):
            messagebox.showwarning("警告", "請輸入有效的 YouTube 影片網址！")
            return
            
        download_dir = self.save_path_var.get()
        if not download_dir:
            messagebox.showwarning("警告", "請選擇保存目錄！")
            return
        
        if not check_ffmpeg_installed():
            messagebox.showerror("錯誤", "無法找到 ffmpeg，請先安裝並加入系統環境變數。\n教學：https://ffmpeg.org/download.html")
            return
        
        # 從選項中提取數字（例如 "320 (最佳)" → "320"）
        quality = self.quality_var.get().split()[0]
        sample_rate = self.sample_rate_var.get().split()[0]
        
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress["value"] = 0
        self.status_var.set("準備下載...")
        
        # 啟動下載線程
        self.stop_download = False
        self.download_thread = Thread(
            target=self.download_audio,
            args=(url, download_dir, quality, sample_rate),
            daemon=True
        )
        self.download_thread.start()
    
    def download_audio(self, url, download_dir, quality, sample_rate):
        try:
            os.makedirs(download_dir, exist_ok=True)
            
            def progress_hook(d):
                if self.stop_download:
                    raise Exception("下載已取消")
                    
                if d['status'] == 'downloading':
                    try:
                        if d.get('downloaded_bytes') and d.get('total_bytes'):
                            percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                        elif '_percent_str' in d:
                            # 清除 ANSI 顏色轉義碼再轉成 float
                            clean_percent = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', d['_percent_str']).replace('%', '').strip()
                            percent = float(clean_percent)
                        else:
                            percent = 0.0

                        self.progress["value"] = percent
                        self.status_var.set(f"下載中... {percent:.1f}%")
                        self.root.update_idletasks()
                    except Exception:
                        pass
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_dir, sanitize_filename(self.filename_var.get()) + '.%(ext)s') if self.filename_var.get().strip() else os.path.join(download_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'noplaylist': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality,
                }],
                'postprocessor_args': ['-ar', sample_rate],
                'prefer_ffmpeg': True,
                'progress_hooks': [progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if not self.stop_download:
                self.status_var.set(f"下載完成！已保存到: {download_dir}")
                messagebox.showinfo("完成", f"下載完成！\n文件已保存到: {download_dir}")
        
        except Exception as e:
            if not self.stop_download:
                self.status_var.set("下載失敗")
                messagebox.showerror("錯誤", f"下載失敗: {str(e)}")
        
        finally:
            self.reset_ui()
    
    def cancel_download(self):
        self.stop_download = True
        self.status_var.set("下載已取消")
        self.reset_ui()
    
    def reset_ui(self):
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.stop_download = False
        self.download_thread = None
        
    def on_url_input(self, event=None):
        url = self.url_entry.get().strip()
        if "youtube.com" in url or "youtu.be" in url:
            self.status_var.set("正在取得影片標題...")
            self.root.update_idletasks()
            try:
                title = self.fetch_video_title(url)
                self.filename_var.set(sanitize_filename(title))
                self.status_var.set("已自動填入檔名")
            except Exception as e:
                self.status_var.set("取得標題失敗")
                print(f"取得標題錯誤: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()