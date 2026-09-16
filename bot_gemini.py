"""Gemini entry point; configuration comes from .env."""
from quiz_runner import run

if __name__ == "__main__":
    raise SystemExit(run("gemini"))
