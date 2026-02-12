# 🤖 Clawbot — Secure Local AI Assistant via Telegram (Ollama)

A secure, permissioned personal AI agent that runs locally on your Windows PC and is controlled via Telegram, powered by Ollama.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Brain** | Ollama LLM interprets natural language commands |
| 📱 **Telegram Control** | Send commands from your phone |
| 📂 **File Access** | Read, list, send files from allowed directories only |
| 🖥️ **App Control** | Open apps from a strict whitelist |
| 📸 **Screenshots** | Capture your screen remotely |
| 📜 **Safe Scripts** | Run predefined scripts only |
| 🔐 **User Lock** | Only allowed Telegram IDs can use the bot |
| 🧪 **Token Gate** | Command token required before execution |
| 📊 **System Info** | CPU, RAM, disk, battery, network status |
| 📝 **Logging** | Every action is logged with timestamps |

---

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Ollama

1. Download from **https://ollama.com/download** (Windows)
2. Run the installer
3. Open a terminal and pull a model:
   ```bash
   ollama pull llama3.2
   ```
4. Ollama starts automatically. Verify with:
   ```bash
   ollama list
   ```

### Step 2: Create Your Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **Bot Token** (looks like `7123456789:AAF...`)
4. Get your **User ID**: message **@userinfobot** and copy the ID number

### Step 3: Configure the Assistant

```bash
cd assistant
copy .env.example .env
```

Edit `.env` with your values:
```env
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_ALLOWED_USER_IDS=123456789
TELEGRAM_COMMAND_TOKEN=your_strong_command_token
API_TOKEN=your_local_api_token
ALLOWED_FILE_DIRS=C:\Users\YourUser\Desktop;C:\Users\YourUser\Documents
OLLAMA_MODEL=llama3.2
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run

```bash
python main.py
```

✅ Now open Telegram, find your bot, and send `/start`!

---

## 💬 Usage Examples

| You say... | Bot does... |
|------------|-------------|
| "Open Chrome" | Launches Chrome |
| "Show files on Desktop" | Lists Desktop contents |
| "<token> read C:\notes.txt" | Shows file contents (allowed dirs only) |
| "token:<token> send report.pdf" | Sends file via Telegram |
| "<token> take a screenshot" | Captures & sends screenshot |
| "<token> open chrome" | Opens Chrome from whitelist |
| "<token> run the backup script" | Runs a predefined safe script |
| "<token> status" | Shows CPU, RAM, disk info |

### Slash Commands

| Command | Action |
|---------|--------|
| `/start` | Initialize the bot |
| `/help` | Show all capabilities |
| `/status` | System & Ollama status |
| `/screenshot` | Quick screenshot |

---

## 📁 Project Structure

```
assistant/
├── main.py              # Entry point — FastAPI + Telegram launcher
├── config.py            # Environment config loader
├── llm_engine.py        # Ollama LLM integration
├── command_router.py    # Intent → action dispatcher
├── telegram_bot.py      # Telegram bot handlers
├── telegram_interface.py# Telegram interface wrapper
├── file_manager.py      # File read/list/send (whitelisted dirs)
├── system_control.py    # System info utilities
├── screenshot.py        # Screen capture
├── security.py          # User auth & rate limiting
├── logger.py            # Structured rotating logs
├── requirements.txt     # Python dependencies
├── .env.example         # Config template
└── README.md            # This file
```

---

## 🔐 Security Notes

- **User locked**: Only allowed Telegram IDs can use the bot
- **Token gated**: Commands require a command token
- **Strict whitelist**: Only allowed apps, scripts, and directories are accessible
- **No raw shell**: No arbitrary shell commands are executed
- **Local only**: FastAPI binds to `127.0.0.1`
- **Ollama local**: Your AI runs on your PC — no data sent to cloud
- **Logged**: Every command and result is logged to `clawbot.log`

### ⚠️ Important

This bot is permissioned and whitelisted. Keep your:
- `.env` file **private** (never commit it)
- Telegram Bot Token **secret**
- PC **behind a firewall**

## 🛡️ Security Hardening Recommendations

- Use a long random token for `TELEGRAM_COMMAND_TOKEN` and rotate it periodically
- Keep `ALLOWED_FILE_DIRS` minimal and avoid sensitive folders
- Remove unused apps from `WHITELISTED_APPS`
- Store logs on an encrypted drive if possible
- Keep Windows and Python dependencies updated

---

## 🔮 Future Roadmap

- [ ] **Voice messages** — speech-to-text via Whisper
- [ ] **Scheduled tasks** — cron-style job scheduling
- [ ] **Clipboard access** — read/write clipboard
- [ ] **Browser automation** — Playwright integration
- [ ] **Multi-user support** — role-based access for family
- [ ] **Plugin system** — easy-to-add custom actions
- [ ] **Chat memory** — conversation context across sessions
- [ ] **File upload** — receive files from Telegram to PC
- [ ] **Webhook mode** — for deployment behind reverse proxy

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Ollama" | Run `ollama serve` in a terminal |
| Bot doesn't respond | Check `TELEGRAM_BOT_TOKEN` in `.env` |
| "Access Denied" | Your Telegram user ID doesn't match `.env` |
| "Invalid token" | Verify `TELEGRAM_COMMAND_TOKEN` and command format |
| Screenshot fails | Ensure no remote desktop lock |
| Email fails | Use Gmail App Password, not regular password |

---

**Clawbot — 100% Free, 100% Local, 100% Yours**
