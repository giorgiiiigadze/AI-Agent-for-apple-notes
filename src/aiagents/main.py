"""Terminal entry point for the Apple Notes agent."""

from .agent import NotesAgent  # Handles conversation and OpenAI tool calls.
from .config import load_settings  # Reads API key and app configuration.
from .notes_client import AppleNotesClient  # Talks to the native Notes app.
from rich.console import Console  # Prints styled output without breaking the spinner.
from rich.prompt import Confirm  # Provides a yes/no prompt with a safe default.
from rich.text import Text  # Keeps note titles literal in Rich prompts.


def main() -> None:
    """Start an interactive Apple Notes conversation."""
    # Rich owns terminal output so its live spinner stays visually stable.
    console = Console()
    # Create one settings object for this app session.
    settings = load_settings()
    # Create the macOS Notes bridge using the configured result limit.
    notes = AppleNotesClient(max_notes=settings.max_notes)
    status = console.status("[bold cyan]Thinking...", spinner="dots")

    def confirm_delete(title: str) -> bool:
        """Ask the terminal user; only an explicit yes permits deletion."""
        status.stop()
        try:
            return Confirm.ask(Text(f'Delete “{title}”?'), console=console, default=True)
        except EOFError:
            return False
        finally:
            status.start()

    # Show Notes actions above the spinner whenever the model calls a local tool.
    def show_tool_call(name: str, arguments: dict) -> None:
        console.print(f"  [dim][Apple Notes] {name}({arguments})[/dim]")

    # Give the agent its OpenAI settings, Notes capability, and UI callback.
    agent = NotesAgent(settings, notes, confirm_delete=confirm_delete, on_tool_call=show_tool_call)

    # Show which model is active before asking for terminal input.
    console.print(f"Apple Notes assistant ({settings.model}) — Ctrl+C to quit")
    try:
        while True:
            # Wait for a user question and remove accidental surrounding spaces.
            question = console.input("\n[bold]You:[/] ").strip()
            if question:
                # Animate dots until the API and any requested tools finish.
                with status:
                    answer = agent.ask(question)
                # Print after the spinner stops, so the answer has a clean line.
                console.print("\n[bold green]Assistant:[/]", answer)
    except (EOFError, KeyboardInterrupt):
        # Exit cleanly when the terminal closes or the user presses Ctrl+C.
        console.print("\nBye!")
