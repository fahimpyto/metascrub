from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / (1024*1024):.1f}MB"


def print_scan_results(console: Console, results: list[dict]):
    ai_count = sum(1 for r in results if r.get("is_ai"))
    clean_count = sum(1 for r in results if not r.get("is_ai") and not r.get("error"))
    error_count = sum(1 for r in results if r.get("error"))

    if not results:
        console.print("[yellow]No image files found.[/yellow]")
        return

    table = Table(box=box.ROUNDED, title=f"Scan Results - {len(results)} images")

    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Size", style="white")
    table.add_column("AI?", style="bold")
    table.add_column("Tool", style="yellow")

    for r in results:
        if r.get("error"):
            table.add_row(
                Path(r["path"]).name,
                r.get("format", "?"),
                _fmt_size(r.get("size", 0)),
                "[red]ERROR[/red]",
                r["error"],
            )
        elif r["is_ai"]:
            label = "[red]YES[/red]"
            tool = r.get("ai_tool") or "Unknown"
            table.add_row(
                Path(r["path"]).name,
                r["format"],
                _fmt_size(r["size"]),
                label,
                tool,
            )
        else:
            table.add_row(
                Path(r["path"]).name,
                r["format"],
                _fmt_size(r["size"]),
                "[green]No[/green]",
                "-",
            )

    console.print(table)

    summary = f"[bold]{len(results)}[/bold] images scanned  *  [red]{ai_count} AI[/red]  *  [green]{clean_count} clean[/green]"
    if error_count:
        summary += f"  *  [red]{error_count} errors[/red]"
    console.print(summary)


def print_clean_results(console: Console, processed: list[dict]):
    success = [p for p in processed if p.get("success")]
    errors = [p for p in processed if not p.get("success")]

    table = Table(box=box.ROUNDED, title="Cleaning Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("AI Tool", style="yellow")
    table.add_column("Output", style="green")

    for p in success:
        table.add_row(
            Path(p["path"]).name,
            "[green]OK Cleaned[/green]",
            p.get("ai_tool") or "--",
            p.get("output", "in-place"),
        )

    for p in errors:
        table.add_row(
            Path(p["path"]).name,
            "[red]FAILED[/red]",
            p.get("error", "Unknown"),
            "--",
        )

    console.print(table)
    console.print(
        f"[bold]{len(success)}[/bold] cleaned  *  [red]{len(errors)} failed[/red]"
    )


def print_dump(console: Console, data: dict):
    from rich.panel import Panel
    from rich.text import Text

    # ── File Info ──
    fi = data["file"]
    lines = [
        f"Path:     {fi['path']}",
        f"Size:     {_fmt_size(fi['size'])}",
        f"Created:  {fi['created']}",
        f"Modified: {fi['modified']}",
        f"SHA256:   {fi['sha256']}",
    ]
    console.print(Panel("\n".join(lines), title=f"[bold cyan]{fi['name']}[/bold cyan] — {fi['format'].upper()}", border_style="cyan"))

    # ── AI Detection ──
    ai = data.get("ai", {})
    if ai.get("is_ai"):
        console.print(f"[red]!! AI-Generated[/red] — Tool: {ai.get('tool', 'Unknown')}")
    else:
        console.print("[green]No AI metadata detected[/green]")

    # ── Camera ──
    cam = data.get("camera")
    if cam:
        t = Table(box=box.SIMPLE, title="Camera")
        t.add_column("Field", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in cam.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── GPS ──
    gps = data.get("gps")
    if gps:
        t = Table(box=box.SIMPLE, title="GPS Location")
        t.add_column("Field", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in gps.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── Shooting ──
    shooting = data.get("shooting")
    if shooting:
        t = Table(box=box.SIMPLE, title="Shooting Settings")
        t.add_column("Setting", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in shooting.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── Dates ──
    dates = data.get("dates")
    if dates:
        t = Table(box=box.SIMPLE, title="Dates")
        t.add_column("Field", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in dates.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── Copyright ──
    cr = data.get("copyright")
    if cr:
        t = Table(box=box.SIMPLE, title="Copyright / Description")
        t.add_column("Field", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in cr.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── EXIF all tags ──
    exif = data.get("exif")
    if exif:
        for ifd_name, ifd_data in exif.items():
            if ifd_name == "thumbnail":
                console.print(f"[bold]Thumbnail:[/bold] {ifd_data}")
                continue
            t = Table(box=box.SIMPLE, title=f"EXIF — {ifd_data.get('label', ifd_name)}")
            t.add_column("Tag", style="cyan")
            t.add_column("Value", style="yellow")
            for tag, val in ifd_data.get("tags", {}).items():
                t.add_row(tag, str(val))
            console.print(t)

    # ── XMP ──
    xmp = data.get("xmp")
    if xmp:
        console.print(Panel(xmp[:2000], title="XMP Metadata", border_style="green"))

    # ── ICC Profile ──
    icc = data.get("icc_profile")
    if icc:
        console.print(f"[bold]ICC Profile:[/bold] {icc}")

    # ── Text Chunks (PNG) / Comments (JPEG) ──
    text_chunks = data.get("text_chunks")
    if text_chunks:
        t = Table(box=box.SIMPLE, title="PNG Text Chunks")
        t.add_column("Keyword", style="cyan")
        t.add_column("Value", style="yellow")
        for tc in text_chunks:
            t.add_row(tc["keyword"], tc["value"][:300])
        console.print(t)

    comments = data.get("comments")
    if comments:
        t = Table(box=box.SIMPLE, title="JPEG Comments")
        t.add_column("#", style="dim")
        t.add_column("Comment", style="yellow")
        for i, c in enumerate(comments, 1):
            t.add_row(str(i), c[:300])
        console.print(t)

    # ── JFIF ──
    jfif = data.get("jfif")
    if jfif:
        t = Table(box=box.SIMPLE, title="JFIF")
        t.add_column("Field", style="cyan")
        t.add_column("Value", style="yellow")
        for k, v in jfif.items():
            t.add_row(k.replace("_", " ").title(), str(v))
        console.print(t)

    # ── Raw Structure ──
    struct = data.get("structure", [])
    if struct:
        is_png = any("index" in s for s in struct)
        is_jpeg = any("marker" in s for s in struct)
        is_webp = any("chunk_type" in s for s in struct)

        if is_png:
            title = "PNG Chunks"
            cols = [("Index", "dim"), ("Type", "cyan"), ("Length", "white"), ("CRC", "dim"), ("Info", "yellow")]
            rows = []
            for s in struct:
                info_parts = []
                dec = s.get("decoded", {})
                if isinstance(dec, dict):
                    for k, v in dec.items():
                        info_parts.append(f"{k}={v}")
                if s.get("key"):
                    info_parts.insert(0, f"{s['key']}: {s.get('value', '')[:80]}")
                rows.append([str(s["index"]), s["type"], str(s["length"]), s["crc"][:8], "; ".join(info_parts)])
        elif is_jpeg:
            title = "JPEG Markers"
            cols = [("Offset", "dim"), ("Marker", "cyan"), ("Name", "white"), ("Length", "white"), ("Info", "yellow")]
            rows = []
            for s in struct:
                info = s.get("content")
                if isinstance(info, dict):
                    info_str = "; ".join(f"{k}={v}" for k, v in info.items())
                elif info:
                    info_str = str(info)[:120]
                else:
                    info_str = ""
                rows.append([str(s["offset"]), s["marker"], s["name"], str(s["length"]), info_str])
        elif is_webp:
            title = "WebP Chunks"
            cols = [("Offset", "dim"), ("Type", "cyan"), ("Name", "white"), ("Length", "white"), ("Info", "yellow")]
            rows = []
            for s in struct:
                info = s.get("content")
                if isinstance(info, dict):
                    info_str = "; ".join(f"{k}={v}" for k, v in info.items())
                elif info:
                    info_str = str(info)[:120]
                else:
                    info_str = ""
                rows.append([str(s["offset"]), s["chunk_type"], s["name"], str(s["length"]), info_str])

        t = Table(box=box.ROUNDED, title=title)
        for col_name, col_style in cols:
            t.add_column(col_name, style=col_style, no_wrap=True)
        for row in rows:
            t.add_row(*row)
        console.print(t)


def print_image_info(console: Console, path: Path, metadata: dict):
    console.print(f"\n[bold cyan]File:[/bold cyan] {path.name}")
    console.print(f"[bold]Path:[/bold] {path.resolve()}")

    if metadata.get("error"):
        console.print(f"[red]Error: {metadata['error']}[/red]")
        return

    if metadata.get("is_ai"):
        console.print(f"[red]!! AI-Generated[/red] -- Tool: {metadata.get('ai_tool', 'Unknown')}")
    else:
        console.print("[green]No AI metadata detected[/green]")

    if metadata.get("exif"):
        table = Table(box=box.SIMPLE, title="EXIF Metadata")
        table.add_column("Tag", style="cyan")
        table.add_column("Value", style="yellow")
        for tag, value in metadata["exif"].items():
            table.add_row(str(tag), str(value))
        console.print(table)
