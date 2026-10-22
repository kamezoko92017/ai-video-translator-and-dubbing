import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dubbing.pipeline import VideoDubbingPipeline

# Khởi tạo pipeline trọn gói:
# - whisper_model: 'base', 'small', 'medium', hoặc 'large-v3'
# - voice: 'Adam' (nam trầm ElevenLabs), 'Maggie' (nữ ElevenLabs), hoặc 'Thanh Niên Tự Tin'
pipeline = VideoDubbingPipeline(
    whisper_model="base",
    voice="Adam",
    device="auto"
)

input_video = "downloads/sample.mp4"
output_video = "output/sample_dubbed_vietnamese.mp4"

if not os.path.exists(input_video):
    print("Vui lòng tải video về downloads/sample.mp4 để chạy thử quy trình đầy đủ.")
    sys.exit(0)

print(f"Bắt đầu quy trình tự động Việt hóa và lồng tiếng: {input_video}")
result = pipeline.process(
    video_path=input_video,
    output_path=output_video,
    target_lang="vi",
    burn_subtitles=True,        # Tự động khắc phụ đề Vietsub vào video
    original_bgm_volume=0.18     # Giữ nhạc nền gốc ở mức 18% để nghe rõ giọng lồng tiếng
)

print("\n[HOÀN TẤT TOÀN BỘ QUY TRÌNH]")
print(f"Video đã lồng tiếng xuất sắc: {result['output_video']}")
print(f"File phụ đề tiếng Việt: {result['translated_srt']}")
