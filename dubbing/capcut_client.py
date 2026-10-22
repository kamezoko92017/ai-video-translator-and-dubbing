"""
CapCut ElevenLabs & Native TTS Client (Pure Python - Zero external dependencies required)
Allows synthesizing high-quality ElevenLabs voices (Adam, Maggie, etc.) and CapCut native voices
for free without API keys or accounts.
"""

from dataclasses import dataclass
import base64
import gzip
import hashlib
import json
import os
import re
import secrets
import time
import urllib.parse
import urllib.request
import uuid
from typing import Dict, List, Optional, Union

TTS_SIGN_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmTd34Lw4b7IuldSXh/zY
CMla+ITdGG5TeWz6ad+OySd4r+IrY45AoqrYUxhQ2dl+7z+i7r/5vEa8rr39BYfB
8AGMQLmZA8HmgpWBsqrn/V6daUALkKnkLb70Fn32CJigIuGXAYqxUdGuI340aC+0
v5Es3puJsHyzf01/AelE4Cdc6bZhQrASJLBh8R3BQToYClmDVSDUQk28o8sl/guA
Z4n303Vj+6Siv1HayPCdV6kpVVnMBAG4+umUbwGmn132N3fgpzLarFF3XyWmS1zh
D/J07iM/rP8GDO9IskHNHd2phrO0G6KzrcFAnTBHjVv+hCBEfzN/no3FNA9AuC36
mwIDAQAB
-----END PUBLIC KEY-----"""

BASE_URL = "https://editor-api-sg.capcutapi.com"


def _der_len(data: bytes, pos: int):
    first = data[pos]
    pos += 1
    if first < 0x80:
        return first, pos
    nbytes = first & 0x7F
    return int.from_bytes(data[pos : pos + nbytes], "big"), pos + nbytes


def _der_value(data: bytes, pos: int, tag: int):
    length, pos = _der_len(data, pos + 1)
    return data[pos : pos + length], pos + length


def _der_int(data: bytes, pos: int):
    raw, pos = _der_value(data, pos, 0x02)
    return int.from_bytes(raw.lstrip(b"\x00"), "big"), pos


def _rsa_public_numbers_from_pem(pem: str):
    b64 = "".join(line for line in pem.splitlines() if not line.startswith("-----"))
    der = base64.b64decode(b64)
    outer, pos = _der_value(der, 0, 0x30)
    _, pos = _der_value(outer, 0, 0x30)
    bit_string, pos = _der_value(outer, pos, 0x03)
    rsa_seq, pos = _der_value(bit_string[1:], 0, 0x30)
    modulus, pos = _der_int(rsa_seq, 0)
    exponent, pos = _der_int(rsa_seq, pos)
    return modulus, exponent


def rsa_encrypt_pkcs1v15(message: Union[str, bytes], pem: str = TTS_SIGN_PUBLIC_KEY_PEM) -> str:
    """Pure Python RSA PKCS#1 v1.5 encryption (no external cryptography packages required)."""
    modulus, exponent = _rsa_public_numbers_from_pem(pem)
    key_len = (modulus.bit_length() + 7) // 8
    msg = message.encode("utf-8") if isinstance(message, str) else bytes(message)
    if len(msg) > key_len - 11:
        raise ValueError("message too long for RSA PKCS#1 v1.5")
    ps_len = key_len - len(msg) - 3
    ps = bytearray()
    while len(ps) < ps_len:
        chunk = secrets.token_bytes(ps_len - len(ps))
        ps.extend(b for b in chunk if b != 0)
    encoded = b"\x00\x02" + bytes(ps[:ps_len]) + b"\x00" + msg
    encrypted = pow(int.from_bytes(encoded, "big"), exponent, modulus).to_bytes(key_len, "big")
    return base64.b64encode(encrypted).decode("ascii")


def escape_xml(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generate_device_info() -> Dict[str, str]:
    """Generate realistic device identity with dynamic suffix to prevent rate limiting."""
    suffix = f"{secrets.randbelow(10000):04d}"
    return {
        "aid": "359289",
        "app_name": "CapCut",
        "appvr": "8.9.1",
        "version_name": "8.9.1",
        "version_code": "8.9.1",
        "channel": "capcutpc_google",
        "device_platform": "pc",
        "device_type": "windows",
        "device_brand": "windows",
        "os_version": "26200.8875",
        "device_id": f"766267532498431{suffix}",
        "iid": "7647185302080423697",
        "region": "VN",
        "loc": "VN",
        "lan": "vi-VN",
        "pf": "3",
        "tdid": f"766267532498431{suffix}",
    }


def make_sign_header(url: str, appvr: str, device_time: str, tdid: str) -> str:
    path = url.split("?")[0]
    sign_str = f"9e2c|{path[-7:]}|3|{appvr}|{device_time}|{tdid}|11ac"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


def make_trace_id() -> str:
    seed = uuid.uuid4().hex[:32]
    return f"00-{seed}-{seed[:16]}-01"


def read_json_resp(resp) -> dict:
    raw = resp.read()
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


@dataclass
class TTSResult:
    audio_bytes: bytes
    duration_ms: int
    utterances: List[Dict]
    audio_url: str
    voice_id: str
    voice_name: str
    text: str

    def save(self, filepath: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(self.audio_bytes)
        return filepath


class CapCutTTSClient:
    """
    Client for synthesizing voice via CapCut's ElevenLabs and Native TTS gateway.
    """

    def __init__(self, voice_catalog_path: Optional[str] = None):
        if voice_catalog_path is None:
            voice_catalog_path = os.path.join(os.path.dirname(__file__), "voices.json")
        self.catalog: List[Dict] = []
        if os.path.exists(voice_catalog_path):
            with open(voice_catalog_path, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)
        self.device = generate_device_info()

    def rotate_device(self):
        """Rotates device fingerprint if encountering temporary gateway friction."""
        self.device = generate_device_info()

    def list_voices(self, language: Optional[str] = None, only_elevenlabs: bool = False) -> List[Dict]:
        """List available voices with metadata."""
        voices = self.catalog
        if only_elevenlabs:
            voices = [v for v in voices if v.get("is_elevenlabs")]
        if language:
            voices = [v for v in voices if v.get("language") == language]
        return voices

    def find_voice(self, voice_identifier: str) -> Dict:
        """Resolve voice identifier by ID, exact name, or partial friendly name."""
        voice_clean = voice_identifier.lower().strip()
        # 1. Exact ID match
        for v in self.catalog:
            if v["id"].lower() == voice_clean:
                return v
        # 2. Exact name match
        for v in self.catalog:
            if v["name"].lower() == voice_clean:
                return v
        # 3. Partial name match
        for v in self.catalog:
            if voice_clean in v["name"].lower() or voice_clean in v.get("display_name", "").lower():
                return v
        # Default fallback to Adam (ElevenLabs)
        return {
            "id": voice_identifier,
            "name": voice_identifier,
            "display_name": voice_identifier,
            "resource_id": "7369525170723099153",
            "platform": "11labs" if len(voice_identifier) == 20 else "sami",
            "req_key": "11labs_text_to_speech" if len(voice_identifier) == 20 else "sami_text_to_speech",
            "language": "en",
            "is_elevenlabs": len(voice_identifier) == 20,
        }

    def synthesize(
        self,
        text: str,
        voice: str = "Adam",
        speed: float = 1.0,
        timeout: float = 40.0,
    ) -> TTSResult:
        """
        Synthesize speech from text.
        :param text: Text to read (Vietnamese, English, etc.)
        :param voice: Voice name (e.g. "Adam", "Maggie", "Alex", "Thanh Niên Tự Tin") or Voice ID
        :param speed: Speech rate (0.5 to 2.0, default 1.0)
        :param timeout: Maximum seconds to wait for audio generation
        :return: TTSResult object containing audio bytes and word-level timestamps
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        v_info = self.find_voice(voice)
        voice_id = v_info["id"]
        resource_id = v_info.get("resource_id", "7369525170723099153")
        platform = v_info.get("platform", "11labs")
        req_key = v_info.get("req_key", "11labs_text_to_speech")
        rate_str = f"{float(speed):.1f}"

        # Build SSML
        voice_block = (
            f'    <voice name="{voice_id}" mock_tone_info="" platform="{platform}" '
            f'resource_id="{resource_id}" emotion="" emotion_scale="0" style="" role="" '
            f'moyin_emotion="" is_clone_tone="false" need_subtitle_timestamp="false">\n'
            f'        <prosody rate="{rate_str}">{escape_xml(text)}</prosody>\n'
            f'    </voice>'
        )
        ssml = (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n'
            f'{voice_block}\n'
            '</speak>'
        )

        babi = {
            "feature_entrance": "editor",
            "feature_entrance_detail": "editor-feature-text_to_speech",
            "feature_key": "text_to_speech",
            "scenario": "video_editor",
        }
        extra_info = json.dumps({"benefit_info": {}}, separators=(",", ":"))
        ssml_md5 = hashlib.md5(ssml.encode("utf-8")).hexdigest()
        sign_input = f"appid:{self.device['aid']}&did:{self.device['device_id']}&creditDisable:false&ssml:{ssml_md5}&extraInfo:{extra_info}"
        
        payload = {
            "audio_format": "mp3",
            "babi_param": json.dumps(babi, separators=(",", ":")),
            "credit_disable": False,
            "extra_info": extra_info,
            "need_merge_voice": False,
            "need_subtitle_timestamp": False,
            "scene": "text_to_speech",
            "ssml": ssml,
            "sign": rsa_encrypt_pkcs1v15(sign_input),
        }

        bind_id = str(uuid.uuid4())
        task_context = str(uuid.uuid4())
        body = {
            "bind_id": bind_id,
            "can_queue": True,
            "enter_from": "text_to_speech",
            "tasks": [
                {
                    "context": task_context,
                    "payload": json.dumps(payload, separators=(",", ":")),
                    "req_key": req_key,
                    "task_version": "v3",
                }
            ],
        }
        body_text = json.dumps(body, separators=(",", ":"))

        # Build Headers & Query
        now = str(int(time.time()))
        headers = {
            "content-type": "application/json",
            "appvr": self.device["appvr"],
            "ch": self.device["channel"],
            "device-time": now,
            "lan": self.device["lan"],
            "loc": self.device["loc"],
            "pf": self.device["pf"],
            "sign-ver": "1",
            "tdid": self.device["tdid"],
            "x-ss-stub": hashlib.md5(body_text.encode("utf-8")).hexdigest(),
            "x-ss-dp": self.device["aid"],
            "x-khronos": now,
            "x-tt-trace-id": make_trace_id(),
            "user-agent": "Cronet/TTNetVersion:1d7cc3b1 2025-07-16 QuicVersion:52c2b40d 2025-04-03",
            "accept-encoding": "gzip, deflate",
            "store-country-code": self.device["loc"].lower(),
            "store-country-code-src": "did",
            "is-dispatch-us-ttp": "0",
            "is-app-region-us-ttp": "0",
            "app-sdk-version": self.device["appvr"],
            "appid": self.device["aid"],
        }
        query = {
            "app_name": self.device["app_name"],
            "device_type": self.device["device_type"],
            "os_version": self.device["os_version"],
            "channel": self.device["channel"],
            "version_name": self.device["version_name"],
            "device_brand": self.device["device_brand"],
            "device_id": self.device["device_id"],
            "iid": self.device["iid"],
            "version_code": self.device["version_code"],
            "device_platform": self.device["device_platform"],
            "aid": self.device["aid"],
            "region": self.device["region"],
            "babi_param": json.dumps(babi, separators=(",", ":")),
        }

        url_new = f"{BASE_URL}/lv/v1/common_task/new?{urllib.parse.urlencode(query)}"
        headers["sign"] = make_sign_header(url_new, self.device["appvr"], headers["device-time"], self.device["tdid"])

        # 1. Submit task
        req = urllib.request.Request(url_new, data=body_text.encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            submit_resp = read_json_resp(resp)

        tasks = submit_resp.get("data", {}).get("tasks") or []
        if not tasks:
            raise RuntimeError(f"CapCut TTS submission failed: {submit_resp}")

        task_id = tasks[0]["id"]
        token = tasks[0]["token"]

        # 2. Poll for completion
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(1.0)
            q_body = {
                "tasks": [
                    {
                        "bind_id": bind_id,
                        "id": task_id,
                        "req_key": "sami_text_to_speech",
                        "task_version": "v3",
                        "token": token,
                    }
                ]
            }
            q_text = json.dumps(q_body, separators=(",", ":"))
            q_now = str(int(time.time()))
            q_query = {
                "app_name": self.device["app_name"],
                "device_type": self.device["device_type"],
                "os_version": self.device["os_version"],
                "channel": self.device["channel"],
                "version_name": self.device["version_name"],
                "device_brand": self.device["device_brand"],
                "device_id": self.device["device_id"],
                "iid": self.device["iid"],
                "version_code": self.device["version_code"],
                "device_platform": self.device["device_platform"],
                "aid": self.device["aid"],
            }
            q_url = f"{BASE_URL}/lv/v1/common_task/query?{urllib.parse.urlencode(q_query)}"
            q_headers = dict(headers)
            q_headers["device-time"] = q_now
            q_headers["x-khronos"] = q_now
            q_headers["x-ss-stub"] = hashlib.md5(q_text.encode("utf-8")).hexdigest()
            q_headers["sign"] = make_sign_header(q_url, self.device["appvr"], q_now, self.device["tdid"])

            q_req = urllib.request.Request(q_url, data=q_text.encode("utf-8"), headers=q_headers)
            with urllib.request.urlopen(q_req, timeout=15) as q_resp:
                q_data = read_json_resp(q_resp)

            q_tasks = q_data.get("data", {}).get("tasks") or []
            if not q_tasks:
                continue

            q_task = q_tasks[0]
            status = str(q_task.get("status") or "").lower()

            if status in ("succeed", "success", "done", "completed"):
                # Extract payload details
                payload_str = q_task.get("payload", "")
                utterances = []
                duration_ms = 0
                audio_url = ""

                if payload_str:
                    try:
                        p_obj = json.loads(payload_str)
                        subs = p_obj.get("audio_subtitles", [])
                        if subs:
                            audio_url = subs[0].get("speech_url", "")
                            utterances = subs[0].get("utterances", [])
                            duration_ms = subs[0].get("duration", 0)
                    except Exception:
                        pass

                if not audio_url:
                    urls = re.findall(r'https?://[^\s"\'\\]+', str(q_task))
                    audio_urls = [u for u in urls if "tiktokcdn" in u or "mp3" in u]
                    audio_url = audio_urls[0] if audio_urls else (urls[0] if urls else "")

                if not audio_url:
                    raise RuntimeError(f"Could not locate audio URL in response: {q_task}")

                # Download audio
                with urllib.request.urlopen(audio_url, timeout=20) as a_resp:
                    audio_bytes = a_resp.read()

                return TTSResult(
                    audio_bytes=audio_bytes,
                    duration_ms=duration_ms or len(audio_bytes) // 4,
                    utterances=utterances,
                    audio_url=audio_url,
                    voice_id=voice_id,
                    voice_name=v_info.get("name", voice_id),
                    text=text,
                )

            elif status in ("failed", "fail", "error"):
                err_msg = q_task.get("err_msg") or q_task.get("detail_info") or "Task generation failed"
                raise RuntimeError(f"CapCut TTS generation failed: {err_msg}")

        raise TimeoutError(f"CapCut TTS timed out after {timeout} seconds.")

    def synthesize_long_text(
        self,
        text: str,
        voice: str = "Adam",
        speed: float = 1.0,
        max_chunk_chars: int = 250,
    ) -> TTSResult:
        """
        Synthesizes longer paragraphs by chunking text and concatenating MP3 buffers.
        """
        # Split text into logical sentences or chunks
        raw_chunks = re.split(r'(?<=[.!?\n])\s+', text.strip())
        chunks = []
        current = ""
        for c in raw_chunks:
            if not c.strip():
                continue
            if len(current) + len(c) < max_chunk_chars:
                current = f"{current} {c}".strip()
            else:
                if current:
                    chunks.append(current)
                current = c
        if current:
            chunks.append(current)

        if len(chunks) <= 1:
            return self.synthesize(text, voice=voice, speed=speed)

        all_bytes = bytearray()
        all_utterances = []
        total_duration = 0
        v_name = voice

        for idx, chunk in enumerate(chunks):
            res = self.synthesize(chunk, voice=voice, speed=speed)
            all_bytes.extend(res.audio_bytes)
            v_name = res.voice_name
            # Offset utterances timestamps
            for u in res.utterances:
                all_utterances.append({
                    "word": u.get("word"),
                    "start_time": u.get("start_time", 0) + total_duration,
                    "end_time": u.get("end_time", 0) + total_duration,
                })
            total_duration += res.duration_ms

        return TTSResult(
            audio_bytes=bytes(all_bytes),
            duration_ms=total_duration,
            utterances=all_utterances,
            audio_url="",
            voice_id=voice,
            voice_name=v_name,
            text=text,
        )
