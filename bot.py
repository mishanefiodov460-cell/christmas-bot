from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
USERS_FILE = "users.json"


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in users:
        await update.message.reply_text(
            f"🎄 Ти вже зареєстрований як:\n{users[user_id]}\n\nОбери дію:",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "🎄 Привіт!\nНапиши своє ім’я та прізвище.",
            reply_markup=main_menu()
        )
        context.user_data["waiting_for_name"] = True


async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # КНОПКИ МЕНЮ
    if update.message.text:
        text = update.message.text.strip()
        if update.message.text == "👨‍💻 Від розробника (Мишка)":
            await developer_info(update, context)
            return

        if text == "🎁 Надіслати побажання":
            await send_start(update, context)
            return

        if text == "📋 Список користувачів":
            await list_users(update, context)
            return

    # РЕЄСТРАЦІЯ
    if context.user_data.get("waiting_for_name"):
        if not update.message.text or len(update.message.text.split()) < 2:
            await update.message.reply_text(
                "❌ Будь ласка, введи *ім’я та прізвище*.",
                parse_mode="Markdown"
            )
            return

        users[user_id] = update.message.text.strip()
        save_users(users)
        context.user_data["waiting_for_name"] = False

        await update.message.reply_text(
            f"✅ Запам’ятав!\nТи зареєстрований як:\n{update.message.text.strip()}",
            reply_markup=main_menu()
        )
        return

    # ✉️ АНOНІМНЕ ПОВІДОМЛЕННЯ (БУДЬ-ЯКИЙ ТИП)
    if context.user_data.get("writing_message"):
        recipient_id = waiting_for_recipient.pop(user_id)
        context.user_data["writing_message"] = False

        await context.bot.copy_message(
            chat_id=recipient_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )

        await update.message.reply_text(
            "✅ Побажання надіслано анонімно 🎁",
            reply_markup=main_menu()
        )
        return


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("🎄 Поки що ніхто не зареєстрований.")
        return

    text = "🎁 Зареєстровані користувачі:\n\n"
    for name in users.values():
        text += f"• {name}\n"

    await update.message.reply_text(text)

async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("🎄 Поки що немає зареєстрованих користувачів.")
        return

    keyboard = []

    for uid, name in users.items():
        keyboard.append([
            InlineKeyboardButton(
                text=name,
                callback_data=f"choose:{uid}"
            )
        ])

    await update.message.reply_text(
        "🎁 Кому хочеш надіслати анонімне побажання?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, recipient_id = query.data.split(":")
    sender_id = str(query.from_user.id)

    waiting_for_recipient[sender_id] = recipient_id
    context.user_data["writing_message"] = True

    await query.message.reply_text(
        "✉️ Напиши анонімне побажання:"
    )

def main_menu():
    keyboard = [
        ["🎁 Надіслати побажання"],
        ["📋 Список користувачів"],
        ["👨‍💻 Від розробника (Мишка)"]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
async def developer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👨‍💻 Від розробника (Мишка)\n\n"
        "Цей бот створив Міша аніматор по пріколу от души для всіх роботяг флай кідса. Всіх з наступаючим 🎄\n\n"
        "Бот не зберігає ваші повідомлення. Зберігаються лише ваші імена які ввелись при реєстрації. Підтримується відправка тексту, фото/відео, гіфок, стікерів, аудіо та відеоповідомлень. \n\n"
        "Дякую, що користуєшся 💙"
    )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_users))
    app.add_handler(CommandHandler("send", send_start))
    app.add_handler(CallbackQueryHandler(choose_recipient, pattern="^choose:"))

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_any_message))

    app.run_polling()


if __name__ == "__main__":
    main()


