from pathlib import Path
import re

import click
from rich.console import Console
from rich.table import Table
from rich import box

from metascrub.scanner import scan_and_analyze
from metascrub.formatter import print_scan_results
from metascrub.cleaner import clean_file, get_format
from metascrub.injector import make_custom_exif_blob, make_organic_exif_blob, inject_canva_metadata

console = Console()


def run_interactive_scan(path: Path, recursive: bool = False):
    scan_path = path.resolve()
    console.print(f"Scanning [cyan]{scan_path}[/cyan] ...")
    results = scan_and_analyze(scan_path, recursive=recursive)

    if not results:
        console.print("[yellow]No image files found.[/yellow]")
        return

    print_scan_results(console, results)

    ai_files = [r for r in results if r.get("is_ai")]
    if not ai_files:
        console.print("[green]No images with detected metadata.[/green]")
        return

    console.print()
    table = Table(box=box.ROUNDED, title="Labeled Images", style="bold red")
    table.add_column("#", style="dim", width=4)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Tool", style="yellow")
    for i, r in enumerate(ai_files, 1):
        table.add_row(
            str(i),
            Path(r["path"]).name,
            r.get("format", "?"),
            r.get("ai_tool") or "Unknown",
        )
    console.print(table)

    prompt = "Select files to process (e.g. 1,3,5 / 1-5 / [Enter]=all / q=quit): "
    choice = click.prompt(prompt, default="", show_default=False).strip()

    if choice.lower() == "q":
        console.print("[yellow]Cancelled.[/yellow]")
        return

    selected = _parse_selection(choice, len(ai_files))
    if not selected:
        console.print("[yellow]No files selected.[/yellow]")
        return

    out_dir = None
    out_choice = click.prompt(
        "Output folder (in-place saves here, or enter folder name)",
        default="", show_default=False
    ).strip()
    if out_choice:
        out_dir = scan_path / out_choice
        out_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Output folder: [cyan]{out_dir}[/cyan]")

    clean_summary = []
    for idx in selected:
        r = ai_files[idx - 1]
        file_path = Path(r["path"])
        fmt = r.get("format")
        console.print()
        console.print(f"[bold]Processing [cyan]{file_path.name}[/cyan] ...[/bold]")

        try:
            cleaned_path = clean_file(file_path, organic=False, in_place=out_dir is None,
                                      output_dir=out_dir)

            exif_choice = click.prompt(
                f"  Inject metadata for [cyan]{file_path.name}[/cyan]? (s)kip / (a)uto EXIF / (p)ersonalize / (c)anva",
                default="s",
                show_default=False,
            ).strip().lower()

            if exif_choice == "a":
                cleaned_path = clean_file(file_path, organic=True, in_place=out_dir is None,
                                          output_dir=out_dir)
                exif_label = "EXIF: auto (camera)"
            elif exif_choice == "p":
                cleaned_path = _do_personalized_exif(file_path, fmt, out_dir)
                exif_label = "EXIF: custom (camera)"
            elif exif_choice == "c":
                target = cleaned_path
                inject_canva_metadata(target, fmt=fmt)
                exif_label = "Canva metadata"
            else:
                exif_label = "none"

            out_name = cleaned_path.name if out_dir else file_path.name
            clean_summary.append((out_name, "OK Cleaned", r.get("ai_tool"), exif_label))
        except Exception as e:
            console.print(f"  [red]Error: {e}[/red]")
            clean_summary.append((file_path.name, "FAILED", r.get("ai_tool"), str(e)))

    console.print()
    _print_interactive_summary(clean_summary)


def _parse_selection(choice: str, total: int) -> list[int]:
    if not choice:
        return list(range(1, total + 1))

    selected = set()
    parts = [p.strip() for p in choice.split(",")]
    for part in parts:
        if not part:
            continue
        m = re.match(r"^(\d+)-(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            selected.update(range(start, end + 1))
        elif part.isdigit():
            n = int(part)
            if 1 <= n <= total:
                selected.add(n)
    return sorted(s for s in selected if 1 <= s <= total)


def _do_personalized_exif(file_path: Path, fmt: str | None, out_dir: Path | None = None) -> Path:
    console.print(f"  [bold]Personalized EXIF for [cyan]{file_path.name}[/cyan]:[/bold]")
    console.print("  (press Enter for auto defaults)")

    make = click.prompt("    Camera Make", default="").strip()
    model = click.prompt("    Camera Model", default="").strip()
    lens = click.prompt("    Lens", default="").strip()
    date_str = click.prompt("    Date/Time (YYYY:MM:DD HH:MM:SS)", default="").strip()

    width, height = _get_image_dimensions(file_path, fmt)
    exif_blob = make_custom_exif_blob(
        width=width,
        height=height,
        make=make or None,
        model=model or None,
        lens=lens or None,
        date_str=date_str or None,
    )
    return clean_file(file_path, organic=exif_blob, in_place=out_dir is None,
                      output_dir=out_dir)


def _get_image_dimensions(path: Path, fmt: str | None) -> tuple:
    try:
        from PIL import Image
        img = Image.open(path)
        return img.size
    except Exception:
        return None, None


def _print_interactive_summary(summary: list):
    table = Table(box=box.ROUNDED, title="Interactive Session Summary")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Tool", style="yellow")
    table.add_column("EXIF", style="green")

    for name, status, tool, exif in summary:
        status_col = "[green]OK Cleaned[/green]" if status == "OK Cleaned" else f"[red]{status}[/red]"
        table.add_row(name, status_col, tool or "--", exif)

    console.print(table)
    success = sum(1 for _, s, _, _ in summary if s == "OK Cleaned")
    console.print(f"[bold]{success}[/bold] cleaned  *  [red]{len(summary) - success} failed[/red]")
