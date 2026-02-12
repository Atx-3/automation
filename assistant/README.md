# 🤖 AI Assistant — Full PC Control via Telegram

A personal AI agent that gives you **full control of your Windows PC** from your phone via **Telegram**, powered by **Ollama** (100% free, 100% local).

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Brain** | Ollama LLM interprets natural language commands |
| 📱 **Telegram Control** | Send commands from your phone |
| 📂 **File Access** | Read, write, delete, list, search, send any file |
| 🖥️ **System Control** | Open apps, run commands, kill processes |
| 📸 **Screenshots** | Capture your screen remotely |
| 📧 **Email** | Send emails on your behalf |
| 🔐 **User Lock** | Only YOUR Telegram ID can use the bot |
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
TELEGRAM_ALLOWED_USER_ID=123456789
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
| "Read C:\notes.txt" | Shows file contents |
| "Send me the report.pdf" | Sends file via Telegram |
| "Take a screenshot" | Captures & sends screenshot |
| "Run ipconfig" | Runs command, shows output |
| "What's my system status?" | Shows CPU, RAM, disk info |
| "Kill notepad" | Terminates notepad process |
| "Search for .py files in projects" | Finds matching files |
| "Send email to john@mail.com about the meeting" | Sends email |

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
├── file_manager.py      # File read/write/delete/list/search
├── system_control.py    # App launcher, shell, processes
├── screenshot.py        # Screen capture
├── messaging.py         # Email automation
├── security.py          # User auth & rate limiting
├── logger.py            # Structured rotating logs
├── requirements.txt     # Python dependencies
├── .env.example         # Config template
└── README.md            # This file
```

---

## 🔐 Security Notes

- **User locked**: Only the Telegram ID in `.env` can use the bot
- **Rate limited**: 30 requests/minute (configurable)
- **Confirmation required**: Dangerous actions (delete, kill) ask you to confirm
- **Local only**: FastAPI binds to `127.0.0.1` — not exposed to the internet
- **Ollama local**: Your AI runs on your PC — no data sent to cloud
- **Logged**: Every command and result is logged to `assistant.log`

### ⚠️ Important

This bot has **full access** to your PC. Keep your:
- `.env` file **private** (never commit it)
- Telegram Bot Token **secret**
- PC **behind a firewall**

---

## 📧 Email Setup (Optional)

To enable email sending, add to `.env`:

```env
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

For Gmail: create an **App Password** at https://myaccount.google.com/apppasswords

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
| Screenshot fails | Ensure no remote desktop lock |
| Email fails | Use Gmail App Password, not regular password |

---

**Built with ❤️ — 100% Free, 100% Local, 100% Yours**
