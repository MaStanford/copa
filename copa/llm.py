"""LLM backend abstraction for Copa description generation."""

from __future__ import annotations

import json
import shutil
import subprocess


PROMPT_TEMPLATE = (
    "Given this shell command, write a short description (under 15 words) "
    "of what it does. Output only the description.\n\n"
    "Command: {command}"
)


def generate_description(
    command: str, backend: str = "claude", model: str | None = None
) -> str | None:
    """Generate a description for a command using the configured LLM backend.

    Returns the generated description, or None on failure.
    """
    prompt = PROMPT_TEMPLATE.format(command=command)

    if backend == "claude":
        return _generate_claude(prompt)
    elif backend == "ollama":
        return _generate_ollama(prompt, model or "llama3.2:3b")
    else:
        return None


def _generate_claude(prompt: str) -> str | None:
    """Generate using the claude CLI."""
    if not shutil.which("claude"):
        return None

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return _clean_response(result.stdout.strip())
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def _generate_ollama(prompt: str, model: str) -> str | None:
    """Generate using ollama HTTP API."""
    try:
        import requests
    except ImportError:
        return None

    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            response_text = data.get("response", "").strip()
            if response_text:
                return _clean_response(response_text)
    except Exception:
        pass

    return None


def _clean_response(text: str) -> str:
    """Clean up an LLM response — strip quotes, trailing punctuation, etc."""
    text = text.strip().strip('"').strip("'")
    # Remove leading "Description: " if the model echoed the prompt format
    for prefix in ("Description:", "description:"):
        if text.lower().startswith(prefix.lower()):
            text = text[len(prefix):].strip()
    # Truncate to first line only
    text = text.split("\n")[0].strip()
    return text


def check_ollama_available() -> tuple[bool, str]:
    """Check if ollama is installed and running.

    Returns (is_ready, message).
    """
    if not shutil.which("ollama"):
        return False, "ollama is not installed. Install from https://ollama.com"

    try:
        import requests
    except ImportError:
        return False, "requests package not installed. Run: pip install copa[ollama]"

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            return True, "ollama is running"
    except Exception:
        pass

    return False, "ollama is not running. Start with: ollama serve"


def check_ollama_model(model: str) -> tuple[bool, list[str]]:
    """Check if a specific model is available in ollama.

    Returns (model_available, list_of_available_models).
    """
    try:
        import requests
    except ImportError:
        return False, []

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return model in models, models
    except Exception:
        pass

    return False, []
