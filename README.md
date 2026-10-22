# AI Video Downloader, Translator & Auto-Dubbing Pipeline 🎬🇻🇳

Hệ thống mã nguồn mở hoàn chỉnh phục vụ:
1. **Tải video chất lượng cao không logo/watermark** từ đa nền tảng: Douyin (抖音), TikTok, YouTube (Shorts & Long), Facebook Reels, Bilibili, Kuaishou (快手), Instagram, X/Twitter.
2. **Quy trình tự động Việt hóa & lồng tiếng thông minh (End-to-End Dubbing):** Tách tiếng (ASR Whisper) ➔ Dịch thuật ngữ cảnh video (AI Translator) ➔ Tạo giọng lồng tiếng ElevenLabs miễn phí (Voice Synthesis) ➔ Tự động co giãn tốc độ (Atempo time-stretching) ➔ Giảm âm lượng nhạc nền (Audio Ducking) ➔ Xuất video hoàn thiện kèm Vietsub!

---

## 📑 MỤC LỤC
- [Phần 1: Cách Download Video Từ Nhiều Nguồn Sạch Không Logo](#phần-1-cách-download-video-từ-nhiều-nguồn-sạch-không-logo)
  - [1.1. Các nền tảng hỗ trợ](#11-các-nền-tảng-hỗ-trợ)
  - [1.2. Hướng dẫn sử dụng CLI](#12-hướng-dẫn-sử-dụng-cli)
  - [1.3. Hướng dẫn sử dụng trong code Python](#13-hướng-dẫn-sử-dụng-trong-code-python)
- [Phần 2: Hướng Dẫn Cài Đặt Môi Trường & Thư Viện Cần Thiết](#phần-2-hướng-dẫn-cài-đặt-môi-trường--thư-viện-cần-thiết)
  - [2.1. Cài đặt FFmpeg (Bắt buộc)](#21-cài-đặt-ffmpeg-bắt-buộc)
  - [2.2. Cài đặt Python & PyTorch (CUDA GPU vs CPU)](#22-cài-đặt-python--pytorch-cuda-gpu-vs-cpu)
  - [2.3. Cài đặt Faster-Whisper, yt-dlp & các thư viện](#23-cài-đặt-faster-whisper-yt-dlp--các-thư-viện)
- [Phần 3: Quy Trình Việt Hóa & Lồng Tiếng Tự Động](#phần-3-quy-trình-việt-hóa--lồng-tiếng-tự-động)
  - [3.1. Sơ đồ kiến trúc xử lý](#31-sơ-đồ-kiến-trúc-xử-lý)
  - [3.2. Bóc tách phụ đề & Timestamps (Speech-to-Text)](#32-bóc-tách-phụ-đề--timestamps-speech-to-text)
  - [3.3. Dịch thuật theo ngữ cảnh video (AI Translator)](#33-dịch-thuật-theo-ngữ-cảnh-video-ai-translator)
  - [3.4. Lồng tiếng ElevenLabs miễn phí & Khớp khẩu hình](#34-lồng-tiếng-elevenlabs-miễn-phí--khớp-khẩu-hình)
  - [3.5. Trộn âm thanh (Audio Ducking) & Render video hoàn thiện](#35-trộn-âm-thanh-audio-ducking--render-video-hoàn-thiện)
  - [3.6. Chạy quy trình trọn gói bằng 1 dòng lệnh](#36-chạy-quy-trình-trọn-gói-bằng-1-dòng-lệnh)
- [Danh sách giọng đọc ElevenLabs & CapCut tiêu biểu](#danh-sách-giọng-đọc-elevenlabs--capcut-tiêu-biểu)
- [Bảng thông số model Whisper](#bảng-thông-số-model-whisper)

---

## PHẦN 1: CÁCH DOWNLOAD VIDEO TỪ NHIỀU NGUỒN SẠCH KHÔNG LOGO

### 1.1. Các nền tảng hỗ trợ
Module `VideoDownloader` tự động nhận diện và trích xuất link video stream sạch nhất (hạn chế tối đa watermark và logo thừa):
- **Douyin (抖音):** Hỗ trợ link rút gọn di động (`https://v.douyin.com/...`) và web (`https://www.douyin.com/video/...`).
- **TikTok:** Hỗ trợ link `vt.tiktok.com` và `tiktok.com/@user/video/...`.
- **YouTube:** Hỗ trợ cả YouTube Shorts, Video chuẩn, Live archive, tách audio 320kbps.
- **Facebook:** Hỗ trợ Facebook Reels, Watch (`fb.watch`).
- **Bilibili:** Hỗ trợ link `bilibili.com/video/BV...` tải chuẩn HD.
- **Kuaishou (快手), Instagram Reels, X/Twitter.**

### 1.2. Hướng dẫn sử dụng CLI
Bạn có thể tải bất kỳ video nào qua dòng lệnh cực kỳ tiện lợi:

```bash
# 1. Tải video Douyin/TikTok chất lượng cao nhất:
python -m downloader.cli "https://v.douyin.com/iJXXXXX/" -o downloads/

# 2. Tải video YouTube ở độ phân giải tối đa 1080p:
python -m downloader.cli "https://www.youtube.com/watch?v=XXXXXX" --quality 1080

# 3. Chỉ tải track âm thanh (MP3 320kbps) phục vụ dịch/tách nhạc:
python -m downloader.cli "https://www.youtube.com/watch?v=XXXXXX" -a -o downloads/
```

### 1.3. Hướng dẫn sử dụng trong code Python
```python
from downloader import VideoDownloader

dl = VideoDownloader(output_dir="downloads")

# Tải video:
info = dl.download_video("https://v.douyin.com/iJXXXXX/", max_height=1080)
print(f"File đã tải: {info['video_path']}")
print(f"Tiêu đề: {info['title']}")
print(f"Thời lượng: {info['duration']} giây")

# Chỉ tải file âm thanh:
audio_path = dl.download_audio("https://www.youtube.com/watch?v=XXXXXX")
```

---

## PHẦN 2: HƯỚNG DẪN CÀI ĐẶT MÔI TRƯỜNG & THƯ VIỆN CẦN THIẾT

### 2.1. Cài đặt FFmpeg (Bắt buộc)
FFmpeg là công cụ xương sống để cắt, ghép âm thanh, chỉnh tốc độ tempo và render video.

- **Trên Windows:**
  1. Tải bản build đầy đủ từ [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip).
  2. Giải nén vào `C:\ffmpeg`.
  3. Thêm `C:\ffmpeg\bin` vào **System Environment Variables (PATH)**.
  4. Mở Command Prompt kiểm tra: `ffmpeg -version`.
- **Trên macOS:**
  ```bash
  brew install ffmpeg
  ```
- **Trên Ubuntu / Debian Linux:**
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

---

### 2.2. Cài đặt Python & PyTorch (CUDA GPU vs CPU)
Khuyến nghị sử dụng **Python 3.10, 3.11 hoặc 3.12**.

- **Nếu máy có Card đồ họa NVIDIA (Khuyên dùng để Whisper chạy siêu tốc):**
  Cài đặt PyTorch với CUDA 12.1 hoặc 11.8:
  ```bash
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
  ```
- **Nếu chạy trên CPU (Laptop, máy không có GPU rời):**
  ```bash
  pip install torch torchaudio
  ```

---

### 2.3. Cài đặt Faster-Whisper, yt-dlp & các thư viện
Chạy lệnh cài đặt toàn bộ gói phụ thuộc:
```bash
pip install -r requirements.txt
```

Hoặc cài trực tiếp:
```bash
pip install yt-dlp faster-whisper deep-translator requests
```

*(Nếu trên Windows, bạn chỉ cần nháy đúp chuột vào file `setup_env.bat` để script tự động cài đặt).*

---

## PHẦN 3: QUY TRÌNH VIỆT HÓA & LỒNG TIẾNG TỰ ĐỘNG

### 3.1. Sơ đồ kiến trúc xử lý

```text
[ Video Nguồn ] (Douyin / TikTok / YouTube / Bilibili)
      │
      ▼ (yt-dlp)
[ Tải Video Sạch Không Logo ]
      │
      ├─────────────────────────────────────────┐
      │ (Trích xuất Audio 16kHz)                 │ (Giữ lại Video Gốc)
      ▼                                         │
[ Faster-Whisper ASR ]                          │
      │ (Nhận diện câu & mốc thời gian start-end)│
      ▼                                         │
[ AI Translator ] (Gemini / OpenAI / Free)      │
      │ (Dịch chuẩn ngữ cảnh, vừa khẩu hình)     │
      ▼                                         │
[ CapCut ElevenLabs TTS ]                       │
      │ (Tạo giọng lồng tiếng: Adam, Maggie...) │
      ▼                                         │
[ FFmpeg Atempo Time-Stretch ]                  │
      │ (Co giãn tốc độ để khớp thời lượng gốc) │
      ▼                                         │
[ Audio Mixer & Ducking ] ◄─────────────────────┘
      │ (Giảm nhạc nền gốc -14dB khi có thoại)
      ▼
[ Video Hoàn Thiện Vietsub & Lồng Tiếng Việt ]
```

---

### 3.2. Bóc tách phụ đề & Timestamps (Speech-to-Text)
Sử dụng `Faster-Whisper` (nhanh gấp 4 lần so với whisper chuẩn, tốn ít VRAM hơn):

```python
from dubbing.transcribe import Transcriber

transcriber = Transcriber(model_size="base", device="auto")
segments, source_lang = transcriber.transcribe("downloads/video.mp4")

print(f"Ngôn ngữ gốc: {source_lang.upper()}")
# Xuất ra file phụ đề chuẩn SRT:
transcriber.export_srt(segments, "output/original.srt")
```

---

### 3.3. Dịch thuật theo ngữ cảnh video (AI Translator)
Không dịch theo từng từ riêng lẻ! Module `SubtitleTranslator` truyền toàn bộ ngữ cảnh câu chuyện kèm giới hạn thời lượng (`duration`) để AI dịch câu tiếng Việt vừa vặn, gãy gọn:

- **Chế độ miễn phí 100%:** Tự động dùng Google Translate API tích hợp sẵn (không cần key).
- **Chế độ nâng cao với Google Gemini (Miễn phí 15 RPM):**
  ```bash
  set GEMINI_API_KEY=your_gemini_key_here
  ```
- **Chế độ OpenAI (GPT-4o mini):**
  ```bash
  set OPENAI_API_KEY=your_openai_key_here
  ```

Code thực hiện:
```python
from dubbing.translator import SubtitleTranslator

translator = SubtitleTranslator() # Tự động chọn Gemini > OpenAI > Free
translated_segments = translator.translate_segments(segments, target_lang="vi")
```

---

### 3.4. Lồng tiếng ElevenLabs miễn phí & Khớp khẩu hình
Hệ thống sử dụng cổng kết nối **CapCut ElevenLabs Gateway** tích hợp sẵn trong repo (`capcut_client.py`), mang đến:
- Giọng đọc số 1 thế giới: **Adam** (nam trầm), **Maggie** (nữ ngọt ngào), **Alex 1**, **Joanne**, **Josh**...
- **Thuật toán Atempo Time-Stretching:** Nếu câu thoại tiếng Việt đọc dài hơn hoặc ngắn hơn mốc thời gian của người nói trong video gốc >15%, FFmpeg sẽ tự động điều chỉnh tốc độ từ 0.75x đến 1.35x mà **hoàn toàn không làm méo cao độ (pitch)** của giọng nói.

```python
from dubbing.voice_synthesizer import VoiceSynthesizer

synthesizer = VoiceSynthesizer(voice="Adam")
clip_path = synthesizer.synthesize_segment(segment, out_dir="output/clips")
```

---

### 3.5. Trộn âm thanh (Audio Ducking) & Render video hoàn thiện
Video chuyên nghiệp **không bao giờ tắt phụt âm thanh gốc** mà phải giữ lại tiếng động hiện trường, tiếng động cơ, tiếng vỗ tay và nhạc nền BGM:
- Khi có giọng lồng tiếng: Nhạc nền gốc tự động giảm xuống **15% - 20%** (Ducking -14dB).
- Khi người nói dừng lại: Nhạc nền tự động tăng về mức bình thường.
- Khắc trực tiếp phụ đề Vietsub vào video với viền đen bóng mờ chống chói chữ.

```python
from dubbing.audio_mixer import AudioMixer

mixer = AudioMixer()
# Ghép các đoạn thoại lên dòng thời gian chuẩn:
timeline_wav = mixer.build_voice_timeline(segments, segment_clips, total_duration, "dubbed.wav")

# Xuất video hoàn thiện:
mixer.mix_dubbed_video(
    original_video="downloads/video.mp4",
    dubbed_voice_wav=timeline_wav,
    output_video="output/video_vietsub_longtieng.mp4",
    original_volume=0.20,
    burn_subtitles_srt="output/translated_vi.srt"
)
```

---

### 3.6. Chạy quy trình trọn gói bằng 1 dòng lệnh
Tất cả các bước trên đã được gom lại thành class `VideoDubbingPipeline`:

```python
from dubbing.pipeline import VideoDubbingPipeline

# Khởi tạo
pipeline = VideoDubbingPipeline(whisper_model="base", voice="Adam")

# Chạy tự động từ A đến Z:
result = pipeline.process(
    video_path="downloads/video_trung_quoc.mp4",
    output_path="output/video_da_long_tieng.mp4",
    target_lang="vi",
    burn_subtitles=True,
    original_bgm_volume=0.18
)

print(f"Video thành phẩm: {result['output_video']}")
```

---

## 🎙️ DANH SÁCH GIỌNG ĐỌC ELEVENLABS & CAPCUT TIÊU BIỂU

| Tên Giọng | Nền tảng | Giới tính | Thể loại phù hợp |
| :--- | :--- | :--- | :--- |
| **Adam** | ElevenLabs | Nam | Giọng trầm ấm, review phim, tài liệu, kể chuyện số 1 |
| **Maggie** | ElevenLabs | Nữ | Truyền cảm, ngọt ngào, tâm lý, vlog |
| **Alex 1** | ElevenLabs | Nam | Trẻ trung, tin tức công nghệ, hiện đại |
| **Joanne** | ElevenLabs | Nữ | Giới thiệu doanh nghiệp, MC truyền hình |
| **Josh** | ElevenLabs | Nam | Tự sự, ấm áp, sâu sắc |
| **Scarlett** | ElevenLabs | Nữ | Quyến rũ, quảng cáo, thời trang |
| **Late Night Radio** | ElevenLabs | Nam | Radio đêm, tâm sự đêm muộn |
| **Thanh Niên Tự Tin**| CapCut VN | Nam | Review TikTok, tin tức ngắn, hài hước |
| **Cô Gái Hoạt Ngôn** | CapCut VN | Nữ | Review đồ ăn, mỹ phẩm, mẹo vặt |
| **Giọng Nam Trầm** | CapCut VN | Nam | Kể chuyện ma, phim trinh thám, kiếm hiệp |

---

## 📊 BẢNG THÔNG SỐ MODEL WHISPER

| Model | Yêu cầu VRAM | Tốc độ | Độ chính xác | Khuyến nghị sử dụng |
| :--- | :--- | :--- | :--- | :--- |
| **tiny** | ~1 GB | Cực nhanh (32x) | Khá | Test nhanh, máy yếu không có GPU |
| **base** | ~1 GB | Rất nhanh (16x) | Tốt | Video nói rõ ràng, âm thanh sạch |
| **small** | ~2 GB | Nhanh (6x) | Rất tốt | **Khuyên dùng tối ưu cho hầu hết video** |
| **medium** | ~5 GB | Trung bình (2x) | Xuất sắc | Video có tạp âm, nói nhanh |
| **large-v3** | ~10 GB | Chậm (1x) | Cao nhất | Phim dài tập, tiếng địa phương khó |

---

## ⚖️ License
Mã nguồn phát hành theo giấy phép **MIT**. Bạn hoàn toàn được phép tự do sử dụng, chỉnh sửa và tích hợp vào các dự án cá nhân hoặc thương mại.
