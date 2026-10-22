"""
Voice Dubbing Synthesizer with Audio Time-Stretching (Atempo)
Integrates CapCut ElevenLabs TTS to produce natural speech synchronized to video.
"""
import os
import subprocess
import tempfile
from typing import List, Dict, Optional
from .transcribe import SubtitleSegment

class VoiceSynthesizer:
    def __init__(self, voice: str = "Adam"):
        self.voice = voice
        self._client = None

    def _get_client(self):
        if self._client is None:
            # Import our CapCutTTSClient
            from .capcut_client import CapCutTTSClient
            self._client = CapCutTTSClient()
        return self._client

    def adjust_audio_speed(self, input_wav: str, output_wav: str, speed_factor: float):
        """
        Adjusts audio playback speed without pitch distortion using FFmpeg atempo filter.
        Speed factor ranges: 0.5 to 2.0.
        """
        speed = max(0.6, min(2.0, speed_factor))
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_wav,
            "-filter:a", f"atempo={speed:.3f}",
            output_wav
        ]
        subprocess.run(cmd, check=True)

    def synthesize_segment(self, segment: SubtitleSegment, out_dir: str) -> Optional[str]:
        text = segment.translated_text or segment.text
        if not text.strip():
            return None

        client = self._get_client()
        raw_res = client.synthesize(text, voice=self.voice)
        
        target_duration = segment.duration
        actual_duration = raw_res.duration_ms / 1000.0

        raw_path = os.path.join(out_dir, f"seg_{segment.index:04d}_raw.mp3")
        raw_res.save(raw_path)

        final_path = os.path.join(out_dir, f"seg_{segment.index:04d}.wav")

        # If actual audio differs from target segment duration by more than 15%, stretch/compress tempo
        if target_duration > 0.4 and actual_duration > 0.4:
            speed_ratio = actual_duration / target_duration
            if abs(speed_ratio - 1.0) > 0.15:
                # clamp reasonable speed adjustment (0.7x to 1.35x)
                clamped_ratio = max(0.75, min(1.35, speed_ratio))
                self.adjust_audio_speed(raw_path, final_path, clamped_ratio)
                return final_path

        # Otherwise just convert to standard WAV
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", raw_path, final_path]
        subprocess.run(cmd, check=True)
        return final_path
