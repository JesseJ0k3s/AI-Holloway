"""Minimal Claude API client using only the Python standard library.

Deliberately no `pip install anthropic`. Five people on five laptops with 2.5
days is not the time to debug virtualenvs. This is ~60 lines of urllib and it
works on a stock macOS Python 3.9.

Set your key once:

    export ANTHROPIC_API_KEY=sk-ant-...

If no key is present, callers fall back to the rule-based mock engine in
extract.py so the pipeline ALWAYS produces a dashboard. Never let the live demo
depend on a network call succeeding in a classroom.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# Sonnet is the right call here: extraction is high-volume, low-difficulty
# structured output. Opus is overkill and ~5x the cost for this workload.
DEFAULT_MODEL = "claude-sonnet-4-5"


class LLMUnavailable(RuntimeError):
    """Raised when we cannot reach Claude; callers should fall back to mock."""


def have_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1500,
    temperature: float = 0.0,
    retries: int = 3,
) -> str:
    """Send one message to Claude and return the text of the reply."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not set")

    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": API_VERSION,
        },
        method="POST",
    )

    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
            return "".join(parts).strip()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            last_err = RuntimeError("HTTP %s: %s" % (e.code, detail))
            # 429 and 5xx are worth retrying; 400/401 are not.
            if e.code not in (429, 500, 502, 503, 529):
                break
            time.sleep(2 ** attempt)
        except Exception as e:  # network hiccups
            last_err = e
            time.sleep(2 ** attempt)

    raise LLMUnavailable("Claude call failed: %s" % last_err)


def complete_json(prompt: str, system: str = "", **kw: Any) -> Any:
    """Same as complete(), but parse the reply as JSON.

    Models sometimes wrap JSON in prose or a ```json fence. We strip both
    rather than fighting the model about it.
    """
    raw = complete(prompt, system=system, **kw)
    return parse_json_loose(raw)


def parse_json_loose(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: grab the outermost bracketed span.
        for open_c, close_c in (("[", "]"), ("{", "}")):
            i, j = text.find(open_c), text.rfind(close_c)
            if i != -1 and j > i:
                try:
                    return json.loads(text[i : j + 1])
                except json.JSONDecodeError:
                    continue
        raise
