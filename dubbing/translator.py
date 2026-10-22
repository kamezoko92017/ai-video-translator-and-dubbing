"""
AI-Powered Contextual Video Subtitle Translator
Translates dialogue accurately to natural Vietnamese matching video timing.
Supports Google Gemini, OpenAI, or free translation fallback.
"""
import os
import json
import urllib.request
from typing import List, Optional, Dict, Any
from .transcribe import SubtitleSegment

SYSTEM_DUBBING_PROMPT = """Bạn là chuyên gia dịch thuật và biên tập kịch bản lồng tiếng video/phim ngắn chuyên nghiệp.
Nhiệm vụ: Dịch các câu thoại dưới đây sang tiếng Việt để lồng tiếng (Voice-Over/Dubbing).

YÊU CẦU QUAN TRỌNG:
1. Văn phong: Tự nhiên, đời thường, gãy gọn, giàu cảm xúc, đúng ngữ cảnh nói của người Việt.
2. Khớp thời lượng (Time-matching): Câu dịch không được quá dài dòng so với thời lượng nói cho phép.
3. Đại từ nhân xưng: Tự động suy luận mối quan hệ phù hợp (tôi - bạn, anh - em, mẹ - con, sếp - em...).
4. Trả về đúng định dạng JSON: danh sách các object {"index": số, "translated_text": "câu dịch"}."""

class SubtitleTranslator:
    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.provider = provider
        if self.provider == "auto":
            if os.environ.get("GEMINI_API_KEY"):
                self.provider = "gemini"
            elif os.environ.get("OPENAI_API_KEY"):
                self.provider = "openai"
            else:
                self.provider = "free"

    def translate_segments(self, segments: List[SubtitleSegment], target_lang: str = "vi") -> List[SubtitleSegment]:
        if not segments:
            return []

        if self.provider == "gemini" and self.api_key:
            return self._translate_gemini(segments, target_lang)
        elif self.provider == "openai" and self.api_key:
            return self._translate_openai(segments, target_lang)
        else:
            return self._translate_free(segments, target_lang)

    def _translate_free(self, segments: List[SubtitleSegment], target_lang: str) -> List[SubtitleSegment]:
        """Free translation using deep-translator or Google Translate API."""
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source="auto", target=target_lang)
            for s in segments:
                try:
                    s.translated_text = translator.translate(s.text)
                except Exception:
                    s.translated_text = s.text
            return segments
        except ImportError:
            # Fallback simple URL fetch
            for s in segments:
                s.translated_text = self._google_trans_fallback(s.text, target_lang)
            return segments

    def _google_trans_fallback(self, text: str, target_lang: str) -> str:
        try:
            q = urllib.parse.quote(text)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={q}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode("utf-8"))
                return "".join([part[0] for part in data[0] if part[0]])
        except Exception:
            return text

    def _translate_gemini(self, segments: List[SubtitleSegment], target_lang: str) -> List[SubtitleSegment]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        data_input = [{"index": s.index, "duration": round(s.duration, 1), "text": s.text} for s in segments]
        prompt = f"{SYSTEM_DUBBING_PROMPT}\n\nDữ liệu thoại cần dịch:\n{json.dumps(data_input, ensure_ascii=False)}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8"))
            raw_text = res["candidates"][0]["content"]["parts"][0]["text"]
            translated_list = json.loads(raw_text)
            trans_map = {item["index"]: item.get("translated_text", "") for item in translated_list}
            for s in segments:
                s.translated_text = trans_map.get(s.index, s.text)
        return segments

    def _translate_openai(self, segments: List[SubtitleSegment], target_lang: str) -> List[SubtitleSegment]:
        data_input = [{"index": s.index, "duration": round(s.duration, 1), "text": s.text} for s in segments]
        prompt = f"{SYSTEM_DUBBING_PROMPT}\n\nDữ liệu thoại:\n{json.dumps(data_input, ensure_ascii=False)}"
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": SYSTEM_DUBBING_PROMPT}, {"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            items = parsed if isinstance(parsed, list) else parsed.get("items", parsed.get("translations", []))
            trans_map = {item["index"]: item.get("translated_text", "") for item in items}
            for s in segments:
                s.translated_text = trans_map.get(s.index, s.text)
        return segments
