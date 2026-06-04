from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from metascrub import cleaner
from metascrub.detectors import detect_ai_image


def scan_folder(path: Path, recursive: bool = False):
    images = []
    if recursive:
        files = list(path.rglob('*'))
    else:
        files = list(path.glob('*'))

    for f in files:
        if f.is_file() and cleaner.get_format(f):
            images.append(f)

    return images


def analyze_file(path: Path) -> dict:
    fmt = cleaner.get_format(path)
    if not fmt:
        return {"path": str(path), "format": None, "error": "Unsupported format"}

    try:
        data = path.read_bytes()
        ai_info = detect_ai_image(data, fmt)
        return {
            "path": str(path),
            "format": fmt,
            "size": path.stat().st_size,
            "is_ai": ai_info["is_ai"],
            "ai_tool": ai_info["tool"],
            "error": None,
        }
    except Exception as e:
        return {
            "path": str(path),
            "format": fmt,
            "size": path.stat().st_size,
            "is_ai": False,
            "ai_tool": None,
            "error": str(e),
        }


def scan_and_analyze(path: Path, recursive: bool = False, max_workers: int = 8) -> list[dict]:
    files = scan_folder(path, recursive)
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        fut_map = {pool.submit(analyze_file, f): f for f in files}
        for fut in as_completed(fut_map):
            results.append(fut.result())

    results.sort(key=lambda x: x["path"])
    return results
