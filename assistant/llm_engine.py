"""
llm_engine.py — Ollama LLM integration for the AI Assistant.

Sends user messages to the local Ollama API and parses structured
JSON responses containing intent, action, parameters, and confidence.
"""

import json
import httpx
from typing import Optional


# System prompt that instructs the LLM to return structured JSON
SYSTEM_PROMPT = """You are a personal AI assistant with full access to the user's Windows PC.
You interpret natural language commands and return a structured JSON response.

You MUST respond with ONLY a valid JSON object in this exact format:
{
    "intent": "brief description of what the user wants",
    "action": "one of the allowed actions listed below",
    "parameters": { ... action-specific parameters ... },
    "confidence": 0.0 to 1.0
}

ALLOWED ACTIONS and their parameters:

1. "open_app" — Open an application
   parameters: {"app_name": "name of the app like notepad, chrome, explorer, etc."}

2. "run_command" — Execute a system command
   parameters: {"command": "the shell command to run"}

3. "read_file" — Read a file's contents
   parameters: {"file_path": "full path to the file"}

4. "write_file" — Write content to a file
   parameters: {"file_path": "full path", "content": "text content to write"}

5. "delete_file" — Delete a file (requires confirmation)
   parameters: {"file_path": "full path to delete"}

6. "list_files" — List files in a directory
   parameters: {"directory": "full directory path"}

7. "send_file" — Send a file to the user via Telegram
   parameters: {"file_path": "full path to the file"}

8. "screenshot" — Take a screenshot of the screen
   parameters: {}

9. "system_info" — Get system information (CPU, RAM, disk, etc.)
   parameters: {}

10. "send_message" — Send a message on behalf of the user
    parameters: {"platform": "email", "to": "recipient", "subject": "subject", "body": "message body"}

11. "kill_process" — Kill a running process
    parameters: {"process_name": "name of the process"}

12. "search_files" — Search for files by name
    parameters: {"query": "search term", "directory": "where to search (optional)"}

13. "status" — Report assistant status
    parameters: {}

14. "help" — Show help information
    parameters: {}

15. "chat" — General conversation (no PC action needed)
    parameters: {"response": "your conversational reply"}

RULES:
- Always respond with ONLY the JSON object, no extra text.
- If the user wants general conversation, use the "chat" action.
- If you're unsure what the user wants, set confidence below 0.5 and use "chat" action.
- For dangerous operations (delete, format), still classify them — the system will ask for confirmation.
"""


async def query_ollama(
    user_message: str,
    base_url: str = "http://localhost:11434",
    model: str = "llama3.2",
    timeout: float = 120.0,
) -> dict:
    """
    Send a user message to Ollama and parse the structured JSON response.

    Args:
        user_message: The natural language command from the user.
        base_url: Ollama API base URL.
        model: The Ollama model to use.
        timeout: Request timeout in seconds.

    Returns:
        Parsed dict with keys: intent, action, parameters, confidence.
        On failure, returns a fallback dict with action="chat".
    """
    payload = {
        "model": model,
        "prompt": user_message,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1,  # Low temperature for consistent structured output
        },
    }

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
        valid_actions = {
            "open_app", "run_command", "read_file", "write_file",
            "delete_file", "list_files", "send_file", "screenshot",
            "system_info", "send_message", "kill_process", "search_files",
            "status", "help", "chat",
        }
        if result["action"] not in valid_actions:
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
