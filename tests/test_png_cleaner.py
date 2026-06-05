import struct
import zlib

import pytest

from metascrub.png_cleaner import (
    read_chunks,
    rebuild_png,
    make_chunk,
    is_ai_text_chunk,
    is_ai_chunk,
    clean_png,
)
from metascrub.detectors import PNG_SIGNATURE, AI_CHUNK_TYPES


def build_minimal_png_chunks():
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = make_chunk(b"IHDR", ihdr_data)
    idat_data = zlib.compress(b"\x00\x00\x00")
    idat = make_chunk(b"IDAT", idat_data)
    iend = make_chunk(b"IEND", b"")
    return [ihdr, idat, iend]


class TestReadChunks:
    def test_minimal_png(self):
        chunks = build_minimal_png_chunks()
        data = rebuild_png(chunks)
        parsed = read_chunks(data)
        assert len(parsed) == 3
        types = [ct for ct, _, _ in parsed]
        assert types == [b"IHDR", b"IDAT", b"IEND"]

    def test_with_text_chunk(self):
        chunks = build_minimal_png_chunks()
        txt = make_chunk(b"tEXt", b"key\x00value")
        chunks.insert(1, txt)
        data = rebuild_png(chunks)
        parsed = read_chunks(data)
        assert len(parsed) == 4


class TestRebuildPng:
    def test_roundtrip(self):
        chunks = build_minimal_png_chunks()
        data = rebuild_png(chunks)
        assert data.startswith(PNG_SIGNATURE)
        parsed = read_chunks(data)
        assert len(parsed) == len(chunks)

    def test_preserves_content(self):
        original_text = b"Software\x00TestApp"
        chunks = build_minimal_png_chunks()
        chunks.insert(1, make_chunk(b"tEXt", original_text))
        data = rebuild_png(chunks)
        parsed = read_chunks(data)
        text_chunks = [(ct, cd) for ct, cd, _ in parsed if ct == b"tEXt"]
        assert len(text_chunks) == 1
        assert text_chunks[0][1] == original_text


class TestIsAiTextChunk:
    def test_parameters_keyword(self):
        assert is_ai_text_chunk(b"tEXt", b"parameters\x00some data")

    def test_prompt_keyword(self):
        assert is_ai_text_chunk(b"tEXt", b"prompt\x00a beautiful image")

    def test_mj_prompt_keyword(self):
        assert is_ai_text_chunk(b"tEXt", b"mj_prompt\x00/a cat")

    def test_non_ai_keyword(self):
        assert not is_ai_text_chunk(b"tEXt", b"Software\x00TestApp")

    def test_empty_data(self):
        assert not is_ai_text_chunk(b"tEXt", b"")

    def test_invalid_chunk_type(self):
        assert not is_ai_text_chunk(b"IDAT", b"parameters\x00data")


class TestIsAiChunk:
    def test_c2pa_chunks(self):
        assert is_ai_chunk(b"caBX")
        assert is_ai_chunk(b"caMs")
        assert is_ai_chunk(b"caSt")

    def test_non_c2pa_chunk(self):
        assert not is_ai_chunk(b"IHDR")
        assert not is_ai_chunk(b"IDAT")


class TestCleanPng:
    def test_clean_minimal_png(self):
        chunks = build_minimal_png_chunks()
        data = rebuild_png(chunks)
        cleaned = clean_png(data)
        assert cleaned.startswith(PNG_SIGNATURE)

    def test_clean_removes_ai_text_chunk(self):
        chunks = build_minimal_png_chunks()
        chunks.insert(1, make_chunk(b"tEXt", b"parameters\x00steps=20"))
        data = rebuild_png(chunks)
        cleaned = clean_png(data)
        parsed = read_chunks(cleaned)
        types = [ct for ct, _, _ in parsed]
        assert b"tEXt" not in types

    def test_clean_removes_c2pa_chunk(self):
        chunks = build_minimal_png_chunks()
        chunks.insert(1, make_chunk(b"caBX", b"\x00" * 20))
        data = rebuild_png(chunks)
        cleaned = clean_png(data)
        parsed = read_chunks(cleaned)
        types = [ct for ct, _, _ in parsed]
        assert b"caBX" not in types

    def test_clean_preserves_non_ai_text(self):
        chunks = build_minimal_png_chunks()
        chunks.insert(1, make_chunk(b"tEXt", b"Software\x00TestApp"))
        data = rebuild_png(chunks)
        cleaned = clean_png(data)
        parsed = read_chunks(cleaned)
        text_chunks = [(ct, cd) for ct, cd, _ in parsed if ct == b"tEXt"]
        assert len(text_chunks) == 1
        assert b"Software" in text_chunks[0][1]

    def test_clean_injects_exif(self):
        chunks = build_minimal_png_chunks()
        data = rebuild_png(chunks)
        cleaned = clean_png(data, organic=True)
        parsed = read_chunks(cleaned)
        types = [ct for ct, _, _ in parsed]
        assert b"eXIf" in types

    def test_clean_with_invalid_png_raises(self):
        with pytest.raises(ValueError, match="Not a valid PNG"):
            clean_png(b"not a png")
