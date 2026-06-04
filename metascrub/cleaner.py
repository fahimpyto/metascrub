from pathlib import Path

from metascrub import png_cleaner
from metascrub import jpeg_cleaner
from metascrub import webp_cleaner


IMAGE_EXTENSIONS = {
    '.jpg': 'jpeg', '.jpeg': 'jpeg', '.jpe': 'jpeg',
    '.png': 'png',
    '.webp': 'webp',
}


def get_format(path: Path) -> str | None:
    return IMAGE_EXTENSIONS.get(path.suffix.lower())


def clean_image(data: bytes, fmt: str, organic: bool = False) -> bytes:
    if fmt == 'png':
        return png_cleaner.clean_png(data, organic=organic)
    elif fmt == 'jpeg':
        return jpeg_cleaner.clean_jpeg(data, organic=organic)
    elif fmt == 'webp':
        return webp_cleaner.clean_webp(data, organic=organic)
    raise ValueError(f"Unsupported format: {fmt}")


def clean_file(path: Path, organic: bool = False, in_place: bool = True, output_dir: Path | None = None) -> Path:
    fmt = get_format(path)
    if not fmt:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    data = path.read_bytes()
    cleaned = clean_image(data, fmt, organic=organic)

    if in_place:
        path.write_bytes(cleaned)
        return path
    else:
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path = output_dir / path.name
        else:
            stem = path.stem
            out_path = path.with_name(f"{stem}_cleaned{path.suffix}")
        out_path.write_bytes(cleaned)
        return out_path
