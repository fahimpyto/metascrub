from pathlib import Path

from metascrub.cleaner import IMAGE_EXTENSIONS, get_format, clean_image, clean_file


class TestGetFormat:
    def test_known_extensions(self):
        assert get_format(Path("image.jpg")) == "jpeg"
        assert get_format(Path("image.JPEG")) == "jpeg"
        assert get_format(Path("image.png")) == "png"
        assert get_format(Path("image.webp")) == "webp"
        assert get_format(Path("image.jpe")) == "jpeg"

    def test_unknown_extension(self):
        assert get_format(Path("image.bmp")) is None
        assert get_format(Path("image.gif")) is None
        assert get_format(Path("image")) is None


class TestImageExtensions:
    def test_all_values_are_valid_formats(self):
        valid = {"jpeg", "png", "webp"}
        assert set(IMAGE_EXTENSIONS.values()) == valid

    def test_case_insensitive_keys(self):
        for ext in IMAGE_EXTENSIONS:
            assert ext == ext.lower()


class TestCleanImage:
    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            clean_image(b"", "bmp")

    def test_invalid_png_raises(self):
        with pytest.raises(ValueError, match="Not a valid PNG"):
            clean_image(b"not a png", "png")

    def test_invalid_jpeg_raises(self):
        with pytest.raises(ValueError, match="Not a valid JPEG"):
            clean_image(b"not a jpeg", "jpeg")

    def test_invalid_webp_raises(self):
        with pytest.raises(ValueError, match="Not a valid WebP"):
            clean_image(b"not a webp", "webp")


import pytest


class TestCleanFile:
    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "test.bmp"
        f.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported file type"):
            clean_file(Path(f))
