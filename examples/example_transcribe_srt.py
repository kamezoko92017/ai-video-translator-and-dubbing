import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dubbing.transcribe import Transcriber

transcriber = Transcriber(model_size="base")

# Bóc tách phụ đề từ file video / audio
media_file = "downloads/sample.mp4"
if not os.path.exists(media_file):
    print("Vui lòng đặt một file video mẫu vào downloads/sample.mp4 trước khi chạy thử.")
    sys.exit(0)

print(f"Đang nhận diện giọng nói từ: {media_file}...")
segments, lang = transcriber.transcribe(media_file)

print(f"Ngôn ngữ phát hiện: {lang.upper()}")
print(f"Số câu nhận diện được: {len(segments)}")

# Xuất ra file phụ đề chuẩn SRT
out_srt = "output/sample_original.srt"
transcriber.export_srt(segments, out_srt)
print(f"Đã lưu phụ đề SRT: {out_srt}")
