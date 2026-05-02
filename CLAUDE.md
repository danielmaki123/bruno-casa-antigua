# CLAUDE.md — BrunoBot

Project-specific guidance for the BrunoBot Telegram bot (restaurant automation).

---

## 🤖 Project Overview

**BrunoBot v2** is a Telegram bot for "Casa Antigua" restaurant, replacing Hermes Agent with a custom Python implementation.

- **Language:** Python 3.11
- **Framework:** `python-telegram-bot` v20+ (async)
- **LLM:** Kimi (Moonshot) / OpenAI-compatible endpoint
- **Database:** PostgreSQL (persistent memory) + Google Sheets (operational data)
- **Deployment:** Docker + EasyPanel
- **Status:** Under development (architecture ready in `BRUNOBOT_V2_ARCHITECTURE.md`)

---

## 🚀 Quick Start

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: TELEGRAM_TOKEN, DATABASE_URL, GOOGLE_SHEETS_ID, LLM_API_KEY

# Run locally (for testing)
python bot/main.py
```

### Deploy
```bash
# Docker build (for EasyPanel)
docker build -t brunobot .
docker-compose up -d
```

---

## 📂 Directory Structure

```
BrunoBot/
├── .env                      # Secrets (NEVER commit)
├── .env.example              # Template
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # EasyPanel orchestration
├── Dockerfile                # Container image
│
├── bot/
│   ├── main.py              # Entry point (telegram polling)
│   ├── config.py            # Settings loader
│   ├── handlers/            # Message handlers (commands, messages)
│   └── skills/              # Features as Python modules
│       ├── memory.py        # PostgreSQL queries
│       ├── llm.py           # LLM API calls (Kimi/OpenAI)
│       └── sheets.py        # Google Sheets integration
│
├── data/                     # Data exports (git-ignored)
├── database/                 # DB migrations, schema
│
├── docs/
│   ├── BRUNOBOT_V2_ARCHITECTURE.md
│   └── sheets_structure.md
```

---

## 🎯 Common Tasks

### Add a new skill (feature)
1. Create file: `bot/skills/my_feature.py`
2. Add handler to `bot/handlers/`
3. Register in `bot/main.py`
4. Test: `python bot/main.py`

### Query the database
- PostgreSQL connection via `DATABASE_URL`
- Use parameterized queries (prevent SQL injection)
- Check `bot/skills/memory.py` for existing patterns

### Integrate a Google Sheet
- Authenticate via `credentials.json` + `google-auth`
- Use `bot/skills/sheets.py` (already implemented)
- Sheet ID in `.env` as `GOOGLE_SHEETS_ID`

### Switch LLM provider
- Edit `bot/skills/llm.py`
- Kimi and OpenAI use the same SDK — just change the endpoint

---

## 🔗 Skills This Project Uses

| Skill | When | Notes |
|-------|------|-------|
| `/codex:review` | Before merging to main | Security + logic audit |
| `/debug` | Bot crashes or unexpected behavior | Trace logs in `bot/main.py` |
| `/plan` | Adding major features | Document in `BRUNOBOT_V2_ARCHITECTURE.md` |
| `/n8n` | Connecting to restaurant workflows | See `.hermes/` for existing automations |

---

## ⚙️ Development Checklist

- [ ] `.env` configured (never commit)
- [ ] PostgreSQL connection tested (`echo $DATABASE_URL`)
- [ ] Google Sheets authenticated (run `python -c "from bot.skills.sheets import test_auth; test_auth()"`)
- [ ] Docker builds locally (`docker build -t brunobot .`)
- [ ] Telegram webhook/polling works

---

## 🐛 Debugging

**Bot not responding?**
- Check `TELEGRAM_TOKEN` in `.env`
- Verify network (firewall, VPN)
- Review logs: `docker logs brunobot`

**Database connection fails?**
- Test `DATABASE_URL` connectivity
- Verify PostgreSQL is running on EasyPanel
- Check for IP whitelist restrictions

**LLM errors?**
- Verify API key for Kimi/OpenAI in `.env`
- Test: `python -c "from bot.skills.llm import test_connection; test_connection()"`

---

## 📋 References

- Architecture: `BRUNOBOT_V2_ARCHITECTURE.md` (read before major changes)
- Google Sheets mapping: `docs/sheets_structure.md`
- Telegram API: https://docs.python-telegram-bot.org
- Kimi API: Use OpenAI endpoint (SDK-compatible)
