"""Apple Notes AI agent package."""

# Re-export main so the command in pyproject.toml can use aiagents:main.
from .main import main

# Limit what `from aiagents import *` exposes to the public entry function.
__all__ = ["main"]
