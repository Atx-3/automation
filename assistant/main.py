"""
main.py — Entry point for the AI Assistant.

Starts the FastAPI server and Telegram bot together.
The FastAPI server provides a health endpoint and optional local API.
The Telegram bot runs as the primary user interface.
"""

import asyncio
import threading
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import config
from logger import setup_logger
from llm_engine import check_ollama_status, query_ollama
from command_router import route_command
from telegram_bot import create_bot, set_bot_commands

# ── Logger ────────────────────────────────────────────────────────────
logger = setup_logger("main", config.LOG_FILE, config.LOG_LEVEL)


# ── FastAPI Lifespan ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for FastAPI."""
    logger.info("=" * 60)
    logger.info("  🤖 AI Assistant starting up...")
    logger.info("=" * 60)

    # Check Ollama status
    ollama_ok = await check_ollama_status(config.OLLAMA_BASE_URL)
    if ollama_ok:
        logger.info(f"✅ Ollama is running at {config.OLLAMA_BASE_URL}")
        logger.info(f"   Model: {config.OLLAMA_MODEL}")
    else:
        logger.warning(
            f"⚠️  Ollama is NOT running at {config.OLLAMA_BASE_URL}\n"
            f"   Start it with: ollama serve\n"
            f"   Then pull a model: ollama pull {config.OLLAMA_MODEL}"
        )

    # Start Telegram bot in background
    logger.info("🚀 Starting Telegram bot...")
    bot_app = create_bot()

    # Run the bot in a separate thread
    bot_thread = threading.Thread(
        target=_run_telegram_bot,
        args=(bot_app,),
        daemon=True,
    )
    bot_thread.start()
    logger.info("✅ Telegram bot started in background thread")

    logger.info(f"🌐 FastAPI server running at http://{config.API_HOST}:{config.API_PORT}")
    logger.info("=" * 60)

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down AI Assistant...")


def _run_telegram_bot(bot_app):
    """Run the Telegram bot in a new event loop (for threading)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(set_bot_commands(bot_app))
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    bot_app.run_polling(drop_pending_updates=True)


# ── FastAPI App ───────────────────────────────────────────────────────
app = FastAPI(
    title="AI Assistant API",
    description="Local AI assistant with full PC access via Telegram",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Health Check Endpoint ─────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check — returns system status."""
    ollama_ok = await check_ollama_status(config.OLLAMA_BASE_URL)
    return {
        "status": "healthy",
        "ollama": "online" if ollama_ok else "offline",
        "model": config.OLLAMA_MODEL,
    }


# ── Local Command Endpoint ───────────────────────────────────────────
class CommandRequest(BaseModel):
    """Request body for the /command endpoint."""
    message: str
    user_id: int = 0


@app.post("/command")
async def execute_command(request: CommandRequest):
    """
    Execute a command via local API (for testing or local integrations).

    This endpoint is only accessible on localhost.
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Send to LLM
    parsed = await query_ollama(
        request.message,
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_MODEL,
    )

    # Route to action
    result = await route_command(parsed, request.user_id, config.SCREENSHOT_DIR)

    return {
        "llm_response": parsed,
        "result": result.get("text", ""),
        "file_path": result.get("file_path"),
    }


# ── Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print()
    print("  ╔═══════════════════════════════════════╗")
    print("  ║    🤖 AI Assistant — Starting...      ║")
    print("  ║    Telegram + Ollama + FastAPI         ║")
    print("  ╚═══════════════════════════════════════╝")
    print()

    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
        log_level="info",
    )
