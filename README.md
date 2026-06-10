# SnapVault

> A personal Discord bot for capturing and retrieving your own screenshots and notes using AI — just forward something, then ask about it later.

**This bot is privately hosted by me.** You don't need to run anything — just use the invite link below to add it to your server and start saving.

---

## Add the Bot to Your Server

**[→ Click here to add SnapVault](https://discord.com/oauth2/authorize?client_id=1511051090911563849&permissions=309237763136&integration_type=0&scope=bot)**

Once added, the bot is live as long as I have `bot.py` running on my machine.

---

##  How to Use It

| Action | How |
|---|---|
| Save a screenshot | Send or forward any image to the bot or a channel it's in |
| Save a text note | Send any plain-text message |
| Ask a question | Ask anything — e.g. *"what bikes am I looking at?"* |
| Set a reminder | `!remind 2025-06-10T09:00 check bike price` |
| Clear your history | `!clear` |

---

##  Features

- **Multimodal ingestion** — Save plain text notes or screenshot content in one place, natively in Discord.
- **Hybrid OCR extraction** — Parses screenshot text via local Tesseract OCR, with automatic fallback to a Vision model (`api-gemma-4-26b`) for sparse or low-text images.
- **Semantic search** — Indexes and vector-searches your saves using ChromaDB and UCSD's `api-tgpt-embeddings` model.
- **Contextual RAG chat** — Maintains short-term conversation context in Discord Threads using a 120B parameter model (`api-gpt-oss-120b`) to answer follow-up questions accurately.
- **Reminders** — Schedule and trigger notification alerts asynchronously, persisted in local SQLite.

---
## Demo Video
[Discord Bot Demo](https://youtu.be/GbfL2x-EJMg)
[Discord Bot New Demo](https://youtu.be/9RZWZfwJgHY)

##  System Architecture

```
Discord Message
       │
       ▼
  Ingestion Layer
  ├─ Text Notes
  └─ Image Uploads
          │
          ▼
OCR / Vision Extraction
          │
          ▼
    SQLite Storage
          │
          ▼
    Embedding Model
          │
          ▼
      ChromaDB
          │
          ▼
     Retrieval (RAG)
          │
          ▼
        LLM
          │
          ▼
Discord Response
```

---

##  Current Limitations

- **Local storage only** — Data lives in `snapvault.db` and `./chroma_db` on the host machine. Cloud deployments (e.g. Railway) need mounted storage volumes to persist data.
- **Single-user focused** — Multi-user memory isolation and database partitioning are in progress; currently optimized for a single demo profile.
- **Availability depends on my machine** — The bot is only online when I'm running `bot.py` locally.

---

---

##  Developer Setup 

> Everything below is for my own reference. Users don't need to do any of this.

### Project Structure

```
snapvault/
├── bot.py              # Discord client + all event/command routing
├── ingestion.py        # Save flow: image or text → Note → DB + embed
├── extractor_ocr.py    # Tesseract OCR, sparse detection
├── extractor_vision.py # Vision model fallback
├── embedder.py         # LlamaIndex → ChromaDB upsert
├── query_engine.py     # LlamaIndex retrieval → ranked Note IDs
├── conversation.py     # Thread history buffer + LLM answer
├── reminders.py        # Background loop for due reminders
├── db.py               # SQLite: notes + reminders tables
├── models.py           # Note dataclass
├── config.py           # All constants + env var loading
├── requirements.txt
└── .env.example
```

---

### Step 1 — Create the Discord Bot (one-time)

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application** → name it `SnapVault`
2. Left sidebar → **Bot** → **Add Bot**
3. Under **Privileged Gateway Intents**, enable **Message Content Intent** 
4. Copy the **Token** → paste into `.env` as `DISCORD_TOKEN`
5. Left sidebar → **OAuth2 → URL Generator**
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Read Message History`, `Create Public Threads`, `Attach Files`, `Add Reactions`
6. Open the generated URL → add the bot to your server

Invite link (with permissions already set):
```
https://discord.com/oauth2/authorize?client_id=1511051090911563849&permissions=309237763136&integration_type=0&scope=bot
```

---

### Step 2 — Install Tesseract (system dependency)

**Mac:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr
```

**Windows:** Download from [UB-Mannheim installer](https://github.com/UB-Mannheim/tesseract/wiki) and add `tesseract.exe` to your system PATH.

---

### Step 3 — Python environment

```bash
cd snapvault
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 4 — Configure environment variables

```env
DISCORD_TOKEN="your_discord_bot_token"
UCSD_API_KEY="your_triton_api_key"
OPENAI_API_KEY="your_triton_api_key"
```

---

### Step 5 — Test without Discord

Run the CLI test harness to validate ingestion, OCR extraction, and RAG retrieval in the terminal without connecting to the Discord Gateway:

```bash
python test_cli.py
```

---

### Step 6 — Run the bot

```bash
python bot.py
```

The bot is online when you see:
```
[SnapVault] logged in as SnapVault#XXXX
```
Next, open discord server and talk to Otter.
---

### Future steps- Deploying to Railway 

1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Add environment variables: `DISCORD_TOKEN`, `UCSD_API_KEY`, `OPENAI_API_KEY`
4. Railway auto-detects Python and runs `python bot.py`

> ⚠️ Railway's free tier sleeps after inactivity. Use a paid plan for always-on uptime. Also note that Railway uses an ephemeral filesystem — you'll need to configure a mounted volume for `snapvault.db` and `chroma_db/` to persist data across restarts.



## feedback
- a classification model for input state
- guardrail for hello xxx
- let user update

To dos: 
1. neutral input mode- add slash commands(/save, /ask); also use a small LLM to classify non slash commands - bot.py (done)
2. sensitive info guarrail- flag possible sensitive info, ask user to confirm; - conversation.py
if sensitive but still want to be saved, then make sure during rag, direct retrieval, no LLM part (done, if >=12 gibberish, would pop up the sensitive notification)
3. note management- if detects repeated notes, let LLM decide, then prompt to user to confirm if update; also let user delete -db.py, ingestion.py, embedder.py (done)
4. allow the update/delete message button on discord work in sync with the storage system (done)
4. Google Calendar (to do)
5. Live Deployment (to do)

What I'd add next, in priority order:
Rate limiting per user — right now one user hammering saves would burn your API quota for everyone. A simple in-memory counter per user_id per minute is enough.
better/smarter memory management
multiple channels, different functionalities