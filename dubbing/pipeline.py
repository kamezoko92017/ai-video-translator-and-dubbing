"""
End-to-End Automated AI Video Translation & Dubbing Pipeline
"""
import os
import shutil
import tempfile
from typing import Optional, Dict, Any
from .transcribe import Transcriber
from .translator import SubtitleTranslator
from .voice_synthesizer import VoiceSynthesizer
from .audio_mixer import AudioMixer

class VideoDubbingPipeline:
    def __init__(
        self,
        whisper_model: str = "base",
        voice: str = "Adam",
        translator_api_key: Optional[str] = None,
        device: str = "auto"
    ):
        self.transcriber = Transcriber(model_size=whisper_model, device=device)
        self.translator = SubtitleTranslator(api_key=translator_api_key)
        self.synthesizer = VoiceSynthesizer(voice=voice)
        self.mixer = AudioMixer()

    def process(
        self,
        video_path: str,
        output_path: str,
        target_lang: str = "vi",
        burn_subtitles: bool = True,
        original_bgm_volume: float = 0.20
    ) -> Dict[str, Any]:
        """
        Executes full pipeline:
        1. Extract Audio
        2. Transcribe with timestamps
        3. Translate to Vietnamese
        4. Synthesize voice per segment with time-stretch
        5. Mix audio with ducking
        6. Render final dubbed video
        """
        temp_dir = tempfile.mkdtemp(prefix="dubbing_")
        try:
            print("[1/5] Extracting audio track...")
            wav_path = self.transcriber.extract_audio(video_path, os.path.join(temp_dir, "audio16k.wav"))

            print("[2/5] Transcribing speech with Whisper...")
            segments, source_lang = self.transcriber.transcribe(wav_path)
            print(f"      Detected source language: {source_lang.upper()} ({len(segments)} segments)")

            orig_srt = os.path.join(temp_dir, "original.srt")
            self.transcriber.export_srt(segments, orig_srt, use_translated=False)

            print(f"[3/5] Translating to {target_lang.upper()} (Contextual Dubbing Translation)...")
            segments = self.translator.translate_segments(segments, target_lang=target_lang)

            vi_srt = os.path.join(temp_dir, "translated_vi.srt")
            self.transcriber.export_srt(segments, vi_srt, use_translated=True)

            print(f"[4/5] Synthesizing voice with ElevenLabs ({self.synthesizer.voice})...")
            clips_dir = os.path.join(temp_dir, "voice_clips")
            os.makedirs(clips_dir, exist_ok=True)
            segment_clips = {}

            for s in segments:
                clip_path = self.synthesizer.synthesize_segment(s, clips_dir)
                if clip_path:
                    segment_clips[s.index] = clip_path

            # Get video total duration using ffprobe
            import subprocess
            cmd_dur = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            res_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
            total_duration = float(res_dur.stdout.strip()) if res_dur.returncode == 0 else 60.0

            print("[5/5] Mixing audio with background music ducking & rendering final video...")
            assembled_voice_wav = self.mixer.build_voice_timeline(
                segments, segment_clips, total_duration, os.path.join(temp_dir, "dubbed_timeline.wav")
            )

            final_video = self.mixer.mix_dubbed_video(
                original_video=video_path,
                dubbed_voice_wav=assembled_voice_wav,
                output_video=output_path,
                original_volume=original_bgm_volume,
                burn_subtitles_srt=vi_srt if burn_subtitles else None
            )

            print(f"[SUCCESS] Final dubbed video created: {final_video}")
            return {
                "output_video": final_video,
                "source_language": source_lang,
                "segments_count": len(segments),
                "original_srt": orig_srt,
                "translated_srt": vi_srt
            }
        finally:
            # Leave temp_dir or clean up
            pass
