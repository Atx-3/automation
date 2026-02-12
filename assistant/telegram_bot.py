"""
telegram_bot.py — Telegram bot interface for Clawbot.

Handles all Telegram communication:
- User authentication (only allowed user IDs)
- Text message processing through LLM → Router pipeline
- Photo/image processing for vision model analysis
- Slash commands (/start, /help, /status, /screenshot, /stats, /clear)
- File sending (documents, photos)
- Confirmation flow for dangerous actions
"""

import os
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from security import verify_user, sanitize_input, RateLimiter, extract_command_with_token
from logger import setup_logger, log_command, log_security_event
from llm_engine import query_ollama, check_ollama_status
from command_router import (
    route_command,
    handle_confirmation,
    has_pending_confirmation,
)
from system_control import get_system_info
from screenshot import take_screenshot
import database

# ── Setup ─────────────────────────────────────────────────────────────
logger = setup_logger("telegram", config.LOG_FILE, config.LOG_LEVEL)
rate_limiter = RateLimiter(max_requests=config.RATE_LIMIT_RPM, window_seconds=60)


# ── Auth Decorator ────────────────────────────────────────────────────
def auth_required(func):
    """Decorator to verify the user is authorized before handling."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not verify_user(user_id, config.TELEGRAM_ALLOWED_USER_IDS):
            log_security_event(logger, "AUTH_FAIL", user_id, "Unauthorized access attempt")
            await update.message.reply_text(
                "🚫 Access Denied. You are not authorized to use Clawbot."
            )
            return
        return await func(update, context)
    return wrapper


# ── Command Handlers ──────────────────────────────────────────────────

@auth_required
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_name = update.effective_user.first_name or "Boss"
    await update.message.reply_text(
        f"🤖 **Clawbot is online, {user_name}!**\n\n"
        f"I operate with strict permissions and whitelists only.\n\n"
        f"🧠 AI Model: `{config.OLLAMA_MODEL}`\n"
        f"📡 Send me text or photos — I can understand both!\n\n"
        f"Type /help to see what I can do.",
        parse_mode="Markdown",
    )
    log_command(logger, update.effective_user.id, "/start", "start", "Welcome sent")


@auth_required
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "🤖 **Clawbot — Your Personal AI Assistant**\n\n"
        "Just tell me what you want in natural language! Examples:\n\n"
        "📂 *Files:*\n"
        '  • "Show me files on my Desktop"\n'
        '  • "Read the file C:\\\\notes.txt"\n'
        '  • "Send me the report from Documents"\n'
        "\n"
        "🖥️ *System:*\n"
        '  • "Open Chrome"\n'
        '  • "Take a screenshot"\n'
        "\n"
        "📜 *Scripts:*\n"
        '  • "Run the backup script"\n\n'
        "📸 *Vision:*\n"
        "  • Send a photo and I'll analyze it!\n\n"
        "📋 *Commands:*\n"
        "  /start — Start Clawbot\n"
        "  /help — This help menu\n"
        "  /status — System status\n"
        "  /screenshot — Quick screenshot\n\n"
        "🔐 **Command Token:**\n"
        "  Use one of these formats:\n"
        "  • `<token> your command`\n"
        "  • `token:<token> your command`\n"
        "  For /status or /screenshot, send `/status token:<token>`"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")
    log_command(logger, update.effective_user.id, "/help", "help", "Help sent")


@auth_required
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    if config.TELEGRAM_COMMAND_TOKEN:
        raw = update.message.text or ""
        tail = raw.replace("/status", "", 1).strip()
        if tail == config.TELEGRAM_COMMAND_TOKEN:
            ok = True
        else:
            ok, _ = extract_command_with_token(tail, config.TELEGRAM_COMMAND_TOKEN)
        if not ok:
            await update.message.reply_text("🔐 Invalid or missing command token.")
            return
    await update.message.reply_text("⏳ Gathering system info...")

    # Check Ollama
    ollama_ok = await check_ollama_status(config.OLLAMA_BASE_URL)
    ollama_status = "✅ Online" if ollama_ok else "❌ Offline"

    # System info
    sys_info = await get_system_info()

    status_text = (
        f"🤖 **Clawbot Status**\n\n"
        f"🧠 Ollama: {ollama_status}\n"
        f"📡 Model: `{config.OLLAMA_MODEL}`\n\n"
        f"{sys_info}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")
    log_command(logger, update.effective_user.id, "/status", "status", "Status sent")


@auth_required
async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /screenshot command — quick screenshot without LLM."""
    if config.TELEGRAM_COMMAND_TOKEN:
        raw = update.message.text or ""
        tail = raw.replace("/screenshot", "", 1).strip()
        if tail == config.TELEGRAM_COMMAND_TOKEN:
            ok = True
        else:
            ok, _ = extract_command_with_token(tail, config.TELEGRAM_COMMAND_TOKEN)
        if not ok:
            await update.message.reply_text("🔐 Invalid or missing command token.")
            return
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
            await update.message.reply_photo(photo=photo, caption="📸 Screenshot — Clawbot")
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
        log_security_event(logger, "RATE_LIMIT", user_id, f"remaining={remaining}")
        await update.message.reply_text(
            f"⏱️ Rate limited. Please wait a moment.\n"
            f"Remaining requests: {remaining}"
        )
        return

    # ── Check for pending confirmation ────────────────────────────
    if has_pending_confirmation(user_id):
        result = await handle_confirmation(user_id, text, config.SCREENSHOT_DIR)
        if result:
            await _send_result(update, result)
            log_command(logger, user_id, text, "confirmation", result.get("text", "")[:100])
            return

    ok, cleaned = extract_command_with_token(text, config.TELEGRAM_COMMAND_TOKEN)
    if not ok:
        await update.message.reply_text("🔐 Invalid or missing command token.")
        return
    if not cleaned:
        await update.message.reply_text("❓ Empty message received.")
        return

    # ── Save user message to database ─────────────────────────────
    database.save_message(user_id, "user", cleaned)

    # ── Send to LLM ───────────────────────────────────────────────
    await update.message.reply_text("🧠 Thinking...")

    parsed = await query_ollama(
        cleaned,
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_MODEL,
        timeout=config.OLLAMA_TIMEOUT,
        user_id=user_id,
    )

    logger.info(
        f"LLM response: action={parsed.get('action')} "
        f"confidence={parsed.get('confidence')} "
        f"intent={parsed.get('intent')}"
    )

    # ── Route to action handler ───────────────────────────────────
    result = await route_command(parsed, user_id, config.SCREENSHOT_DIR)

    # ── Save assistant response to database ───────────────────────
    database.save_message(user_id, "assistant", result.get("text", "")[:5000], parsed.get("action"))

    # ── Send result ───────────────────────────────────────────────
    await _send_result(update, result)

    log_command(
        logger, user_id, cleaned,
        parsed.get("action", "unknown"),
        result.get("text", "")[:100],
    )


# ── Photo Message Handler ────────────────────────────────────────────

@auth_required
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle photo messages — send to vision model for analysis.

    The user can send a photo with an optional caption (question about the photo).
    """
    user_id = update.effective_user.id

    # Rate limiting
    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text("⏱️ Rate limited. Please wait.")
        return

    await update.message.reply_text("👁️ Analyzing image...")

    # Get the largest photo version
    photo = update.message.photo[-1]
    photo_file = await context.bot.get_file(photo.file_id)

    # Download the photo
    image_bytes = await photo_file.download_as_bytearray()

    # Use caption as the question, or default
    caption = update.message.caption or "What do you see in this image? Describe it in detail."
    caption = sanitize_input(caption)
    ok, cleaned = extract_command_with_token(caption, config.TELEGRAM_COMMAND_TOKEN)
    if not ok:
        await update.message.reply_text("🔐 Invalid or missing command token.")
        return
    caption = cleaned or "Describe the image clearly."

    # Save user message
    database.save_message(user_id, "user", f"[Photo] {caption}")

    # Send to vision model
    parsed = await query_ollama(
        caption,
        base_url=config.OLLAMA_BASE_URL,
        model=config.OLLAMA_MODEL,
        timeout=config.OLLAMA_TIMEOUT,
        user_id=user_id,
        image_data=bytes(image_bytes),
    )

    # For image analysis, the response is usually a chat action
    response_text = parsed.get("parameters", {}).get("response", "")
    if not response_text:
        response_text = parsed.get("intent", "I couldn't analyze the image.")

    # Save to database
    database.save_message(user_id, "assistant", response_text[:5000], "vision")

    # Send response
    try:
        await update.message.reply_text(response_text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(response_text)

    log_command(logger, user_id, f"[photo] {caption[:50]}", "vision", response_text[:100])


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

    # Register photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Register text message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Clawbot Telegram bot configured successfully")
    return app


async def set_bot_commands(app: Application):
    """Set the bot's command menu in Telegram."""
    commands = [
        BotCommand("start", "Start Clawbot"),
        BotCommand("help", "Show help"),
        BotCommand("status", "System status"),
        BotCommand("screenshot", "Take a screenshot"),
    ]
    await app.bot.set_my_commands(commands)
