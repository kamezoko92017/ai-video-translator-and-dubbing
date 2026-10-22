"""
Audio Mixing, Ducking & Final Video Re-muxing Module
Mixes dubbed voice over original background music with automatic volume ducking.
"""
import os
import subprocess
from typing import List, Optional
from .transcribe import SubtitleSegment

class AudioMixer:
    def __init__(self, ducking_attenuation_db: float = -14.0):
        self.ducking_db = ducking_attenuation_db

    def build_voice_timeline(self, segments: List[SubtitleSegment], segment_audios: dict, total_duration: float, output_wav: str) -> str:
        """
        Assembles individual dubbed voice clips onto a continuous timeline matching video timestamps.
        """
        # Create silent base track of exact total_duration
        cmd_silence = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_duration:.2f}",
            output_wav
        ]
        subprocess.run(cmd_silence, check=True)

        if not segment_audios:
            return output_wav

        # Use amix or adelay filter to place each audio at segment.start
        inputs = ["-i", output_wav]
        filter_parts = []
        for i, s in enumerate(segments, start=1):
            clip = segment_audios.get(s.index)
            if not clip or not os.path.exists(clip):
                continue
            inputs.extend(["-i", clip])
            delay_ms = int(s.start * 1000)
            filter_parts.append(f"[{len(inputs)//2 - 1}:a]adelay={delay_ms}|{delay_ms}[a{i}];")

        if not filter_parts:
            return output_wav

        joined_inputs = "".join(f"[a{i}]" for i, s in enumerate(segments, start=1) if s.index in segment_audios)
        num_mix = len([s for s in segments if s.index in segment_audios]) + 1
        filter_complex = f"{''.join(filter_parts)}[0:a]{joined_inputs}amix=inputs={num_mix}:duration=first:dropout_transition=2[outa]"

        out_timeline = output_wav.replace(".wav", "_assembled.wav")
        cmd_mix = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            out_timeline
        ]
        subprocess.run(cmd_mix, check=True)
        return out_timeline

    def mix_dubbed_video(
        self,
        original_video: str,
        dubbed_voice_wav: str,
        output_video: str,
        original_volume: float = 0.20,
        dubbed_volume: float = 1.15,
        burn_subtitles_srt: Optional[str] = None
    ) -> str:
        """
        Combines original video + original audio (ducked to background) + new dubbed voice.
        Optionally burns subtitles into video.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_video)), exist_ok=True)

        # Filter: reduce original audio volume to BGM level, boost dubbed voice, and mix
        filter_complex = f"[0:a]volume={original_volume:.2f}[bgm];[1:a]volume={dubbed_volume:.2f}[voice];[bgm][voice]amix=inputs=2:duration=first[aout]"
        
        video_filters = []
        if burn_subtitles_srt and os.path.exists(burn_subtitles_srt):
            # Escape path for FFmpeg subtitles filter
            srt_esc = burn_subtitles_srt.replace("\\", "/").replace(":", "\\:")
            video_filters.append(f"subtitles='{srt_esc}':force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3'")

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", original_video,
            "-i", dubbed_voice_wav,
            "-filter_complex", filter_complex,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
        ]

        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])

        cmd.append(output_video)
        subprocess.run(cmd, check=True)
        return output_video
