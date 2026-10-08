"""Application settings and project paths."""

import os  # Lets us read OPENAI_API_KEY from the environment.
from dataclasses import dataclass  # Makes a small class for related settings.
from pathlib import Path  # Builds file paths safely on every operating system.

from dotenv import load_dotenv  # Loads variables from the local .env file.


# Walk from src/notesagent/config.py back to the project folder.
PROJECT_ROOT = Path(__file__).parents[2]
# The agent reads its behavior instructions from this separate text file.
PROMPT_FILE = Path(__file__).parent / "prompts" / "system_prompt.txt"


@dataclass(frozen=True)
class Settings:
    """Settings shared by the agent and Apple Notes client."""

    # The secret used to authenticate OpenAI requests.
    api_key: str
    # The model used by the agent to answer questions and select tools.
    model: str = "gpt-5.6"
    # The maximum number of Notes records returned by one request.
    max_notes: int = 100
    # The path to the system prompt text read when the agent starts.
    prompt_file: Path = PROMPT_FILE


def load_settings() -> Settings:
    """Load configuration from the project's .env file."""
    # Load .env explicitly from the project root, regardless of the current folder.
    load_dotenv(PROJECT_ROOT / ".env")
    # Read the key only after .env has been loaded.
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Stop early so requests are never sent without credentials.
        raise ValueError("OPENAI_API_KEY was not found in your .env file")
    # Bundle the values into one immutable Settings object.
    return Settings(api_key=api_key)

# print(Settings.model)
# print(Settings.max_notes)
