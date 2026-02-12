"""
telegram_bot.py — Telegram bot interface for the AI Assistant.

Handles all Telegram communication:
- User authentication (only your user ID is allowed)
- Text message processing through LLM → Router pipeline
- Slash commands (/start, /help, /status, /screenshot)
- File sending (documents, photos)
- Confirmation flow for dangerous actions
"""

import os
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from security import verify_user, sanitize_input, RateLimiter
from logger import setup_logger, log_command
from llm_engine import query_ollama, check_ollama_status
from command_router import (
    route_command,
    handle_confirmation,
    has_pending_confirmation,
)
from system_control import get_system_info
from screenshot import take_screenshot

# ── Setup ─────────────────────────────────────────────────────────────
logger = setup_logger("telegram", config.LOG_FILE, config.LOG_LEVEL)
rate_limiter = RateLimiter(max_requests=config.RATE_LIMIT_RPM, window_seconds=60)


# ── Auth Decorator ────────────────────────────────────────────────────
def auth_required(func):
    """Decorator to verify the user is authorized before handling."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not verify_user(user_id, config.TELEGRAM_ALLOWED_USER_ID):
            logger.warning(f"Unauthorized access attempt from user_id={user_id}")
            await update.message.reply_text(
                "🚫 Access Denied. You are not authorized to use this bot."
            )
            return
        return await func(update, context)
    return wrapper


# ── Command Handlers ──────────────────────────────────────────────────

@auth_required
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "🤖 **AI Assistant is online!**\n\n"
        "I have full access to your PC. Just tell me what you need.\n\n"
        "Type /help to see what I can do.\n"
        "Type /status to check system status.",
        parse_mode="Markdown",
    )
    log_command(logger, update.effective_user.id, "/start", "start", "Welcome sent")


@auth_required
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "🤖 **AI Assistant — Help**\n\n"
        "Just tell me what you want in natural language! Examples:\n\n"
        "📂 *Files:*\n"
        '  • "Show me files on my Desktop"\n'
        '  • "Read the file C:\\\\notes.txt"\n'
        '  • "Send me the report from Documents"\n'
        '  • "Search for .py files"\n\n'
        "🖥️ *System:*\n"
        '  • "Open Chrome"\n'
        '  • "Run ipconfig"\n'
        '  • "Show system info"\n'
        '  • "Take a screenshot"\n\n'
        "📧 *Messaging:*\n"
        '  • "Send an email to john@email.com"\n\n'
        "📋 *Commands:*\n"
        "  /start — Start the bot\n"
        "  /help — This help menu\n"
        "  /status — System status\n"
        "  /screenshot — Quick screenshot"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
    log_command(logger, update.effective_user.id, "/help", "help", "Help sent")


@auth_required
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    await update.message.reply_text("⏳ Gathering system info...")

    # Check Ollama
    ollama_ok = await check_ollama_status(config.OLLAMA_BASE_URL)
    ollama_status = "✅ Online" if ollama_ok else "❌ Offline"

    # System info
    sys_info = await get_system_info()

    status_text = (
        f"🤖 **Assistant Status**\n\n"
        f"🧠 Ollama: {ollama_status}\n"
        f"📡 Model: {config.OLLAMA_MODEL}\n\n"
        f"{sys_info}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")
    log_command(logger, update.effective_user.id, "/status", "status", "Status sent")


@auth_required
async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /screenshot command — quick screenshot without LLM."""
    await update.message.reply_text("📸 Capturing screen...")

    screenshot_path = await take_screenshot(config.SCREENSHOT_DIR)

    if screenshot_path.startswith("ERROR:"):
        await update.message.reply_text(f"❌ Screenshot failed: {screenshot_path[6:]}")
        log_command(
            logger, update.effective_user.id,
            "/screenshot", "screenshot", error=screenshot_path,
        )
    else:
        with open(screenshot_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption="📸 Screenshot")
        log_command(
            logger, update.effective_user.id,
            "/screenshot", "screenshot", "Screenshot sent",
        )


# ── Text Message Handler ─────────────────────────────────────────────

@auth_required
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle all text messages.

    Pipeline: Auth → Rate Limit → Confirmation Check → LLM → Router → Reply
    """
    user_id = update.effective_user.id
    raw_text = update.message.text
    text = sanitize_input(raw_text)

    if not text:
        await update.message.reply_text("❓ Empty message received.")
        return

    # ── Rate Limiting ─────────────────────────────────────────────
    if not rate_limiter.is_allowed(user_id):
        remaining = rate_limiter.remaining(user_id)
        await update.message.reply_text(
            f"⏱️ Rate limited. Please wait a moment.\n"
            f"Remaining requests: {remaining}"
        )
        logger.warning(f"Rate limited user {user_id}")
        return

    # ── Check for pending confirmation ────────────────────────────
    if has_pending_confirmation(user_id):
        result = await handle_confirmation(user_id, text, config.SCREENSHOT_DIR)
        if result:
            await _send_result(update, result)
            log_command(logger, user_id, text, "confirmation", result.get("text", "")[:100])
            return

    # ── Send to LLM ───────────────────────────────────────────────
    await update.message.reply_text("🧠 Thinking...")

    parsed = await query_ollama(
        text,
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_MODEL,
    )

    logger.info(
        f"LLM response: action={parsed.get('action')} "
        f"confidence={parsed.get('confidence')} "
        f"intent={parsed.get('intent')}"
    )

    # ── Route to action handler ───────────────────────────────────
    result = await route_command(parsed, user_id, config.SCREENSHOT_DIR)

    # ── Send result ───────────────────────────────────────────────
    await _send_result(update, result)

    log_command(
        logger, user_id, text,
        parsed.get("action", "unknown"),
        result.get("text", "")[:100],
    )


async def _send_result(update: Update, result: dict):
    """
    Send the command result back to the user.

    Handles text messages, file sending, and photo sending.
    """
    text = result.get("text", "")
    file_path = result.get("file_path")

    # Send text response
    if text:
        # Split long messages (Telegram limit is 4096 chars)
        while len(text) > 4000:
            chunk = text[:4000]
            # Try markdown first, fall back to plain text
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)
            text = text[4000:]

        if text:
            try:
                await update.message.reply_text(text, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(text)

    # Send file if present
    if file_path and os.path.isfile(file_path):
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
            with open(file_path, "rb") as f:
                await update.message.reply_photo(
                    photo=f,
                    caption=f"📎 {os.path.basename(file_path)}",
                )
        else:
            with open(file_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📎 {os.path.basename(file_path)}",
                )


# ── Bot Setup ─────────────────────────────────────────────────────────

def create_bot() -> Application:
    """
    Create and configure the Telegram bot application.

    Returns:
        Configured telegram Application instance.
    """
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))

    # Register text message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Telegram bot configured successfully")
    return app


async def set_bot_commands(app: Application):
    """Set the bot's command menu in Telegram."""
    commands = [
        BotCommand("start", "Start the assistant"),
        BotCommand("help", "Show help"),
        BotCommand("status", "System status"),
        BotCommand("screenshot", "Take a screenshot"),
    ]
    await app.bot.set_my_commands(commands)
