import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from config import BOT_TOKEN
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

# Google Sheets
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Анкеты").sheet1
except Exception as e:
    logging.error(f"Ошибка при подключении к Google Sheets: {e}")
    sheet = None

user_data = {}
language = {}

# Языки
texts = {
    "ru": {
        "welcome": "Добро пожаловать, {name}!\n\nЯ — бот врача-неонатолога. Чем могу помочь?",
        "choose": "Выберите действие:",
        "services": "Выберите услугу:",
        "form": "📝 Как вас зовут?",
        "contact": "📱 Контакты:\n\nWhatsApp: +7 771 147 10 34\nTelegram: @merey_neonatologist\nКанал: https://t.me/+ohgaSD3VEQc5MGZi"
    },
    "kz": {
        "welcome": "Қош келдіңіз, {name}!\n\nМен — жаңа туған нәрестелер дәрігерімін. Қалай көмектесе аламын?",
        "choose": "Таңдаңыз:",
        "services": "Қызмет түрін таңдаңыз:",
        "form": "📝 Атыңыз кім?",
        "contact": "📱 Байланыс:\n\nWhatsApp: +7 771 147 10 34\nTelegram: @merey_neonatologist\nКанал: https://t.me/+ohgaSD3VEQc5MGZi"
    }
}

# Старт с выбором языка
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz")]
    ]
    await update.message.reply_text(
        "Выберите язык / Тілді таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Установка языка
    if query.data.startswith("lang_"):
        lang = query.data.split("_")[1]
        language[user_id] = lang
        keyboard = [
            [InlineKeyboardButton("📋 Услуги / Қызметтер", callback_data="services")],
            [InlineKeyboardButton("📝 Анкета / Сауалнама", callback_data="form")],
            [InlineKeyboardButton("📱 Контакты", callback_data="contacts")]
        ]
        await query.edit_message_text(
            texts[lang]["welcome"].format(name=query.from_user.first_name) + "\n\n" + texts[lang]["choose"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    lang = language.get(user_id, "ru")

    if query.data == "services":
        keyboard = [
            [InlineKeyboardButton("🩺 Онлайн-консультация", callback_data="service_online")],
            [InlineKeyboardButton("🏡 Оффлайн с выездом", callback_data="service_offline")],
            [InlineKeyboardButton("👶 Курс 0–3 мес", callback_data="course_0_3")],
            [InlineKeyboardButton("🍼 Курс 3–6 мес", callback_data="course_3_6")],
            [InlineKeyboardButton("🌡 Instagram-канал", callback_data="ig_channel")],
            [InlineKeyboardButton("🤱 Доула", callback_data="doula")],
            [InlineKeyboardButton("🌟 Наставничество", callback_data="mentorship")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu")]
        ]
        await query.edit_message_text(texts[lang]["services"], reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "contacts":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
        await query.edit_message_text(texts[lang]["contact"], reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "form":
        user_data[user_id] = {}
        await query.edit_message_text(texts[lang]["form"])

    elif query.data == "menu":
        await start(update, context)

    # (оставшиеся кнопки услуг и описания оставим как было ранее — код был правильный)

# Обработка текстовых сообщений
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    lang = language.get(user_id, "ru")

    if user_id not in user_data:
        await update.message.reply_text("Введите /start чтобы начать." if lang == "ru" else "Бастау үшін /start деп жазыңыз.")
        return

    data = user_data[user_id]
    prompts = [
        ("name", "📍 Город / қала?"),
        ("city", "📅 Дата родов / Туған күні?"),
        ("birthdate", "❓ Что беспокоит / Мәселе неде?"),
        ("problem", "🔎 Формат (онлайн / оффлайн / выезд)?"),
        ("format", "🤔 Что уже пробовали / Не істеп көрдіңіз?"),
        ("tried", "💬 Готовы работать и оплачивать? (да/нет) / Дайынсыз ба?")
    ]

    for key, next_q in prompts:
        if key not in data:
            if key == "birthdate" and len(text) < 4:
                await update.message.reply_text("Пожалуйста, введите корректную дату рождения.")
                return
            data[key] = text.strip()
            await update.message.reply_text(next_q)
            return

    if "ready" not in data:
        data["ready"] = text.strip()
        if sheet:
            try:
                sheet.append_row([
                    data.get("name", ""), data.get("city", ""), data.get("birthdate", ""),
                    data.get("problem", ""), data.get("format", ""), data.get("tried", ""), data.get("ready", "")
                ])
            except Exception as e:
                await update.message.reply_text("Ошибка при сохранении. Попробуйте позже.")
                logging.error(e)
        await update.message.reply_text("✅ Спасибо! Ваша анкета принята. Мы скоро свяжемся с вами." if lang == "ru" else "✅ Рахмет! Сауалнама қабылданды. Біз сізбен хабарласамыз.")
        user_data.pop(user_id)

# Автоответ — бот не понял
async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = language.get(update.effective_user.id, "ru")
    text = "Я вас не понял. Напишите /start чтобы начать." if lang == "ru" else "Сізді түсінбедім. /start деп бастаңыз."
    await update.message.reply_text(text)

# Запуск
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
app.add_handler(MessageHandler(filters.ALL, fallback_handler))

if __name__ == '__main__':
    app.run_polling()