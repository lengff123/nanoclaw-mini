"""
Entry point for running nanoclaw-mini as a module: python -m nanoclaw_mini
"""

from nanoclaw_mini.cli.commands import app

if __name__ == "__main__":
    app()
