import sys, os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dubbing.transcribe import SubtitleSegment, Transcriber
from dubbing.translator import SubtitleTranslator

translator = SubtitleTranslator()

# Dữ liệu mẫu câu thoại tiếng Trung / Anh
sample_segments = [
    SubtitleSegment(index=1, start=0.5, end=3.2, text="Hello everybody, welcome back to my channel!"),
    SubtitleSegment(index=2, start=3.8, end=7.0, text="Today we are exploring the most beautiful hidden places in the world."),
    SubtitleSegment(index=3, start=7.5, end=10.2, text="Don't forget to like and subscribe for more amazing videos.")
]

print("Đang dịch thoại sang tiếng Việt chuyên ngữ cảnh video...")
translated = translator.translate_segments(sample_segments, target_lang="vi")

for s in translated:
    print(f"[{s.start:.1f}s -> {s.end:.1f}s] {s.text}")
    print(f"  ==> {s.translated_text}\n")
