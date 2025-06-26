import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters
)

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# Подключение к Google Sheets
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    sheet = client.open("MyHelperBot_Анкеты").sheet1
except Exception as e:
    logger.error("❌ Ошибка подключения к Google Sheets.")
    logger.error("🔍 Проверь переменную GOOGLE_CREDENTIALS и активирован ли Google Drive API.")
    logger.error(f"🛠️ Техническая ошибка: {e}")
    sheet = None

# Состояния
LANGUAGE, NAME, PHONE = range(3)
user_lang = {}

# Кнопки
main_buttons_ru = [["📚 Курсы и консультации"], ["📍 Контакты", "📝 Заполнить анкету"]]
main_buttons_kz = [["📚 Курстар мен консультациялар"], ["📍 Байланыс", "📝 Сауалнама толтыру"]]

# Назад кнопка
back_button_ru = [["🔙 Назад"]]
back_button_kz = [["🔙 Қайту"]]

# Формирование клавиатуры

def main_keyboard(lang):
    return ReplyKeyboardMarkup(main_buttons_ru if lang == "ru" else main_buttons_kz, resize_keyboard=True)

def back_keyboard(lang):
    return ReplyKeyboardMarkup(back_button_ru if lang == "ru" else back_button_kz, resize_keyboard=True)

# Курсы
COURSES = {
    "Курс 0–3 месяцев": (
        "🌟 <b>Курс для младенцев 0–3 месяцев</b>\n\n"
        "Для родителей, желающих понимать малыша с первых дней.\n"
        "📌 Грудное вскармливание, колики, сон, желтуха, срыгивания.\n"
        "🧑‍⚕️ Поддержка опытного неонатолога.\n"
        "\n<i>Формат:</i> Уроки + аудио в Telegram\n"
        "<i>Доступ:</i> 30 дней\n"
        "<b>Цена:</b> 70 000 тг / 130 $"
    ),
    "Курс 3–6 месяцев": (
        "🌟 <b>Курс для малышей 3–6 месяцев</b>\n\n"
        "🔍 Моторное развитие, массаж, упражнения.\n"
        "👶 Распознавание сигналов и стимуляция развития.\n"
        "\n<i>Формат:</i> Видео Telegram\n"
        "<i>Доступ:</i> Навсегда\n"
        "<b>Цена:</b> 30 000 тг / 6 000 руб"
    ),
    "Наставничество для врачей": (
        "👩‍⚕️ <b>Наставничество для врачей</b>\n\n"
        "📚 10 онлайн-уроков + сопровождение в течение 1 месяца.\n"
        "👩‍⚕️ Актуально для педиатров, акушеров, неонатологов.\n"
        "💡 Практика, кейсы, поддержка."
    )
}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇷🇺 Русский", "🇰🇿 Қазақша"]]
    await update.message.reply_text(
        "👶 <b>Добро пожаловать в MyHelperBot!</b>\n\n"
        "✨ Здесь вы найдёте тепло, поддержку и профессиональные советы для здоровья вашего малыша.\n\n"
        "Выберите язык / Тілді таңдаңыз:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )
    return LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "ru" if "Рус" in update.message.text else "kz"
    user_lang[update.effective_user.id] = lang
    text = (
        "❤️ Спасибо за выбор русского языка! Чем могу быть полезен?"
        if lang == "ru" else
        "❤️ Қазақ тілін таңдағаныңызға рахмет! Қалай көмектесе аламын?"
    )
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))
    return ConversationHandler.END

async def send_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    for title, description in COURSES.items():
        await update.message.reply_text(
            description,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📅 Записаться", callback_data="form")]])
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await ask_name(update, context)

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    text = "📝 Введите ваше имя:" if lang == "ru" else "📝 Атыңызды енгізіңіз:"
    await (update.callback_query.message.reply_text(text) if update.callback_query else update.message.reply_text(text))
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    lang = user_lang.get(update.effective_user.id, "ru")
    await update.message.reply_text(
        "📞 Введите номер телефона (с +7):" if lang == "ru" else "📞 Телефон нөміріңізді енгізіңіз (+7):"
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.startswith("+7") or len(phone) < 10:
        lang = user_lang.get(update.effective_user.id, "ru")
        msg = "⚠️ Неверный формат. Пример: +7 777 123 4567" if lang == "ru" else "⚠️ Қате формат. Мысалы: +7 777 123 4567"
        await update.message.reply_text(msg)
        return PHONE

    name = context.user_data.get("name")
    if sheet:
        sheet.append_row([name, phone])
    lang = user_lang.get(update.effective_user.id, "ru")
    text = "✅ Спасибо! Данные сохранены." if lang == "ru" else "✅ Рақмет! Мәліметтер сақталды."
    await update.message.reply_text(text, reply_markup=main_keyboard(lang))
    return ConversationHandler.END

async def send_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    msg = (
        "📞 <b>Контакты:</b>\n\n"
        "• Telegram — <b>@merey_neonatologist</b>\n"
        "• WhatsApp — <b>+7 771 147 10 34</b>\n"
        "• Профиль врача в Instagram — <b>instagram.com/merey_neonatolog</b>"
        if lang == "ru" else
        "📞 <b>Байланыс:</b>\n\n"
        "• Telegram — <b>@merey_neonatologist</b>\n"
        "• WhatsApp — <b>+7 771 147 10 34</b>\n"
        "• Дәрігердің Instagram парақшасы — <b>instagram.com/merey_neonatolog</b>"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    msg = "🤔 Извините, я вас не понял." if lang == "ru" else "🤔 Кешіріңіз, мен сізді түсінбедім."
    await update.message.reply_text(msg)

# Главная функция

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("Заполнить анкету|Сауалнама толтыру"), ask_name)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("Русский|Қазақша"), set_language))
    app.add_handler(MessageHandler(filters.Regex("Курсы|Курстар"), send_courses))
    app.add_handler(MessageHandler(filters.Regex("Контакты|Байланыс"), send_contacts))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("🤖 Бот запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()