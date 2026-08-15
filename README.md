# 🤖 Telegram Bill Payment Gateway & Hunger Noter Bot

> **A persistent, multi-agent AI bill parsing and expense recording bot for Telegram.**  
> Powered by **Flow-Nexus-Swarm** (Hierarchical Swarm Architecture) and **Ruflo** (Goal-Oriented Planning & Self-Optimization Framework), with automated **OCR Computer Vision** and **SQLite Shared Memory (`AgentDB`)**.

---

## 🌟 Key Features

- **⚡ Standby & Hunger Detection:** Constantly listens in the Telegram gateway. Aggressively extracts bill items, subtotals, grand totals, and currencies from text and receipt images.
- **📸 Auto-OCR Photo Ingestion:** Downloads receipt photos (GrabFood, FoodPanda, Shopee, Lazada, 7-Eleven, Starbucks, supermarkets, utilities) and performs automatic text recognition using `Tesseract`.
- **⏳ Real-Time Animated Progress Bar:** Provides live, stage-by-stage Telegram message editing progress (`10% -> 20% -> 50% -> 80% -> 100%`) while processing receipts.
- **💬 Conversational Intelligence:** Answers questions and chats with members rather than just standing still.
- **✅ Itemized Confirmation & Replay:** Replies immediately upon storing a bill with a checkmark, formatted amount, timestamp, user, source, and OCR snippets.
- **🧠 Ruflo Self-Optimization:** Continuously analyzes agent performance and updates behavior hints.
- **🗄️ SQLite Shared Memory (`AgentDB`):** Thread-safe persistent database for bills, audit logs, and agent states.
- **🔄 Late-Added Catch-Up Scanner (`hunger_catchup.py`):** Ingests historical chat exports or connects via user session (MTProto) to capture past receipts missed before the bot joined.

---

## 🏗️ Architecture & Multi-Agent Swarm

```mermaid
graph TD
    User["Telegram User / Group"] -->|Text or Photo Bill| Gateway["Telegram Gateway (bill_noter/bot.py)"]
    Gateway -->|Interactive Routing| Skill["BillGatewaySkill (Hunger Mode)"]
    
    Skill -->|Goal Planning| Ruflo["Ruflo Goal Engine & Task Planner"]
    Skill -->|Orchestration| Swarm["SwarmOrchestrator (flow-nexus-swarm)"]
    
    subgraph Multi-Agent Swarm Pipeline
        C["1. BillCollectorAgent (Metadata & Ingestion)"] --> P["2. BillParserAgent (Price & Currency Parser + OCR)"]
        P --> S["3. BillStorageAgent (SQLite Ingestion)"]
        S --> R["4. BillResponderAgent (Formatting & Replay)"]
    end
    
    Swarm --> C
    
    C & P & S & R <--> DB[("SQLite Shared Memory: AgentDB (data/swarm_memory.db)")]
    DB --> Opt["Ruflo Self-Optimizer"]
    
    R -->|Progress: 100%| Reply["Telegram Chat Replay with Checkmark & Details"]
```

---

## 📂 Project Structure

```text
telegram_payment_bot/
├── bill_noter_bot.py                 # Primary entry point
├── SOUL.md                          # Immutable soul manifest & bot directive
├── README.md                        # Full documentation
├── hunger_catchup.py                # Retroactive history & chat export ingester
├── .env.example                     # Env template (copy to .env, never commit)
├── data/                            # Runtime: SQLite AgentDB + OCR photos (gitignored)
│
├── bill_noter/                      # Core Noter package
│   ├── __init__.py
│   ├── bot.py                       # Telegram bot handlers & event loop
│   ├── notes_store.py               # Legacy storage
│   └── price_parser.py              # Multi-currency price extraction engine
│
├── skills/                          # Modular AI skills directory
│   ├── __init__.py
│   ├── SKILL.md                     # Skill system documentation
│   ├── registry.py                  # Dynamic skill discovery
│   ├── bill_gateway_skill.py        # Gateway integration (Chat, OCR, Progress bar)
│   │
│   ├── flow_nexus_swarm/            # Multi-agent swarm implementation
│   │   ├── __init__.py
│   │   ├── SKILL.md
│   │   ├── agents.py                # Collector, Parser, Storage, Responder agents
│   │   ├── orchestrator.py          # Hierarchical pipeline coordinator
│   │   ├── shared_memory.py         # SQLite AgentDB backend
│   │   └── topology.py              # Swarm topologies (Hierarchical, Mesh, Ring)
│   │
│   └── ruflo/                       # Goal-oriented framework
│       ├── __init__.py
│       ├── SKILL.md
│       ├── goal_engine.py           # Goal tracking & lifecycle
│       ├── task_planner.py          # Task decomposition
│       └── self_optimizer.py        # Log-based agent learning
│
└── gateway/                         # Gateway scanner & OCR utilities
    ├── bill_detector.py
    ├── checkpoint.py
    ├── gateway.py
    ├── ocr.py                       # Tesseract OCR engine wrapper
    └── sandbox.py                   # Offline testing sandbox
```

---

## 🚀 Quick Start

### 1. Requirements
- Python 3.10+
- `tesseract-ocr` installed (`sudo apt install tesseract-ocr`)
- Dependencies:
  ```bash
  pip install python-telegram-bot pytesseract Pillow
  ```

### 2. Configuration (`.env`)
Copy `.env.example` to `.env` and fill in your own values — **never commit real tokens**:
```env
# Get your token from @BotFather (REQUIRED)
BILL_NOTER_TOKEN=123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Optional: JSON path for legacy notes (defaults to notes.json)
BILL_NOTER_STORE=notes.json
# Optional: default chat to monitor (used by catch-up scripts)
DEFAULT_CHAT_ID=your_chat_id
```

### 3. Run the Bot
```bash
python bill_noter_bot.py
```

---

## 💬 Bot Commands & Interactions

| Command | Description |
|---|---|
| `/start`, `/help` | Show command guide and features. |
| `/recent` | List the last 10 notes stored in **Swarm Memory**. |
| `/total` | Show the total sum and count of noted expenses. |
| `/swarm` | View live multi-agent performance metrics & topology. |
| `/optimize` | Trigger the **Ruflo Self-Optimizer** to tune agent parameters. |
| `/status` | Check running state and active skill plugins. |

### In-Chat Behavior:
1. **Send Text Bill:** `GrabFood dinner 35.50 USD` or `FoodPanda lunch 18.00 EUR`
2. **Send Receipt Photo:** Any receipt or bill image. The bot updates in real time with an animated progress bar and extracts total amounts and store names.
3. **Conversational Questions:** Ask *"how many bills recorded?"* or *"look into this"* for immediate status assistance.

---

## 🔄 Recovering Past Receipts (`hunger_catchup.py`)

If you added the bot late to a group with existing bill history:

1. **Export Chat History in Telegram Desktop** (`JSON` format with Photos).
2. Run the catch-up ingester:
   ```bash
   python hunger_catchup.py path/to/result.json
   ```
3. All historical bills and receipts will be parsed and loaded into `data/swarm_memory.db`!

---

## 📜 License
MIT License.
