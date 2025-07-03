# bot.py
import os
import json
import logging
import gspread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)
from google.oauth2.service_account import Credentials

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# Google Sheets
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open("MyHelperBot_Анкеты").sheet1
except Exception as e:
    logger.error(f"Ошибка Google Sheets: {e}")
    sheet = None

# Состояния анкеты
LANG, PROFILE, NAME, LOCATION, DOB, CONCERN, FORMAT, TRIED, READY = range(9)
user_lang = {}

# Главное меню
def get_main_menu(profile: str):
    btn = InlineKeyboardButton
    if profile == "🤱 Я мама":
        return InlineKeyboardMarkup([
            [btn("📚 Курсы", callback_data="courses")],
            [btn("🩺 Услуги", callback_data="services")],
            [btn("👩‍⚕ О враче", callback_data="about_doctor")],
            [btn("📥 Анкета", callback_data="form")],
            [btn("📍 Контакты", callback_data="contacts")]
        ])
    elif profile == "🤰 Беременная":
        return InlineKeyboardMarkup([
            [btn("📚 Курсы", callback_data="courses")],
            [btn("🤱 Подготовка к родам", callback_data="doula")],
            [btn("👩‍⚕ О враче", callback_data="about_doctor")],
            [btn("📥 Анкета", callback_data="form")],
            [btn("📍 Контакты", callback_data="contacts")]
        ])
    elif profile == "🩺 Специалист":
        return InlineKeyboardMarkup([
            [btn("🌟 Наставничество", callback_data="mentorship")],
            [btn("📍 Контакты", callback_data="contacts")]
        ])
    return InlineKeyboardMarkup([[btn("📥 Анкета", callback_data="form")]])

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz")]
    ]
    await update.message.reply_text(
        "👶 <b>Добро пожаловать в MyHelperBot!</b>\n\n"
        "✨ Я помогу вам с заботой, профессионализмом и теплом.\n\n"
        "Выберите язык / Тілді таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# Язык
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "ru" if query.data == "lang_ru" else "kz"
    user_lang[query.from_user.id] = lang
    keyboard = [
        [InlineKeyboardButton("🤱 Я мама", callback_data="profile_mama")],
        [InlineKeyboardButton("🤰 Беременная", callback_data="profile_pregnant")],
        [InlineKeyboardButton("🩺 Специалист", callback_data="profile_doctor")]
    ]
    await query.message.reply_text(
        "🌸 Кто вы?" if lang == "ru" else "🌸 Кімсіз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Профиль
async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    profile_map = {
        "profile_mama": "🤱 Я мама",
        "profile_pregnant": "🤰 Беременная",
        "profile_doctor": "🩺 Специалист"
    }
    profile = profile_map[query.data]
    context.user_data["profile"] = profile
    await query.message.reply_text("✅ Профиль сохранён. Главное меню:",
                                   reply_markup=get_main_menu(profile))
    if profile in ["🤱 Я мама", "🤰 Беременная"]:
        await query.message.reply_text(
            "<b>👩‍⚕ Жуманова Мерей Насірханқызы</b>\n\n"
            "Врач-неонатолог с опытом более 13 лет.\n"
            "🔹 Реанимация, хирургия, роды, недоношенные дети.\n"
            "👶 Более 18 000 малышей прошли через её руки.\n\n"
            "<i>«Вы не одна. Я рядом, чтобы помочь вам понять малыша — с первых минут жизни и дальше.»</i>\n\n"
            "📩 Заполните анкету — и я подберу для вас формат помощи.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Анкета", callback_data="form")],
                [InlineKeyboardButton("📋 Главное меню", callback_data="menu")]
            ])
        )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    profile = context.user_data.get("profile", "🤱 Я мама")

    if data == "menu":
        await query.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu(profile))

    elif data == "about_doctor":
        await query.message.reply_text(
            "<b>👩‍⚕ Жуманова Мерей Насірханқызы</b>\n\n"
            "Врач-неонатолог с опытом 13+ лет.\n"
            "Реанимация, хирургия, ГВ, адаптация, патология.\n"
            "👶 18 000 малышей. 100% включённость.\n\n"
            "<i>«Вы не одна. Я рядом, чтобы помочь вам понять малыша — с первых минут жизни и дальше.»</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Анкета", callback_data="form")],
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

    elif data == "contacts":
        await query.message.reply_text(
            "📱 Контакты:\n\n"
            "WhatsApp: +7 771 147 10 34\n"
            "Telegram: @merey_neonatologist\n"
            "Канал: https://t.me/+ohgaSD3VEQc5MGZi",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

    elif data == "form":
        context.user_data["question"] = NAME
        await query.message.reply_text("📝 Давайте начнём анкету!")
        return await ask_question(update, context)

    elif data == "courses":
        await query.message.reply_text(
            "📚 Курсы:\n\n"
            "👶 0–3 мес — грудное вскармливание, колики, желтуха\n"
            "👶 3–6 мес — развитие, массаж, перевороты\n"
            "🌡 Температура и иммунитет — без лекарств\n\n"
            "📩 Все курсы содержат видеоуроки, инструкции и поддержку.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

    elif data == "services":
        await query.message.reply_text(
            "🩺 Консультации:\n\n"
            "📞 Онлайн: 2ч видеозвонок + 7 дней поддержки\n"
            "🏡 Оффлайн: выезд на дом + 7 дней сопровождения\n\n"
            "⚠ Подходит мамам с трудностями ГВ, ЖКТ, срыгиваниями, коликами.\n"
            "📩 Начните с анкеты, чтобы подобрать формат.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Анкета", callback_data="form")],
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

    elif data == "mentorship":
        await query.message.reply_text(
            "🌟 Наставничество:\n\n"
            "🔹 Для врачей, медсестёр и акушерок\n"
            "🔹 10 уроков, 1 месяц, поддержка, разбор кейсов\n"
            "🔹 Темы: грудное вскармливание, Доула, желтуха, уход за НР\n\n"
            "📩 Хочешь зарабатывать и не выгорать? Начни с анкеты!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Анкета", callback_data="form")],
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

# Анкета
questions = {
    NAME: "📝 Ваше имя?",
    LOCATION: "🌍 Город / страна?",
    DOB: "📅 Дата родов?",
    CONCERN: "🤔 Что вас беспокоит?",
    FORMAT: "📌 Онлайн / оффлайн / выезд?",
    TRIED: "🔄 Что уже пробовали?",
    READY: "💬 Готовы к работе и оплате?"
}

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data["question"]
    total = READY - NAME + 1
    progress = step - NAME + 1
    await update.message.reply_text(f"{questions[step]}\n\n📊 Шаг {progress} из {total}")
    return step

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data["question"]
    answer = update.message.text.strip()
    if not answer:
        await update.message.reply_text("❗ Пожалуйста, введите корректный ответ.")
        return step
    context.user_data[step] = answer
    step += 1
    if step > READY:
        if sheet:
            sheet.append_row([context.user_data.get(i, "") for i in range(NAME, READY + 1)])
        await update.message.reply_text("✅ Спасибо! Анкета получена. Мы свяжемся с вами в течение 24 часов.")
        profile = context.user_data.get("profile", "🤱 Я мама")
        await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu(profile))
        return ConversationHandler.END
    context.user_data["question"] = step
    return await ask_question(update, context)

# Неизвестное сообщение
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ Пожалуйста, используйте меню ниже.")

# Основной запуск
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    form_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^form$")],
        states={q: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)] for q in range(NAME, READY + 1)},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(set_profile, pattern="^profile_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(form_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()