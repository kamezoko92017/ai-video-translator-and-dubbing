"""
Speech-to-Text & Subtitle Extraction using Whisper / Faster-Whisper
"""
import os
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

@dataclass
class SubtitleSegment:
    index: int
    start: float      # start time in seconds
    end: float        # end time in seconds
    text: str         # original text
    translated_text: str = ""  # translated text

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

def format_timestamp_srt(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

class Transcriber:
    """
    Transcribes audio/video files to timed subtitle segments using Faster-Whisper or OpenAI Whisper.
    """
    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "default"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return self.model
        try:
            from faster_whisper import WhisperModel
            import torch
            dev = self.device
            if dev == "auto":
                dev = "cuda" if torch.cuda.is_available() else "cpu"
            c_type = self.compute_type
            if c_type == "default":
                c_type = "float16" if dev == "cuda" else "int8"
            print(f"Loading Faster-Whisper [{self.model_size}] on {dev.upper()} ({c_type})...")
            self.model = ("faster_whisper", WhisperModel(self.model_size, device=dev, compute_type=c_type))
            return self.model
        except ImportError:
            pass

        try:
            import whisper
            import torch
            dev = self.device
            if dev == "auto":
                dev = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading standard OpenAI-Whisper [{self.model_size}] on {dev.upper()}...")
            self.model = ("whisper", whisper.load_model(self.model_size, device=dev))
            return self.model
        except ImportError:
            raise RuntimeError(
                "Neither faster-whisper nor openai-whisper is installed.\n"
                "Please run: pip install faster-whisper\n"
                "Or: pip install openai-whisper"
            )

    def extract_audio(self, video_path: str, output_wav: Optional[str] = None) -> str:
        """Extracts clean 16kHz mono WAV for Whisper."""
        if not output_wav:
            base, _ = os.path.splitext(video_path)
            output_wav = f"{base}_audio16k.wav"
        
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000",
            output_wav
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
        return output_wav

    def transcribe(self, media_path: str, language: Optional[str] = None) -> (List[SubtitleSegment], str):
        """
        Transcribes video or audio file.
        :return: (List of SubtitleSegment, detected_language)
        """
        backend, model = self._load_model()
        segments_out: List[SubtitleSegment] = []
        detected_lang = language or "en"

        if backend == "faster_whisper":
            segments, info = model.transcribe(media_path, language=language, beam_size=5, vad_filter=True)
            detected_lang = info.language
            for idx, s in enumerate(segments, start=1):
                segments_out.append(SubtitleSegment(
                    index=idx,
                    start=round(s.start, 3),
                    end=round(s.end, 3),
                    text=s.text.strip()
                ))
        else: # standard whisper
            res = model.transcribe(media_path, language=language, verbose=False)
            detected_lang = res.get("language", "en")
            for idx, s in enumerate(res.get("segments", []), start=1):
                segments_out.append(SubtitleSegment(
                    index=idx,
                    start=round(s["start"], 3),
                    end=round(s["end"], 3),
                    text=s["text"].strip()
                ))

        return segments_out, detected_lang

    @staticmethod
    def export_srt(segments: List[SubtitleSegment], output_path: str, use_translated: bool = False):
        with open(output_path, "w", encoding="utf-8") as f:
            for s in segments:
                text = (s.translated_text if use_translated and s.translated_text else s.text)
                f.write(f"{s.index}\n")
                f.write(f"{format_timestamp_srt(s.start)} --> {format_timestamp_srt(s.end)}\n")
                f.write(f"{text}\n\n")
