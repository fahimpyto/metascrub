from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

BANNER_ART = r"""
███████╗██████╗ ██████╗ ██████╗ ██████╗ ██████╗ ██████╗ ██╗   ██╗██████╗
██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██║   ██║██╔══██╗
█████╗  ███████╗██████╗ ███████╗██████╗ ███████╗██████╗ ██║   ██║██████╔╝
██╔══╝  ╚════██║╚════██║╚════██║╚════██║╚════██║╚════██║██║   ██║██╔══██╗
███████╗███████║██████╔╝███████║██████╔╝███████║██████╔╝╚██████╔╝██████╔╝
╚══════╝╚══════╝╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═════╝ ╚═════╝ ╚═════╝
"""


def print_banner(console: Console, version: str) -> None:
    text = Text(BANNER_ART, style="bold cyan")
    text.append(f"\n  v{version}", style="bold yellow")
    text.append("  |  Strip AI metadata from images", style="white")

    panel = Panel(
        Align.center(text),
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(panel)
