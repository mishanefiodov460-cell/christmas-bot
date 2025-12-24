import json
import os
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ====== ENV ======
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # https://xxxx.koyeb.app
PORT = int(os.getenv("PORT", 8000))

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

USERS_FILE = "users.json"

logging.basicConfig(level=logging.INFO)

# ====== DATA ======
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()
waiting_for_recipient = {}

# ====== UI ======
def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["🎁 Надіслати побажання"],
            ["📋 Список користувачів"],
            ["👨‍💻 Від розробника (Мишка)"],
        ],
        resize_keyboard=True,
    )

# ====== HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in users:
        await update.message.reply_text(
            f"🎄 Ти вже зареєстрований як:\n{users[user_id]}\n\nОбери дію:",
            reply_markup=main_menu(),
        )
    else:
        await update.message.reply_text(
            "🎄 Привіт!\nНапиши своє ім’я та прізвище.",
            reply_markup=main_menu(),
        )
        context.user_data["waiting_for_name"] = True

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip() if update.message.text else None

    # MENU
    if text == "👨‍💻 Від розробника (Мишка)":
        await developer_info(update, context)
        return
    if text == "🎁 Надіслати побажання":
        await send_start(update, context)
        return
    if text == "📋 Список користувачів":
        await list_users(update, context)
        return

    # REGISTRATION
    if context.user_data.get("waiting_for_name"):
        if not text or len(text.split()) < 2:
            await update.message.reply_text("❌ Введи ім’я та прізвище.")
            return

        users[user_id] = text
        save_users(users)
        context.user_data["waiting_for_name"] = False

        await update.message.reply_text(
            f"✅ Запам’ятав!\nТи зареєстрований як:\n{text}",
            reply_markup=main_menu(),
        )
        return

    # ANONYMOUS MESSAGE
    if context.user_data.get("writing_message"):
        recipient_id = waiting_for_recipient.pop(user_id)
        context.user_data["writing_message"] = False

        await context.bot.copy_message(
            chat_id=recipient_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )

        await update.message.reply_text(
            "✅ Побажання надіслано анонімно 🎁",
            reply_markup=main_menu(),
        )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("🎄 Поки що нікого немає.")
        return

    text = "🎁 Зареєстровані користувачі:\n\n"
    for name in users.values():
        text += f"• {name}\n"

    await update.message.reply_text(text)

async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("🎄 Поки що немає користувачів.")
        return

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"choose:{uid}")]
        for uid, name in users.items()
    ]

    await update.message.reply_text(
        "🎁 Кому хочеш надіслати анонімне побажання?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, recipient_id = query.data.split(":")
    waiting_for_recipient[str(query.from_user.id)] = recipient_id
    context.user_data["writing_message"] = True

    await query.message.reply_text("✉️ Напиши анонімне побажання:")

async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👨‍💻 Бот від Миші 🎄\n\nАнонімні побажання для всіх 💙"
    )

# ====== WEBHOOK ======
async def on_startup(app: Application):
    await app.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Webhook set: {WEBHOOK_URL}")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(choose_recipient, pattern="^choose:"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_any_message))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
    )

if __name__ == "__main__":
    main()
