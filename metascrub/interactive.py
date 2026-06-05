import re
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from metascrub.scanner import scan_and_analyze, analyze_file
from metascrub.cleaner import clean_file, get_format
from metascrub.injector import make_organic_exif_blob, make_design_exif_blob, make_custom_exif_blob


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / (1024*1024):.1f}MB"


def run_interactive_scan(console: Console, scan_path: Path, recursive: bool = False):
    while True:
        console.print(f"\nScanning [cyan]{scan_path}[/cyan] ...")
        results = scan_and_analyze(scan_path, recursive=recursive)

        if not results:
            console.print("[yellow]No image files found.[/yellow]")
            return

        results.sort(key=lambda r: Path(r["path"]).name.lower())

        table = Table(box=box.ROUNDED, title=f"Scan Results - {len(results)} images")
        table.add_column("#", style="dim", width=4)
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta", width=5)
        table.add_column("Size", style="white")
        table.add_column("AI?", style="bold", width=4)
        table.add_column("Tool", style="yellow")

        for i, r in enumerate(results, 1):
            fname = Path(r["path"]).name
            fmt = r.get("format", "?")
            size = _fmt_size(r.get("size", 0))
            if r.get("error"):
                ai_label = "[red]ERR[/red]"
                tool = r["error"]
            elif r.get("is_ai"):
                ai_label = "[red]YES[/red]"
                tool = r.get("ai_tool") or "Unknown"
            else:
                ai_label = "[green]NO[/green]"
                tool = "-"
            table.add_row(str(i), fname, fmt, size, ai_label, tool)

        console.print(table)

        total = len(results)
        prompt = f"Select image #[bold]1-{total}[/bold] (or 'a' all, 'q' quit): "
        choice = click.prompt(prompt, default="", show_default=False).strip().lower()

        if choice == "q":
            console.print("[yellow]Exited.[/yellow]")
            return

        if choice == "a":
            selected = list(range(total))
        else:
            selected = _parse_selection(choice, total)

        if not selected:
            console.print("[yellow]No valid selection.[/yellow]")
            continue

        # Process each selected image
        for idx in selected:
            r = results[idx]
            file_path = Path(r["path"])
            fmt = r.get("format")
            _process_image(console, file_path, fmt, idx + 1)


def _process_image(console: Console, file_path: Path, fmt: str | None, num: int):
    while True:
        console.print()
        ai_info = analyze_file(file_path)
        ai_status = f"[red]YES - {ai_info.get('ai_tool') or 'Unknown'}[/red]" if ai_info.get("is_ai") else "[green]NO[/green]"
        console.print(Panel(
            f"[bold cyan]#{num}: {file_path.name}[/bold cyan]\n"
            f"AI: {ai_status}  |  Size: {_fmt_size(file_path.stat().st_size)}",
            border_style="blue"
        ))

        table = Table(box=box.SIMPLE, style="bold")
        table.add_column("Option", style="dim", width=6)
        table.add_column("Action", style="cyan")
        table.add_row("[1]", "Info - Show ALL metadata")
        table.add_row("[2]", "Clean - Strip AI metadata → output/ folder")
        table.add_row("[3]", "Data Manipulate - Modify metadata")
        table.add_row("[4]", "← Back to scan results")
        table.add_row("[5]", "Exit")
        console.print(table)

        action = click.prompt("Choose", default="", show_default=False).strip().lower()

        if action in ("1", "info"):
            _show_info(console, file_path, fmt)
        elif action in ("2", "clean"):
            _clean_image(console, file_path, fmt)
        elif action in ("3", "data"):
            _data_manipulate(console, file_path, fmt)
        elif action in ("4", "back"):
            return
        elif action in ("5", "exit"):
            console.print("[yellow]Exited.[/yellow]")
            raise SystemExit(0)
        else:
            console.print("[red]Invalid option.[/red]")


def _show_info(console: Console, file_path: Path, fmt: str | None):
    from metascrub.dumper import dump_image
    from metascrub.formatter import print_dump
    try:
        data = dump_image(file_path)
        print_dump(console, data)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    click.pause("Press any key to continue...")


def _clean_image(console: Console, file_path: Path, fmt: str | None):
    from metascrub.dumper import dump_image
    out_dir = Path("output").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prompt for output name
    default_name = f"{file_path.stem}_cleaned"
    custom_name = click.prompt(
        f"Output filename (without extension)",
        default=default_name, show_default=True
    ).strip()
    if not custom_name:
        custom_name = default_name
    out_name = f"{custom_name}{file_path.suffix}"
    out_path = out_dir / out_name

    if out_path.exists():
        if not click.confirm(f"[yellow]{out_name}[/yellow] exists. Overwrite?", default=False):
            console.print("[yellow]Skipped.[/yellow]")
            return

    console.print(f"Cleaning [cyan]{file_path.name}[/cyan] ...")

    try:
        cleaned = clean_file(file_path, organic=False, in_place=False,
                             output_dir=out_dir / out_name)
        if cleaned.name != out_name:
            dest = cleaned.parent / out_name
            if cleaned.exists():
                cleaned.rename(dest)
                cleaned = dest

        console.print(f"[green]Saved:[/green] {cleaned}")
        console.print()

        # Show remaining metadata
        remaining = analyze_file(cleaned)
        if remaining.get("is_ai"):
            console.print(f"[yellow]⚠ AI metadata may remain: {remaining.get('ai_tool')}[/yellow]")
        else:
            console.print("[green]✓ No AI metadata detected[/green]")

        meta = dump_image(cleaned)
        exif_count = 0
        for ifd_name, ifd_data in meta.get('exif', {}).items():
            if isinstance(ifd_data, dict):
                exif_count += len(ifd_data.get('tags', {}))
        if exif_count:
            console.print(f"[blue]Metadata:[/blue] {exif_count} EXIF tags remain")
        else:
            console.print("[blue]Metadata:[/blue] Fully stripped")

        if meta.get('text_chunks'):
            console.print(f"[blue]Text chunks:[/blue] {len(meta['text_chunks'])}")
        if meta.get('c2pa'):
            console.print(f"[blue]C2PA:[/blue] Present - not fully stripped")
        if meta.get('camera'):
            console.print(f"[blue]Camera:[/blue] {meta['camera'].get('make', '?')} {meta['camera'].get('model', '?')}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

    click.pause("Press any key to continue...")


def _data_manipulate(console: Console, file_path: Path, fmt: str | None):
    from metascrub.cleaner import clean_image
    while True:
        console.print()
        console.print(f"[bold]Data Manipulation - [cyan]{file_path.name}[/cyan][/bold]")
        table = Table(box=box.SIMPLE)
        table.add_column("Option", style="dim", width=8)
        table.add_column("Action", style="cyan")
        table.add_row("[A]", "Auto Organic - inject realistic camera EXIF")
        table.add_row("[C]", "Custom Edit - manually type all metadata")
        table.add_row("[D]", "Add Design App - Photoshop/Procreate/Canva style")
        table.add_row("[B]", "← Back")
        console.print(table)

        action = click.prompt("Choose", default="", show_default=False).strip().lower()
        out_dir = Path("output").resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        if action in ("a", "auto"):
            default_name = f"{file_path.stem}_organic"
            name = click.prompt("Output filename", default=default_name, show_default=True).strip()
            if not name:
                name = default_name
            out_path = out_dir / f"{name}{file_path.suffix}"

            data = file_path.read_bytes()
            w, h = _get_image_dimensions(file_path, fmt)
            blob = make_organic_exif_blob(w, h)
            cleaned = clean_image(data, fmt, organic=blob)
            out_path.write_bytes(cleaned)
            console.print(f"[green]✓ Organic EXIF injected → {out_path}[/green]")
            click.pause("Press any key to continue...")

        elif action in ("c", "custom"):
            console.print(f"  [bold]Custom EXIF for [cyan]{file_path.name}[/cyan]:[/bold]")
            console.print("  (press Enter to skip any field)")

            make = click.prompt("    Camera Make", default="").strip()
            model = click.prompt("    Camera Model", default="").strip()
            lens = click.prompt("    Lens", default="").strip()
            software = click.prompt("    Software", default="").strip()
            date_str = click.prompt("    Date/Time (YYYY:MM:DD HH:MM:SS)", default="").strip()
            iso_raw = click.prompt("    ISO", default="").strip()
            fstop_raw = click.prompt("    F-Stop (e.g. 2.8)", default="").strip()
            shutter_raw = click.prompt("    Shutter Speed (e.g. 1/250)", default="").strip()
            focal_raw = click.prompt("    Focal Length (e.g. 50)", default="").strip()
            description = click.prompt("    Image Description", default="").strip()
            artist = click.prompt("    Artist", default="").strip()
            copyright_s = click.prompt("    Copyright", default="").strip()

            iso = int(iso_raw) if iso_raw.isdigit() else None
            focal = (int(focal_raw), 1) if focal_raw.isdigit() else None
            fnumber_val = None
            if fstop_raw:
                try:
                    fval = float(fstop_raw)
                    fnumber_val = (int(fval * 10), 10)
                except ValueError:
                    pass
            shutter_val = None
            if shutter_raw:
                try:
                    if "/" in shutter_raw:
                        num, den = shutter_raw.split("/")
                        shutter_val = (int(num), int(den))
                    else:
                        shutter_val = (1, int(shutter_raw))
                except ValueError:
                    pass

            w, h = _get_image_dimensions(file_path, fmt)
            blob = make_custom_exif_blob(
                width=w, height=h,
                make=make or None, model=model or None,
                lens=lens or None, date_str=date_str or None,
                iso=iso, fnumber=fnumber_val,
                shutter=shutter_val, focal=focal,
            )

            # Inject description/artist/copyright into the blob
            if description or artist or copyright_s:
                import piexif
                exif_dict = piexif.load(blob)
                if description:
                    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = description.encode()
                if artist:
                    exif_dict['0th'][piexif.ImageIFD.Artist] = artist.encode()
                if copyright_s:
                    exif_dict['0th'][piexif.ImageIFD.Copyright] = copyright_s.encode()
                if software:
                    exif_dict['0th'][piexif.ImageIFD.Software] = software.encode()
                blob = piexif.dump(exif_dict)

            default_name = f"{file_path.stem}_custom"
            name = click.prompt("Output filename", default=default_name, show_default=True).strip()
            if not name:
                name = default_name
            out_path = out_dir / f"{name}{file_path.suffix}"

            data = file_path.read_bytes()
            cleaned = clean_image(data, fmt, organic=blob)
            out_path.write_bytes(cleaned)
            console.print(f"[green]✓ Custom EXIF injected → {out_path}[/green]")
            click.pause("Press any key to continue...")

        elif action in ("d", "design"):
            default_name = f"{file_path.stem}_design"
            name = click.prompt("Output filename", default=default_name, show_default=True).strip()
            if not name:
                name = default_name
            out_path = out_dir / f"{name}{file_path.suffix}"

            data = file_path.read_bytes()
            w, h = _get_image_dimensions(file_path, fmt)
            blob = make_design_exif_blob(w, h)
            cleaned = clean_image(data, fmt, organic=blob)
            out_path.write_bytes(cleaned)
            console.print(f"[green]✓ Design-app metadata injected → {out_path}[/green]")
            click.pause("Press any key to continue...")

        elif action in ("b", "back"):
            return
        else:
            console.print("[red]Invalid option.[/red]")


def _parse_selection(choice: str, total: int) -> list[int]:
    if not choice:
        return []
    selected = set()
    parts = [p.strip() for p in choice.split(",")]
    for part in parts:
        if not part:
            continue
        m = re.match(r"^(\d+)-(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            selected.update(range(max(1, start), min(total, end) + 1))
        elif part.isdigit():
            n = int(part)
            if 1 <= n <= total:
                selected.add(n)
    return sorted(s - 1 for s in selected if 1 <= s <= total)


def _get_image_dimensions(path: Path, fmt: str | None) -> tuple:
    try:
        from PIL import Image
        img = Image.open(path)
        return img.size
    except Exception:
        return None, None
