"""Sends a requirement to an LLM and returns a validated Analysis.

Two providers are supported, chosen with LLM_PROVIDER in .env:
  gemini  (default) - Google Gemini API, has a free tier
  claude            - Anthropic Claude API, paid per use
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from .schema import Analysis, tool_input_schema

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "claude": "claude-sonnet-5-5"}
TOOL_NAME = "submit_analysis"


def current_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider not in DEFAULT_MODELS:
        raise ValueError(f"LLM_PROVIDER must be one of {list(DEFAULT_MODELS)}, got '{provider}'")
    return provider


def current_model() -> str:
    return os.getenv("BA_MODEL", DEFAULT_MODELS[current_provider()])


def current_prompt_version() -> str:
    return os.getenv("PROMPT_VERSION", "v1")


def load_prompt(version: str | None = None) -> str:
    version = version or current_prompt_version()
    return (ROOT / "prompts" / f"{version}.md").read_text(encoding="utf-8")


def _user_message(requirement: str) -> str:
    return f"<requirement>\n{requirement}\n</requirement>"


def _call_gemini(system: str, requirement: str, model: str) -> str:
    from google import genai
    from google.genai import types

    # reads GEMINI_API_KEY; give up on a call after 3 minutes instead of waiting forever
    client = genai.Client(http_options=types.HttpOptions(timeout=180_000))
    response = client.models.generate_content(
        model=model,
        contents=_user_message(requirement),
        config=types.GenerateContentConfig(
            system_instruction=system + "\n\nReturn only JSON that matches the provided schema.",
            response_mime_type="application/json",
            response_json_schema=tool_input_schema(),
            temperature=0.2,
        ),
    )
    return response.text


def _call_claude(system: str, requirement: str, model: str) -> str:
    import json

    import anthropic

    client = anthropic.Anthropic(timeout=180)  # reads ANTHROPIC_API_KEY
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system,
        tools=[{
            "name": TOOL_NAME,
            "description": "Submit the full business analysis for the requirement.",
            "input_schema": tool_input_schema(),
        }],
        tool_choice={"type": "tool", "name": TOOL_NAME},
        messages=[{"role": "user", "content": _user_message(requirement)}],
    )
    if response.stop_reason == "max_tokens":
        raise RuntimeError("The output was cut off. Raise max_tokens or shorten the requirement.")
    for block in response.content:
        if block.type == "tool_use" and block.name == TOOL_NAME:
            return json.dumps(block.input)
    raise RuntimeError("The model did not return a submit_analysis call.")


def analyse(requirement: str, *, model: str | None = None, prompt_version: str | None = None,
            retries: int = 2) -> Analysis:
    provider = current_provider()
    model = model or current_model()
    call = _call_gemini if provider == "gemini" else _call_claude
    system = load_prompt(prompt_version)

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return Analysis.model_validate_json(call(system, requirement, model))
        except ValidationError as e:
            last_error = e  # malformed output: ask again
        except Exception as e:
            # 429 = free-tier rate limit, 503 = model temporarily overloaded: wait and retry
            msg = str(e)
            transient = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "timed out", "Timeout", "504")
            if any(code in msg or code in type(e).__name__ for code in transient):
                last_error = e
                wait = 30 * (attempt + 1)
                print(f"  provider busy, retrying in {wait}s ...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"No valid output after {retries + 1} attempts: {last_error}")
