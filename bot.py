import os
import json
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# --- Логирование ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# --- Google Sheets ---
try:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open("MyHelperBot_Анкеты").sheet1
except Exception as e:
    logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
    sheet = None

# --- Состояния ---
LANG, PROFILE, NAME, LOCATION, DOB, CONCERN, FORMAT, TRIED, READY = range(9)
user_lang = {}

# --- Главное меню ---
def get_main_menu(profile: str):
    btn = InlineKeyboardButton
    buttons = []

    if profile == "🤱 Я мама":
        buttons = [
            [btn("📚 Курсы", "courses"), btn("🩺 Услуги", "services")],
            [btn("👩‍⚕ О враче", "about_doctor"), btn("📥 Анкета", "form")],
            [btn("📍 Контакты", "contacts")]
        ]
    elif profile == "🤰 Беременная":
        buttons = [
            [btn("🤱 Подготовка к родам", "doula"), btn("📚 Курсы", "courses")],
            [btn("👩‍⚕ О враче", "about_doctor"), btn("📥 Анкета", "form")],
            [btn("📍 Контакты", "contacts")]
        ]
    elif profile == "🩺 Специалист":
        buttons = [
            [btn("🌟 Наставничество", "mentorship")],
            [btn("📍 Контакты", "contacts")]
        ]
    return InlineKeyboardMarkup(buttons)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz")
    ]]
    await update.message.reply_text(
        "👶 <b>Добро пожаловать в MyHelperBot!</b>\n\n"
        "✨ Я помогу вам с заботой, профессионализмом и теплом.\n\n"
        "Выберите язык / Тілді таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# --- Установка языка ---
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = "ru" if query.data == "lang_ru" else "kz"
    user_lang[query.from_user.id] = lang
    keyboard = [[
        InlineKeyboardButton("🤱 Я мама", callback_data="profile_mama"),
        InlineKeyboardButton("🤰 Беременная", callback_data="profile_pregnant"),
        InlineKeyboardButton("🩺 Специалист", callback_data="profile_doctor")
    ]]
    await query.message.reply_text(
        "🌸 Давайте начнём. Кто вы?" if lang == "ru" else "🌸 Алдымен кімсіз?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Установка профиля ---
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
    lang = user_lang.get(query.from_user.id, "ru")
    await query.message.reply_text(
        "✅ Профиль сохранён! Вот главное меню:",
        reply_markup=get_main_menu(profile)
    )
    # Автопоказ блока "О враче"
    if profile in ["🤱 Я мама", "🤰 Беременная"]:
        await query.message.reply_text(
            "<b>👩‍⚕ Жуманова Мерей Насірханқызы</b>\n\n"
            "Врач-неонатолог с опытом более 13 лет.\n"
            "🔹 Специализация: реанимация, хирургия, роды, выхаживание недоношенных.\n"
            "👶 Более 18 000 малышей прошли через её руки.\n\n"
            "<i>«Вы не одна. Я рядом, чтобы помочь вам понять малыша — с первых минут жизни и дальше.»</i>\n\n"
            "📩 Хотите получить помощь? Начнём с короткой анкеты:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Заполнить анкету", callback_data="form")],
                [InlineKeyboardButton("📋 Главное меню", callback_data="menu")]
            ]),
            parse_mode="HTML"
        )

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    profile = context.user_data.get("profile", "🤱 Я мама")

    if data == "about_doctor":
        await query.message.reply_text(
            "<b>👩‍⚕ Жуманова Мерей Насірханқызы</b>\n\n"
            "Врач-неонатолог с опытом более 13 лет.\n"
            "🔹 Реанимация новорождённых, хирургия, патология, роды.\n"
            "👶 Более 18 000 малышей прошли через её руки.\n\n"
            "<i>«Вы не одна. Я рядом, чтобы помочь вам понять малыша — с первых минут жизни и дальше.»</i>\n\n"
            "📩 Хотите получить помощь? Начнём с анкеты:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Анкета", callback_data="form")],
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ]),
            parse_mode="HTML"
        )

    elif data == "menu":
        await query.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu(profile))

    elif data == "form":
        context.user_data["question"] = NAME
        await query.message.reply_text("📝 Давайте начнём анкету!")
        return await ask_question(update, context)

    elif data == "courses":
        await query.message.reply_text(
            "📚 Доступные курсы:\n\n"
            "1. 👶 0–3 мес: питание, колики, желтуха, кожа\n"
            "2. 👶 3–6 мес: моторика, массаж, развитие\n"
            "3. 🌡 Температура и иммунитет\n\n"
            "Нажмите на интересующий курс для подробностей.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("0–3 мес", callback_data="course_0_3")],
                [InlineKeyboardButton("3–6 мес", callback_data="course_3_6")],
                [InlineKeyboardButton("Температура и иммунитет", callback_data="course_temp")],
                [InlineKeyboardButton("📋 Назад", callback_data="menu")]
            ])
        )

    # Допиши обработку других курсов, услуг, консультаций и т.д.

# --- Анкета ---
questions = {
    NAME: "📝 Как вас зовут?",
    LOCATION: "🌍 В каком вы городе/стране?",
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
    await update.message.reply_text(f"{questions[step]}\n\nШаг {progress} из {total}")
    return step

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data["question"]
    answer = update.message.text.strip()
    if not answer:
        await update.message.reply_text("❗ Пожалуйста, введите корректный ответ.")
        return step
    context.user_data[step] = answer
    next_step = step + 1
    if next_step > READY:
        if sheet:
            row = [context.user_data.get(i, "") for i in range(NAME, READY + 1)]
            sheet.append_row(row)
        await update.message.reply_text("✅ Анкета получена! Мы с вами свяжемся в течение 24ч.")
        profile = context.user_data.get("profile", "🤱 Я мама")
        await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu(profile))
        return ConversationHandler.END
    context.user_data["question"] = next_step
    return await ask_question(update, context)

# --- Неизвестное сообщение ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ Пожалуйста, используйте кнопки меню.")

# --- Основной запуск ---
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

    logger.info("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()