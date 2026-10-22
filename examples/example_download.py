import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from downloader import VideoDownloader

dl = VideoDownloader(output_dir="downloads")

# Ví dụ 1: Tải video TikTok / Douyin sạch không logo
url = "https://www.youtube.com/watch?v=BaW_jenozKc"  # Youtube 8s demo
print(f"Đang tải video: {url}")

info = dl.download_video(url, max_height=1080)
print(f"[THÀNH CÔNG] Đã lưu video: {info['video_path']}")
print(f"Tiêu đề: {info['title']}")
print(f"Thời lượng: {info['duration']} giây")
print(f"Nền tảng: {info['platform'].upper()}")
