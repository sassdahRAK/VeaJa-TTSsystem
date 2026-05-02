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

Fallback behaviour:
  If the preferred provider returns a rate-limit (429) or server error (5xx),
  the caller automatically tries the next available provider in the routing order.
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.error


# ── Task → preferred provider order ──────────────────────────────────────────
_ROUTING: dict[str, list[str]] = {
    "code":      ["claude", "openai", "gemini"],
    "generate":  ["gemini", "openai", "claude"],
    "grammar":   ["openai", "claude", "gemini"],
    "ask":       ["gemini", "openai", "claude"],
    "translate": ["gemini", "openai", "claude"],
    "summary":   ["gemini", "openai", "claude"],
}

# HTTP status codes that should trigger a fallback to the next provider
_FALLBACK_CODES = {429, 500, 502, 503, 504}


def get_api_keys(mixin) -> dict[str, str]:
    """
    Pull live key values from the mixin's _api_key_inputs dict.
    Also merges in the cached profile so keys are available even when
    the API keys page hasn't been unlocked yet in this session.
    """
    result: dict[str, str] = {}

    # 1. Read from the profile cache (always available, set at startup)
    profile_cache = getattr(mixin, "_last_profile_cache", {})
    for k, v in profile_cache.items():
        if isinstance(v, str) and v.strip():
            result[k] = v.strip()

    # 2. Override with live field values (user may have typed a new key)
    if hasattr(mixin, "_api_key_inputs"):
        for k, f in mixin._api_key_inputs.items():
            v = f.text().strip()
            if v:
                result[k] = v

    return result


# Maps keywords in a custom card name → standard provider key
_CUSTOM_NAME_MAP = {
    "gemini":    "api_key_gemini",
    "google":    "api_key_gemini",
    "aistudio":  "api_key_gemini",
    "openai":    "api_key_openai",
    "gpt":       "api_key_openai",
    "claude":    "api_key_claude",
    "anthropic": "api_key_claude",
}


def _key_map(keys: dict[str, str]) -> dict[str, str]:
    result = {
        "openai": keys.get("api_key_openai", ""),
        "gemini": keys.get("api_key_gemini", ""),
        "claude": keys.get("api_key_claude", ""),
    }
    # Scan custom_* keys — if the card name matches a known provider,
    # use its value to fill the corresponding slot (only if not already set).
    for k, v in keys.items():
        if not v:
            continue
        k_lower = k.lower()
        # Match both custom_* field keys and direct profile keys
        if "custom_" in k_lower or k_lower.startswith("api_key_"):
            for keyword, std_key in _CUSTOM_NAME_MAP.items():
                if keyword in k_lower:
                    provider = std_key.replace("api_key_", "")
                    if not result.get(provider):
                        result[provider] = v
                    break

    # Also parse custom_apis JSON blob if present — keys stored there
    # by name (e.g. {"name": "Google Gemini", "key": "AIza..."})
    custom_apis_raw = keys.get("custom_apis", "")
    if custom_apis_raw and isinstance(custom_apis_raw, str):
        try:
            import json as _json
            customs = _json.loads(custom_apis_raw)
            for entry in customs:
                name = entry.get("name", "").lower()
                key_val = entry.get("key", "").strip()
                if not key_val:
                    continue
                for keyword, std_key in _CUSTOM_NAME_MAP.items():
                    if keyword in name:
                        provider = std_key.replace("api_key_", "")
                        if not result.get(provider):
                            result[provider] = key_val
                        break
        except Exception:
            pass

    return result


def best_provider(task: str, keys: dict[str, str]) -> tuple[str, str] | None:
    """
    Return (provider_name, api_key) for the best available provider for a task.
    Returns None if no key is set.
    """
    order = _ROUTING.get(task, ["openai", "gemini", "claude"])
    mapping = _key_map(keys)
    for provider in order:
        key = mapping.get(provider, "")
        if key:
            return provider, key
    return None


def call_ai(task: str, prompt: str, mixin, system: str = "") -> str:
    """
    Call the best available AI for the given task.

    Automatically falls back to the next provider in the routing order when
    a rate-limit (429) or server error (5xx) is received.

    Returns the response text, or a user-friendly error/fallback string.
    """
    import sys

    keys   = get_api_keys(mixin)
    order  = _ROUTING.get(task, ["openai", "gemini", "claude"])
    mapping = _key_map(keys)

    # ── DEBUG: print what keys were found and candidate order ─────────────
    found = {k: ("✓ set" if v else "✗ empty") for k, v in mapping.items()}
    print(f"[AI] task={task}  keys={found}", file=sys.stderr)

    # Build the list of (provider, key) pairs that have a key set,
    # preserving the preferred order for this task.
    candidates = [
        (provider, mapping[provider])
        for provider in order
        if mapping.get(provider)
    ]

    print(f"[AI] candidates={[p for p,_ in candidates]}", file=sys.stderr)

    if not candidates:
        return _no_key_message(task)

    last_error = ""
    for provider, key in candidates:
        print(f"[AI] trying {provider}…", file=sys.stderr)
        # Retry up to 2 times on rate-limit before falling to next provider
        for attempt in range(3):
            try:
                if provider == "openai":
                    result = _call_openai(key, prompt, system)
                elif provider == "gemini":
                    result = _call_gemini(key, prompt, system)
                elif provider == "claude":
                    result = _call_claude(key, prompt, system)
                else:
                    break
                print(f"[AI] success via {provider}", file=sys.stderr)
                return result
            except urllib.error.HTTPError as e:
                # Read error body once — used for both logging and credit check
                try:
                    err_body_raw = e.read().decode(errors="replace")
                except Exception:
                    err_body_raw = ""
                print(f"[AI] {provider} HTTP {e.code}: {err_body_raw[:300]}", file=sys.stderr)

                if e.code == 429:
                    last_error = f"{provider} HTTP 429 (rate limit)"
                    if attempt < 2:
                        time.sleep(5 * (attempt + 1))
                        continue
                    break  # exhausted retries — try next provider

                if e.code in _FALLBACK_CODES:
                    last_error = f"{provider} HTTP {e.code} (server error)"
                    break  # try next provider

                if e.code == 400:
                    # Check if it's a billing/credit issue
                    try:
                        err_json = json.loads(err_body_raw)
                        err_msg  = err_json.get("error", {}).get("message", "")
                    except Exception:
                        err_msg = err_body_raw
                    if any(w in err_msg.lower() for w in ("credit", "balance", "billing", "payment")):
                        last_error = f"{provider}: no credits — add billing at provider dashboard"
                    else:
                        last_error = f"{provider} HTTP 400 — trying next provider"
                    break  # try next provider

                # 401/403 — bad key, stop immediately with clear message
                return f"⚠ API error ({provider}): HTTP {e.code} — check your API key in My API Key"

            except urllib.error.URLError as e:
                print(f"[AI] {provider} URLError: {e.reason}", file=sys.stderr)
                last_error = f"{provider} network error: {e.reason}"
                break
            except Exception as e:
                print(f"[AI] {provider} exception: {e}", file=sys.stderr)
                last_error = f"{provider}: {e}"
                break

    # All providers and retries exhausted
    if "429" in last_error:
        return (
            "⚠ Rate limit reached on all available providers.\n\n"
            "Your OpenAI free tier allows only ~3 requests/minute.\n\n"
            "Options:\n"
            "  • Wait 60 seconds and try again\n"
            "  • Add a Gemini or Claude key in My API Key — they have\n"
            "    much more generous free tiers\n"
            "  • Upgrade your OpenAI plan at platform.openai.com"
        )
    if "no credits" in last_error:
        return (
            "⚠ API provider has no credits.\n\n"
            f"{last_error}\n\n"
            "Add a free Gemini key in My API Key to keep using the app for free."
        )
    return f"⚠ All providers failed. Last error: {last_error}"


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
        f"gemini-2.0-flash:generateContent?key={key}"
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
        "code":      "Claude 3.5 Sonnet (best for code) or OpenAI GPT-4o",
        "generate":  "Google Gemini 1.5 Pro (best for long generation) or OpenAI GPT-4o",
        "grammar":   "OpenAI GPT-4o (best for prose) or Claude",
        "ask":       "OpenAI GPT-4o or Google Gemini 1.5 Flash",
        "translate": "OpenAI GPT-4o or Google Gemini 1.5 Flash",
        "summary":   "OpenAI GPT-4o or Google Gemini 1.5 Flash",
    }
    rec = recommendations.get(task, "OpenAI, Gemini, or Claude")
    return (
        f"No AI API key found.\n\n"
        f"Recommended for this feature: {rec}\n\n"
        f"Go to  My API Key  in the sidebar to add your key.\n"
        f"It only takes 30 seconds — keys are stored locally and never shared."
    )
