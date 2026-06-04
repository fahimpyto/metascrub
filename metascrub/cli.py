from pathlib import Path
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from metascrub import __version__
from metascrub.scanner import scan_and_analyze, analyze_file
from metascrub.cleaner import clean_file, get_format, clean_image
from metascrub.detectors import detect_ai_image
from metascrub.formatter import print_scan_results, print_clean_results, print_image_info


console = Console()


@click.group()
@click.version_option(__version__, prog_name="metascrub")
def cli():
    """metascrub — Strip AI metadata from images.

    Scans folders for AI-generated images (DALL-E, Midjourney,
    Stable Diffusion, ComfyUI, etc.) and strips their metadata.

    Optionally injects realistic camera EXIF for an "organic" look.
    """
    pass


@cli.command()
@click.option('-p', '--path', type=click.Path(exists=True, file_okay=False),
              default='.', help='Directory to scan')
@click.option('-r', '--recursive', is_flag=True, help='Scan subdirectories')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def scan(path, recursive, as_json):
    """Scan folder for images with AI metadata."""
    scan_path = Path(path).resolve()
    console.print(f"Scanning [cyan]{scan_path}[/cyan] ...")

    results = scan_and_analyze(scan_path, recursive=recursive)

    if as_json:
        import json
        click.echo(json.dumps(results, indent=2, default=str))
    else:
        print_scan_results(console, results)


@cli.command()
@click.argument('targets', nargs=-1, required=False)
@click.option('-p', '--path', type=click.Path(exists=True, file_okay=False),
              help='Directory to process (alternative to file args)')
@click.option('-r', '--recursive', is_flag=True, help='Process subdirectories')
@click.option('-o', '--output', type=click.Path(file_okay=False),
              help='Output directory (keeps originals)')
@click.option('--organic', is_flag=True,
              help='Inject realistic camera EXIF after cleaning')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
@click.option('-y', '--yes', is_flag=True, help='Skip confirmation')
def clean(targets, path, recursive, output, organic, dry_run, yes):
    """Strip AI metadata from images.

    TARGETS can be files or glob patterns (e.g. *.jpg *.png).

    If no TARGETS given, uses --path (default: current directory).
    """
    files_to_clean = []

    if targets:
        for t in targets:
            t_path = Path(t)
            if t_path.is_file():
                files_to_clean.append(t_path)
            else:
                from glob import glob
                matched = [Path(f) for f in glob(t, recursive=False)]
                files_to_clean.extend(matched)
    else:
        scan_path = Path(path or '.').resolve()
        from metascrub.scanner import scan_folder
        files_to_clean = scan_folder(scan_path, recursive=recursive)

    if not files_to_clean:
        console.print("[yellow]No image files found to clean.[/yellow]")
        return

    supported = [f for f in files_to_clean if get_format(f)]
    unsupported = [f for f in files_to_clean if not get_format(f)]

    if unsupported:
        console.print(f"[yellow]Skipping {len(unsupported)} unsupported files[/yellow]")

    if not supported:
        console.print("[yellow]No supported image files found.[/yellow]")
        return

    console.print(f"Found [cyan]{len(supported)}[/cyan] image(s) to process")

    if dry_run:
        console.print("\n[bold]Dry run — would process:[/bold]")
        for f in supported:
            ai_info = analyze_file(f)
            tool = ai_info.get("ai_tool", "—") if ai_info.get("is_ai") else "clean"
            organic_str = " + organic EXIF" if organic else ""
            console.print(f"  {f.name} ({tool}){organic_str}")
        return

    if not yes and len(supported) > 3:
        click.confirm(
            f"Clean {len(supported)} image(s)? This modifies files in-place.",
            abort=True
        )

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Cleaning...", total=len(supported))

        for f in supported:
            try:
                ai_info = analyze_file(f)
                out_path = clean_file(
                    f,
                    organic=organic,
                    in_place=output is None,
                    output_dir=Path(output) if output else None,
                )
                results.append({
                    "path": str(f),
                    "success": True,
                    "ai_tool": ai_info.get("ai_tool"),
                    "output": str(out_path) if output else "in-place",
                })
            except Exception as e:
                results.append({
                    "path": str(f),
                    "success": False,
                    "error": str(e),
                })
            progress.update(task, advance=1)

    print_clean_results(console, results)


@cli.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def info(file, as_json):
    """Show detailed metadata for a single image."""
    path = Path(file).resolve()
    fmt = get_format(path)

    if not fmt:
        console.print(f"[red]Unsupported format: {path.suffix}[/red]")
        sys.exit(1)

    data = path.read_bytes()
    ai_info = detect_ai_image(data, fmt)

    exif_info = {}
    try:
        if fmt == 'jpeg':
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS as EXIF_TAGS
                img = Image.open(path)
                exif = img.getexif()
                for tag_id, value in exif.items():
                    name = EXIF_TAGS.get(tag_id, f"0x{tag_id:04X}")
                    exif_info[name] = str(value)[:200]
            except Exception:
                import piexif
                exif_dict = piexif.load(str(path))
                for ifd_name in ('0th', 'Exif', 'GPS', '1st'):
                    ifd = exif_dict.get(ifd_name, {})
                    for tag_id, value in ifd.items():
                        exif_info[f"{ifd_name}:0x{tag_id:04X}"] = str(value)[:200]
        elif fmt == 'png':
            from metascrub.png_cleaner import read_chunks
            chunks = read_chunks(data)
            for ct, cd, _ in chunks:
                if ct in (b'tEXt', b'iTXt', b'zTXt'):
                    null_pos = cd.find(b'\0')
                    if null_pos > 0:
                        key = cd[:null_pos].decode('latin-1', errors='replace')
                        val = cd[null_pos+1:].decode('latin-1', errors='replace')
                        exif_info[f"PNG:{key}"] = val[:200]
                elif ct == b'eXIf':
                    exif_info["PNG:eXIf"] = f"<{len(cd)} bytes EXIF data>"
                elif ct in (b'caBX', b'caMs', b'caSt'):
                    exif_info[f"PNG:{ct.decode()}"] = f"<C2PA chunk {len(cd)} bytes>"
    except Exception as e:
        exif_info["_error"] = str(e)

    metadata = {
        "path": str(path),
        "format": fmt,
        "size": path.stat().st_size,
        "is_ai": ai_info["is_ai"],
        "ai_tool": ai_info["tool"],
        "exif": exif_info,
        "error": None,
    }

    if as_json:
        import json
        click.echo(json.dumps(metadata, indent=2, default=str))
    else:
        print_image_info(console, path, metadata)


if __name__ == '__main__':
    cli()
