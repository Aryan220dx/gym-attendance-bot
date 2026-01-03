from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from datetime import datetime, time

# =========================
# BOT TOKEN (KEEP PRIVATE)
# =========================
BOT_TOKEN = "8592699078:AAFuRwRXee8LxvVQjEG2Vai69gWYe2IJn7I"

# =========================
# BATCH TIMINGS
# =========================
BATCHES = {
    "Morning": {"start": time(6, 0), "end": time(7, 0)},
    "Evening Batch 1": {"start": time(17, 0), "end": time(18, 0)},
    "Evening Batch 2": {"start": time(21, 0), "end": time(22, 0)}
}

# =========================
# CLIENTS PER BATCH (EDIT THIS)
# =========================
BATCH_CLIENTS = {
    "Morning": ["Rahul", "Neha", "Amit"],
    "Evening Batch 1": ["Rahul", "Sana", "Vikram"],
    "Evening Batch 2": ["Neha", "Amit", "Rohit"]
}

# =========================
# RUNTIME STATE
# =========================
current_batch = None
absentees = set()

# =========================
# HELPERS
# =========================
def get_active_batch():
    now = datetime.now().time()
    for name, info in BATCHES.items():
        if info["start"] <= now <= info["end"]:
            return name, info["start"], info["end"]
    return None, None, None

def normalize(name: str) -> str:
    return name.strip().lower()

# =========================
# MESSAGE HANDLER
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_batch, absentees

    # Safety check: ignore non-text updates
    if update.message is None or update.message.text is None:
        return


    text = update.message.text.strip()
    text_lower = text.lower()

    batch_name, start, end = get_active_batch()

    # No active batch
    if batch_name is None:
        await update.message.reply_text(
            "⏰ No active batch right now.\n"
            "Attendance can only be marked during batch time."
        )
        return

    # New batch detected → reset state
    if current_batch != batch_name:
        current_batch = batch_name
        absentees = set()
        await update.message.reply_text(
            f"🤖 {batch_name} started ({start.strftime('%H:%M')}–{end.strftime('%H:%M')})\n"
            "Everyone is PRESENT by default.\n"
            "Send absentees like: @ Rahul AP\n"
            "Type 'done' when finished."
        )

    # Finalize attendance
    if text_lower == "done":
        total = len(BATCH_CLIENTS.get(batch_name, []))
        absent_count = len(absentees)
        present_count = max(total - absent_count, 0)

        await update.message.reply_text(
            f"📊 Attendance saved for {batch_name}\n"
            f"Present: {present_count}\n"
            f"Absent: {absent_count}"
        )

        # Reset for next session
        current_batch = None
        absentees = set()
        return

    # Handle absent marking: "@ Name AP"
    if text_lower.startswith("@") and "ap" in text_lower:
        # Extract name between '@' and 'ap'
        try:
            name_part = text[1:text_lower.index("ap")].strip()
        except ValueError:
            await update.message.reply_text("⚠️ Format error. Use: @ Name AP")
            return

        # Validate client
        clients = BATCH_CLIENTS.get(batch_name, [])
        normalized_clients = {normalize(c): c for c in clients}
        key = normalize(name_part)

        if key not in normalized_clients:
            await update.message.reply_text(f"⚠️ '{name_part}' not found in this batch.")
            return

        if key in absentees:
            await update.message.reply_text(f"⚠️ {normalized_clients[key]} already marked absent.")
            return

        absentees.add(key)
        await update.message.reply_text(f"✅ {normalized_clients[key]} marked absent.")
        return

    # Ignore other messages quietly
    await update.message.reply_text("ℹ️ Send absentees like '@ Name AP' or type 'done'.")

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running (absent-first logic)...")
    app.run_polling()

if __name__ == "__main__":
    main()
