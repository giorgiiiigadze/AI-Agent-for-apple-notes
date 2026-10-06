"""Compatibility entry point for the Apple Notes agent.

The implementation now lives in the aiagents package.
Run with: uv run python notes.py
"""

# Import the real entry function from the new package structure.
from aiagents.main import main


if __name__ == "__main__":
    # Run only when this file is started directly, not when it is imported.
    main()
