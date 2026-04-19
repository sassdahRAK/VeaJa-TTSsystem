"""
gui/pages/_ai_caller.py
=======================
Lightweight AI API caller used by Ask, Generate, Grammar, and Code tabs.

Best-model routing per task:
  • code / debug / explain  → Claude (best), then OpenAI, then Gemini
  • generate / creative     → Gemini (best long-context), then OpenAI, then Claude
  • grammar / rewrite       → OpenAI (best prose), then Claude, then Gemini
  • ask / general Q&A       → OpenAI, then Gemini, then Claude

All calls are synchronous — run them in a QThread.
"""

from __future__ import annotations
import json
import urllib.request
import urllib.error


# ── Task → preferred provider order ──────────────────────────────────────────
_ROUTING: dict[str, list[str]] = {
    "code":     ["claude", "openai", "gemini"],
    "generate": ["gemini", "openai", "claude"],
    "grammar":  ["openai", "claude", "gemini"],
    "ask":      ["openai", "gemini", "claude"],
}


def get_api_keys(mixin) -> dict[str, str]:
    """Pull live key values from the mixin's _api_key_inputs dict."""
    if not hasattr(mixin, "_api_key_inputs"):
        return {}
    return {k: f.text().strip() for k, f in mixin._api_key_inputs.items()}


def best_provider(task: str, keys: dict[str, str]) -> tuple[str, str] | None:
    """
    Return (provider_name, api_key) for the best available provider for a task.
    Returns None if no key is set.
    """
    order = _ROUTING.get(task, ["openai", "gemini", "claude"])
    mapping = {
        "openai": keys.get("api_key_openai", ""),
        "gemini": keys.get("api_key_gemini", ""),
        "claude": keys.get("api_key_claude", ""),
    }
    for provider in order:
        key = mapping.get(provider, "")
        if key:
            return provider, key
    return None


def call_ai(task: str, prompt: str, mixin, system: str = "") -> str:
    """
    Call the best available AI for the given task.
    Returns the response text, or an error/fallback string.
    """
    keys = get_api_keys(mixin)
    result = best_provider(task, keys)
    if result is None:
        return _no_key_message(task)

    provider, key = result
    try:
        if provider == "openai":
            return _call_openai(key, prompt, system)
        elif provider == "gemini":
            return _call_gemini(key, prompt, system)
        elif provider == "claude":
            return _call_claude(key, prompt, system)
    except Exception as e:
        return f"⚠ API error ({provider}): {e}"
    return _no_key_message(task)


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _call_openai(key: str, prompt: str, system: str = "") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = json.dumps({
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── Google Gemini ─────────────────────────────────────────────────────────────

def _call_gemini(key: str, prompt: str, system: str = "") -> str:
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    body = json.dumps({
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7},
    }).encode()

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={key}"
    )
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ── Anthropic Claude ──────────────────────────────────────────────────────────

def _call_claude(key: str, prompt: str, system: str = "") -> str:
    body_dict: dict = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body_dict["system"] = system

    body = json.dumps(body_dict).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"].strip()


# ── Fallback message ──────────────────────────────────────────────────────────

def _no_key_message(task: str) -> str:
    recommendations = {
        "code":     "Claude 3.5 Sonnet (best for code) or OpenAI GPT-4o",
        "generate": "Google Gemini 1.5 Pro (best for long generation) or OpenAI GPT-4o",
        "grammar":  "OpenAI GPT-4o (best for prose) or Claude",
        "ask":      "OpenAI GPT-4o or Google Gemini 1.5 Flash",
    }
    rec = recommendations.get(task, "OpenAI, Gemini, or Claude")
    return (
        f"No AI API key found.\n\n"
        f"Recommended for this feature: {rec}\n\n"
        f"Go to  My API Key  in the sidebar to add your key.\n"
        f"It only takes 30 seconds — keys are stored locally and never shared."
    )
