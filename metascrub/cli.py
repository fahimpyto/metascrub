from pathlib import Path
import sys

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from metascrub import __version__
from metascrub.scanner import scan_and_analyze, analyze_file
from metascrub.cleaner import clean_file, get_format
from metascrub.detectors import detect_ai_image
from metascrub.formatter import print_scan_results, print_image_info

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(__version__, prog_name="mtsb")
@click.pass_context
def cli(ctx):
    from metascrub.banner import print_banner
    print_banner(console, __version__)
    if ctx.invoked_subcommand is None:
        click.echo(cli.get_help(ctx))


@cli.command()
@click.option('-p', '--path', type=click.Path(exists=True, file_okay=False),
              default='.', help='Directory to scan')
@click.option('-r', '--recursive', is_flag=True, help='Scan subdirectories')
def scan(path, recursive):
    """Scan folder interactively - pick images to process."""
    from metascrub.interactive import run_interactive_scan
    scan_path = Path(path).resolve()
    run_interactive_scan(console, scan_path, recursive=recursive)


@cli.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def info(file, as_json):
    """Show ALL metadata for an image - every detail extracted."""
    from metascrub.dumper import dump_image
    path = Path(file).resolve()
    fmt = get_format(path)
    if not fmt:
        console.print(f"[red]Unsupported format: {path.suffix}[/red]")
        sys.exit(1)
    data = dump_image(path)
    if as_json:
        import json
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        from metascrub.formatter import print_dump
        print_dump(console, data)


@cli.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
def status(file):
    """Quick check: is this image AI-generated?"""
    path = Path(file).resolve()
    fmt = get_format(path)
    if not fmt:
        console.print(f"[red]Unsupported format: {path.suffix}[/red]")
        sys.exit(1)
    data = path.read_bytes()
    ai_info = detect_ai_image(data, fmt)
    if ai_info["is_ai"]:
        tool = ai_info.get("tool") or "Unknown"
        console.print(f"[red]YES[/red] - {tool}")
    else:
        console.print("[green]NO[/green] - No AI metadata detected")


@cli.command()
@click.argument('file', type=click.Path(exists=True, dir_okay=False))
@click.option('-o', '--output', type=click.Path(file_okay=False),
              help='Output directory (default: ./output)')
@click.option('-n', '--name', help='Output filename (without extension)')
@click.option('--organic', is_flag=True,
              help='Inject realistic camera EXIF after cleaning')
@click.option('--design', is_flag=True,
              help='Inject design-app metadata (Photoshop/Procreate)')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def clean(file, output, name, organic, design, dry_run):
    """Strip AI metadata and save to output folder.

    Always saves to output/ - never modifies original.
    """
    path = Path(file).resolve()
    fmt = get_format(path)
    if not fmt:
        console.print(f"[red]Unsupported format: {path.suffix}[/red]")
        sys.exit(1)

    out_dir = Path(output or 'output').resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if name:
        out_name = f"{name}{path.suffix}"
    else:
        out_name = f"{path.stem}_cleaned{path.suffix}"

    if dry_run:
        console.print(f"[yellow]Would clean:[/yellow] {path.name}")
        if organic:
            console.print(f"  + inject organic camera EXIF")
        if design:
            console.print(f"  + inject design-app metadata")
        console.print(f"  -> [cyan]{out_dir / out_name}[/cyan]")
        return

    try:
        inject_exif = bool(organic)
        exif_blob = None
        if design:
            w, h = _get_dimensions(path)
            from metascrub.injector import make_design_exif_blob
            exif_blob = make_design_exif_blob(w, h)

        cleaned_path = clean_file(path, inject_exif=inject_exif, exif_blob=exif_blob,
                                  in_place=False, output_dir=out_dir)
        dest = out_dir / out_name
        if cleaned_path != dest:
            if dest.exists():
                dest.unlink()
            cleaned_path.rename(dest)
            cleaned_path = dest

        console.print(f"[green]Cleaned:[/green] {cleaned_path.name}")
        console.print(f"[green]Output:[/green] {cleaned_path.parent}")

        # Re-scan and show remaining metadata
        remaining = analyze_file(cleaned_path)
        if remaining.get("is_ai"):
            console.print(f"[yellow]Warning: AI metadata may remain: {remaining.get('ai_tool')}[/yellow]")
        else:
            console.print("[green]No AI metadata detected in cleaned file.[/green]")

        # Show what metadata the cleaned file carries
        from metascrub.dumper import dump_image
        meta = dump_image(cleaned_path)
        exif_count = 0
        for ifd_name, ifd_data in meta.get('exif', {}).items():
            if isinstance(ifd_data, dict):
                exif_count += len(ifd_data.get('tags', {}))
        if exif_count:
            console.print(f"[blue]Metadata remaining:[/blue] {exif_count} EXIF tags")
        else:
            console.print("[blue]Metadata remaining:[/blue] None (fully stripped)")
        if meta.get('text_chunks'):
            console.print(f"[blue]Text chunks:[/blue] {len(meta['text_chunks'])}")
        if meta.get('c2pa'):
            console.print(f"[blue]C2PA manifest:[/blue] Present ({meta['c2pa'].get('claim_generator', '?')})")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _get_dimensions(path: Path) -> tuple:
    try:
        from PIL import Image
        img = Image.open(path)
        return img.size
    except Exception:
        return None, None


if __name__ == '__main__':
    cli()
