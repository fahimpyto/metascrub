import struct
import zlib
from pathlib import Path

from metascrub.scanner import scan_folder, analyze_file, scan_and_analyze
from metascrub.detectors import PNG_SIGNATURE


def build_minimal_png_bytes() -> bytes:
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    idat_data = zlib.compress(b"\x00\x00\x00")
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF)
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)

    data = bytearray(PNG_SIGNATURE)
    for ct, cd, crc in [(b"IHDR", ihdr_data, ihdr_crc),
                          (b"IDAT", idat_data, idat_crc),
                          (b"IEND", b"", iend_crc)]:
        data.extend(struct.pack(">I", len(cd)))
        data.extend(ct)
        data.extend(cd)
        data.extend(crc)
    return bytes(data)


class TestScanFolder:
    def test_empty_dir(self, tmp_path):
        images = scan_folder(tmp_path)
        assert images == []

    def test_non_recursive_finds_images(self, tmp_path):
        (tmp_path / "image.png").write_bytes(build_minimal_png_bytes())
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00\x43\x00\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x03\x01\x22\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x00\x00\xff\xd9")
        images = scan_folder(tmp_path)
        assert len(images) == 2
        extensions = {f.suffix.lower() for f in images}
        assert extensions == {".png", ".jpg"}

    def test_recursive_finds_in_subdirs(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "image.png").write_bytes(build_minimal_png_bytes())
        images = scan_folder(tmp_path, recursive=True)
        assert len(images) == 1

    def test_no_images(self, tmp_path):
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "config.json").write_text("{}")
        images = scan_folder(tmp_path)
        assert images == []


class TestAnalyzeFile:
    def test_clean_png(self, tmp_path):
        f = tmp_path / "clean.png"
        f.write_bytes(build_minimal_png_bytes())
        result = analyze_file(Path(f))
        assert result["is_ai"] is False
        assert result["format"] == "png"
        assert result["error"] is None

    def test_unsupported_format(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("hello")
        result = analyze_file(Path(f))
        assert result["format"] is None
        assert result.get("error") is not None

    def test_ai_png_text_chunk(self, tmp_path):
        from metascrub.png_cleaner import make_chunk, rebuild_png, read_chunks
        data = build_minimal_png_bytes()
        chunks = read_chunks(data)
        chunks.insert(1, make_chunk(b"tEXt", b"parameters\x00steps=20"))
        data = rebuild_png(chunks)
        f = tmp_path / "ai.png"
        f.write_bytes(data)
        result = analyze_file(Path(f))
        assert result["is_ai"] is True


class TestScanAndAnalyze:
    def test_empty_dir(self, tmp_path):
        results = scan_and_analyze(tmp_path)
        assert results == []

    def test_with_images(self, tmp_path):
        (tmp_path / "clean.png").write_bytes(build_minimal_png_bytes())
        results = scan_and_analyze(tmp_path)
        assert len(results) == 1
        assert results[0]["is_ai"] is False
