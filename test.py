from rich.console import Console

"""Development script for listing Apple Notes without using the AI model."""

# Reuse the app's real Notes client so the test exercises production code.
from aiagents.notes_client import AppleNotesClient

console = Console()

def list_notes() -> str:
    """Use the same Notes client as the app, making this a useful smoke test."""
    # Create a temporary client and return its list result without OpenAI.
    return AppleNotesClient().list_notes()


if __name__ == "__main__":
    console.print("\n[bold green]Assistant:[/]")
