import struct
import zlib

import pytest

from metascrub.detectors import (
    detect_ai_image,
    AI_SOFTWARE_SIGNATURES,
    AI_TEXT_CHUNK_KEYS,
    PNG_SIGNATURE,
)


def make_png_text_chunk(keyword: str, value: str) -> tuple:
    data = keyword.encode() + b"\x00" + value.encode()
    crc = struct.pack(">I", zlib.crc32(b"tEXt" + data) & 0xFFFFFFFF)
    return (b"tEXt", data, crc)


def make_png_eXIf_chunk(exif_data: bytes) -> tuple:
    data = b"Exif\x00\x00" + exif_data
    crc = struct.pack(">I", zlib.crc32(b"eXIf" + data) & 0xFFFFFFFF)
    return (b"eXIf", data, crc)


def build_png(chunks: list) -> bytes:
    data = bytearray(PNG_SIGNATURE)
    for ct, cd, crc in chunks:
        data.extend(struct.pack(">I", len(cd)))
        data.extend(ct)
        data.extend(cd)
        data.extend(crc)
    return bytes(data)


def build_minimal_png(width: int = 1, height: int = 1) -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    idat_data = zlib.compress(b"\x00" * (width * height * 3))  # RGB
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    return build_png([
        (b"IHDR", ihdr_data, ihdr_crc),
        (b"IDAT", idat_data, idat_crc),
        (b"IEND", b"", iend_crc),
    ])


class TestDetectPngAi:
    def test_no_ai_metadata(self):
        data = build_minimal_png()
        result = detect_ai_image(data, "png")
        assert result["is_ai"] is False

    def test_parameters_text_chunk_detected(self):
        data = build_minimal_png()
        chunks = [
            (b"IHDR", data[8:21], data[21:25]),
            make_png_text_chunk("parameters", "steps=20, seed=42"),
            (b"IDAT", data[33:-12], data[-12:-8]),
            (b"IEND", data[-8:-4], data[-4:]),
        ]
        data = build_png(chunks)
        result = detect_ai_image(data, "png")
        assert result["is_ai"] is True
        assert "Stable Diffusion" in result["tool"]

    def test_mj_prompt_text_chunk_detected(self):
        data = build_minimal_png()
        chunks = [
            (b"IHDR", data[8:21], data[21:25]),
            make_png_text_chunk("mj_prompt", "a beautiful landscape --ar 16:9"),
            (b"IDAT", data[33:-12], data[-12:-8]),
            (b"IEND", data[-8:-4], data[-4:]),
        ]
        data = build_png(chunks)
        result = detect_ai_image(data, "png")
        assert result["is_ai"] is True
        assert "Midjourney" in result["tool"]

    def test_workflow_text_chunk_detected(self):
        data = build_minimal_png()
        chunks = [
            (b"IHDR", data[8:21], data[21:25]),
            make_png_text_chunk("workflow", "{}"),
            (b"IDAT", data[33:-12], data[-12:-8]),
            (b"IEND", data[-8:-4], data[-4:]),
        ]
        data = build_png(chunks)
        result = detect_ai_image(data, "png")
        assert result["is_ai"] is True
        assert "ComfyUI" in result["tool"]

    def test_unknown_ai_text_chunk(self):
        data = build_minimal_png()
        chunks = [
            (b"IHDR", data[8:21], data[21:25]),
            make_png_text_chunk("model_hash", "abc123"),
            (b"IDAT", data[33:-12], data[-12:-8]),
            (b"IEND", data[-8:-4], data[-4:]),
        ]
        data = build_png(chunks)
        result = detect_ai_image(data, "png")
        assert result["is_ai"] is True


class TestDetectJpegAi:
    def test_no_ai_metadata(self):
        sofi = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x03\x01\x22\x00"
        sos_header = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
        data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + sofi + sos_header + b"\x00" * 10 + b"\xff\xd9"
        result = detect_ai_image(data, "jpeg")
        assert result["is_ai"] is False


class TestDetectWebpAi:
    def test_no_ai_metadata(self):
        from metascrub.webp_cleaner import clean_webp
        data = b"RIFF\x00\x00\x00\x00WEBPVP8 \x00\x00\x00\x00"
        result = detect_ai_image(data, "webp")
        assert result["is_ai"] is False

    def test_unknown_format(self):
        result = detect_ai_image(b"not an image", "unknown")
        assert result["is_ai"] is False


class TestSignatures:
    def test_known_tools_in_list(self):
        known = {"openai", "midjourney", "stable diffusion", "comfyui", "adobe firefly"}
        found = set()
        for sig in AI_SOFTWARE_SIGNATURES:
            for tool in known:
                if tool in sig.lower():
                    found.add(tool)
        missing = known - found
        assert not missing, f"Missing signatures for: {missing}"

    def test_text_chunk_keys(self):
        assert "parameters" in AI_TEXT_CHUNK_KEYS
        assert "prompt" in AI_TEXT_CHUNK_KEYS
        assert "mj_prompt" in AI_TEXT_CHUNK_KEYS
        assert "workflow" in AI_TEXT_CHUNK_KEYS
        assert "model_hash" in AI_TEXT_CHUNK_KEYS
