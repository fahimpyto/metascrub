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
