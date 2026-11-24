from . import claude_code, claude_desktop, codex, gemini, vscode
from .common import load_shell_files

DISCOVERERS = [claude_code, codex, gemini, claude_desktop, vscode]


def discover_all(ctx) -> None:
    for d in DISCOVERERS:
        d.discover(ctx)
    load_shell_files(ctx)
