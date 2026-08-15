# 🎨 Emoji & Emote Language

The bot speaks a small, consistent emoji vocabulary so every reply,
status line, and doc reads the same way. **Never invent new emotes** —
reuse the vocabulary below. This keeps messages scannable and sleek.

## Core vocabulary

| Emote | Meaning              | Used for                                        |
|-------|----------------------|-------------------------------------------------|
| ✅    | Confirmation         | bill saved, task done, successful response      |
| 🤖    | The bot itself       | introductions, identity, `/status`              |
| 📋    | Item / label         | the bill item or store label                    |
| 💰    | Amount               | prices, totals, money values                    |
| 📅    | Date                 | bill date                                       |
| 🕐    | Time                 | bill timestamp                                  |
| 👤    | User / author        | who paid                                         |
| 🏷️    | Source               | Grab / FoodPanda / Shopee / etc.                |
| 🖼️    | Photo / OCR          | receipt image captured, OCR processed           |
| 🔍    | Scanning / search    | OCR scan, "looking into this"                   |
| ⚡    | Active / hungry mode | standby, live pipeline, listening               |
| 💾    | Persisting           | saving to SQLite AgentDB                        |
| ✨    | Finalizing           | completing a stage                              |
| 📊    | Stats                | counts, totals, swarm metrics                   |
| 🧮    | Sum                  | `/total` command output                         |
| 📒    | Recent list          | `/recent` command output                        |
| 📭    | Empty state          | no notes yet                                    |
| 🟢🟡🔴 | Agent health         | optimal / monitor / needs_attention             |
| 🔧    | Optimization         | `/optimize` report                              |
| 📸    | Photo input          | "send a receipt photo" prompt                   |
| ⏳    | Progress / loading   | download in progress                            |
| 🚨    | Error                | failures, warnings                              |
| ❓    | Question             | clarifying questions                            |

## Reply templates

### Bill confirmed (text or photo)
```
✅ *Bill Noted & Saved!*
📋 *Item:* <label>
💰 *Amount:* <amount> <currency>
📅 *Date:* <date>
🕐 *Time:* <time>
👤 *Payer:* <author>
🏷️ *Source:* <grab|foodpanda|...>      (only if detected)
🖼️ *Receipt:* Photo Captured & OCR Processed   (photos only)
🔍 *OCR Snippet:* <preview>                     (photos only)
```

### Progress stages (edits in place, same message)
```
⏳ [■□□□□□□□□□] 10% — [Gateway] Downloading receipt image...
⚡ [■■□□□□□□□□] 20% — [Swarm: BillCollector] Ingesting data & OCR scanning...
🔍 [■■■■■□□□□□] 50% — [Swarm: BillParser] Extracting prices, items & currency...
💾 [■■■■■■■■□□] 80% — [Swarm: BillStorage] Saving to SQLite AgentDB...
✨ [■■■■■■■■■■] 100% — [Swarm: BillResponder] Finalizing confirmation...
```

### Agent health (from `/swarm` and `/optimize`)
- 🟢 ≥ 90% — optimal
- 🟡 ≥ 70% — monitor
- 🔴 < 70% — needs attention

## Rules
1. **One emote per line**, at the start, followed by a space and a bold
   label (`✅ *Noted:*`).
2. Emotes carry *meaning*, never decoration — no emoji spam.
3. Docs and SKILL.md units may use section emojis (🧭 🧠 🔬 🗄️ 🏗️ 📂)
   at headings only.
4. Error messages: keep the bot's emote (`🤖`) out — use `🚨` or plain
   text so failures stand out.
