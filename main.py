# =========================
# IMPORTS
# =========================
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from datetime import datetime, time

# =========================
# BOT TOKEN
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")


# =========================
# GOOGLE SHEETS SETUP
# =========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "creds.json", scope
)
client = gspread.authorize(creds)

sheet = client.open_by_key(
    "1Z_Sbc9xI4H5uLQljIJ-P5NSpsAsxkgyxPAjzPCbigW8"
).sheet1

# =========================
# BATCH TIMINGS
# =========================
BATCHES = {
    "Morning": {"start": time(9, 0), "end": time(10, 0)},
    "Evening Batch 1": {"start": time(17, 0), "end": time(20, 0)},
    "Evening Batch 2": {"start": time(20, 0), "end": time(23, 0)},
}

# =========================
# CLIENTS PER BATCH
# =========================
BATCH_CLIENTS = {
    "Morning": ["Rahul", "Neha", "Amit"],
    "Evening Batch 1": ["Rahul", "Sana", "Vikram"],
    "Evening Batch 2": ["Neha", "Amit", "Rohit"],
}

# =========================
# RUNTIME STATE
# =========================
current_batch = None
absentees = set()
selected_absentees = set()  # for multi-select UI

# =========================
# HELPERS
# =========================
def normalize(name: str) -> str:
    return name.strip().lower()

def get_active_batch():
    now = datetime.now().time()
    for name, info in BATCHES.items():
        if info["start"] <= now <= info["end"]:
            return name, info["start"], info["end"]
    return None, None, None

def save_attendance(batch_name, absentees, clients):
    date = datetime.now().strftime("%Y-%m-%d")
    time_now = datetime.now().strftime("%H:%M")

    for name in clients:
        status = "Absent" if normalize(name) in absentees else "Present"
        sheet.append_row([
            date,
            batch_name,
            name,
            status,
            time_now
        ])

# =========================
# INLINE KEYBOARD BUILDER
# =========================
def build_toggle_keyboard(batch_name):
    clients = BATCH_CLIENTS.get(batch_name, [])
    keyboard = []
    row = []

    for name in clients:
        key = normalize(name)
        mark = "✅" if key in selected_absentees else "❌"

        row.append(
            InlineKeyboardButton(
                text=f"{name} {mark}",
                callback_data=f"TOGGLE:{name}"
            )
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("✅ CONFIRM", callback_data="CONFIRM")
    ])

    return InlineKeyboardMarkup(keyboard)

# =========================
# MESSAGE HANDLER (TEXT)
# =========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_batch, absentees, selected_absentees

    if update.message is None or update.message.text is None:
        return

    text = update.message.text.strip()
    text_lower = text.lower()

    batch_name, start, end = get_active_batch()

    if batch_name is None:
        await update.message.reply_text(
            "⏰ No active batch right now.\n"
            "Attendance can only be marked during batch time."
        )
        return

    # New batch → show interactive page
    if current_batch != batch_name:
        current_batch = batch_name
        absentees = set()
        selected_absentees = set()

        await update.message.reply_text(
            f"🕒 {batch_name} started ({start.strftime('%H:%M')}–{end.strftime('%H:%M')})\n"
            "Everyone is PRESENT by default.\n"
            "Tap names to mark ABSENT:",
            reply_markup=build_toggle_keyboard(batch_name)
        )
        return

    # Text fallback: "done"
    if text_lower == "done":
        clients = BATCH_CLIENTS.get(batch_name, [])
        save_attendance(batch_name, absentees, clients)

        await update.message.reply_text(
            f"📊 Attendance saved for {batch_name}\n"
            f"Present: {len(clients) - len(absentees)}\n"
            f"Absent: {len(absentees)}"
        )

        current_batch = None
        absentees = set()
        selected_absentees = set()
        return

# =========================
# CALLBACK HANDLER (BUTTONS)
# =========================
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_batch, absentees, selected_absentees

    query = update.callback_query
    await query.answer()

    if not current_batch:
        await query.edit_message_text("⏰ No active batch.")
        return

    data = query.data

    if data.startswith("TOGGLE:"):
        name = data.split(":", 1)[1]
        key = normalize(name)

        if key in selected_absentees:
            selected_absentees.remove(key)
        else:
            selected_absentees.add(key)

        await query.edit_message_reply_markup(
            reply_markup=build_toggle_keyboard(current_batch)
        )
        return

    if data == "CONFIRM":
        absentees = set(selected_absentees)

        clients = BATCH_CLIENTS.get(current_batch, [])
        save_attendance(current_batch, absentees, clients)

        await query.edit_message_text(
            f"📊 Attendance saved for {current_batch}\n"
            f"Present: {len(clients) - len(absentees)}\n"
            f"Absent: {len(absentees)}"
        )

        current_batch = None
        absentees = set()
        selected_absentees = set()
        return

# =========================
# MAIN
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    print("🤖 Bot is running (multi-select + Google Sheets)...")
    app.run_polling()

if __name__ == "__main__":
    main()

