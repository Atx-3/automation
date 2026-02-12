"""
llm_engine.py — Ollama LLM integration for Clawbot.

Sends user messages to the local Ollama API and parses structured
JSON responses containing intent, action, parameters, and confidence.

Supports multimodal input (text + images) with vision models
like llama3.2-vision or llava.
"""

import json
import base64
import httpx
from typing import Optional

import database


# ── System Prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Clawbot — a secure personal AI assistant running locally on the user's Windows PC.
You interpret natural language commands and return a structured JSON response.

You MUST respond with ONLY a valid JSON object in this exact format:
{
    "intent": "brief description of what the user wants",
    "action": "one of the allowed actions listed below",
    "parameters": { ... action-specific parameters ... },
    "confidence": 0.0 to 1.0
}

ALLOWED ACTIONS and their parameters:

1. "open_app" — Open a whitelisted application
   parameters: {"app_name": "name of the app like notepad, chrome, explorer, etc."}

2. "read_file" — Read a file's contents from allowed directories
   parameters: {"file_path": "full path to the file"}

3. "list_files" — List files in an allowed directory
   parameters: {"directory": "full directory path"}

4. "send_file" — Send a file to the user via Telegram from allowed directories
   parameters: {"file_path": "full path to the file"}

5. "screenshot" — Take a screenshot of the screen
   parameters: {}

6. "run_script" — Run a predefined safe script
   parameters: {"script_name": "name of the script"}

7. "status" — Report assistant status
   parameters: {}

8. "help" — Show help information
   parameters: {}

9. "chat" — General conversation (no PC action needed)
   parameters: {"response": "your conversational reply"}

RULES:
- Always respond with ONLY the JSON object, no extra text.
- If the user wants general conversation, use the "chat" action.
- If you're unsure what the user wants, set confidence below 0.5 and use "chat" action.
- If the user requests anything outside the allowed actions, use "chat" with low confidence.
- Be helpful, precise, and security-focused.
"""


# All known valid actions
VALID_ACTIONS = {
    "open_app", "read_file", "list_files", "send_file",
    "screenshot", "run_script", "status", "help", "chat",
}


async def query_ollama(
    user_message: str,
    base_url: str = "http://localhost:11434",
    model: str = "llama3.2-vision",
    timeout: float = 120.0,
    user_id: int = 0,
    image_data: Optional[bytes] = None,
) -> dict:
    """
    Send a user message to Ollama and parse the structured JSON response.

    Supports multimodal input — if image_data is provided, it will be
    sent alongside the text for vision models.

    Args:
        user_message: The natural language command from the user.
        base_url: Ollama API base URL.
        model: The Ollama model to use.
        timeout: Request timeout in seconds.
        user_id: Telegram user ID (for conversation context).
        image_data: Optional raw image bytes for vision analysis.

    Returns:
        Parsed dict with keys: intent, action, parameters, confidence.
        On failure, returns a fallback dict with action="chat".
    """
    # Build context from recent conversation history
    context_prompt = ""
    if user_id:
        recent = database.get_recent_messages(user_id, limit=10)
        if recent:
            context_lines = []
            for msg in recent[-6:]:  # Last 6 messages for context
                role = "User" if msg["role"] == "user" else "Clawbot"
                context_lines.append(f"{role}: {msg['message'][:300]}")
            context_prompt = (
                "Recent conversation context:\n"
                + "\n".join(context_lines)
                + "\n\nCurrent request:\n"
            )

    full_prompt = context_prompt + user_message

    payload = {
        "model": model,
        "prompt": full_prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,  # Low temperature for consistent structured output
        },
    }

    # Add image data for vision models
    if image_data:
        payload["images"] = [base64.b64encode(image_data).decode("utf-8")]

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        # Extract the response text from Ollama
        raw_response = data.get("response", "")
        parsed = _parse_llm_response(raw_response)
        return parsed

    except httpx.ConnectError:
        return _error_response(
            "Cannot connect to Ollama. Is it running? Start it with: ollama serve"
        )
    except httpx.TimeoutException:
        return _error_response("Ollama request timed out. The model may be loading.")
    except Exception as e:
        return _error_response(f"LLM error: {str(e)}")


def _parse_llm_response(raw: str) -> dict:
    """
    Parse the raw LLM response string into a structured dict.

    Attempts JSON parsing; falls back to a chat response on failure.
    """
    try:
        parsed = json.loads(raw.strip())

        # Validate required fields
        result = {
            "intent": parsed.get("intent", "unknown"),
            "action": parsed.get("action", "chat"),
            "parameters": parsed.get("parameters", {}),
            "confidence": float(parsed.get("confidence", 0.5)),
        }

        # Validate action is a known type
        if result["action"] not in VALID_ACTIONS:
            result["action"] = "chat"
            result["parameters"] = {
                "response": f"I understood your intent ({result['intent']}) "
                            f"but couldn't map it to a valid action."
            }

        return result

    except (json.JSONDecodeError, ValueError, TypeError):
        return {
            "intent": "conversation",
            "action": "chat",
            "parameters": {"response": raw.strip() if raw.strip() else "I couldn't understand that."},
            "confidence": 0.3,
        }


def _error_response(message: str) -> dict:
    """Create a standardized error response dict."""
    return {
        "intent": "error",
        "action": "chat",
        "parameters": {"response": f"⚠️ {message}"},
        "confidence": 0.0,
    }


async def check_ollama_status(base_url: str = "http://localhost:11434") -> bool:
    """
    Check if Ollama is running and responsive.

    Returns:
        True if Ollama is reachable.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def get_available_models(base_url: str = "http://localhost:11434") -> list[str]:
    """
    Get list of locally available Ollama models.

    Returns:
        List of model names.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []
