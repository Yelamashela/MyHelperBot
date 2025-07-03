import os
import json
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
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

# --- Главное меню по профилю ---
def get_main_menu(profile: str, lang: str):
    def btn(text, cb):
        return InlineKeyboardButton(text, callback_data=cb)

    if profile == "🤱 Я мама":
        buttons = [
            [btn("📥 Анкета", "form"), btn("📚 Курсы", "courses")],
            [btn("🩺 Услуги", "services")],
            [btn("📍 Контакты", "contacts")]
        ]
    elif profile == "🤰 Беременная":
        buttons = [
            [btn("📥 Анкета", "form"), btn("🤱 Подготовка к родам", "doula")],
            [btn("📚 Курс для беременных", "pregnancy_course")],
            [btn("📍 Контакты", "contacts")]
        ]
    elif profile == "🩺 Специалист":
        buttons = [
            [btn("🌟 Наставничество", "mentorship")],
            [btn("📍 Контакты", "contacts")]
        ]
    else:
        buttons = [[btn("📥 Анкета", "form")]]

    return InlineKeyboardMarkup(buttons)

# --- Старт ---
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
    user_id = query.from_user.id
    lang = "ru" if query.data == "lang_ru" else "kz"
    user_lang[user_id] = lang
    keyboard = [[
        InlineKeyboardButton("🤱 Я мама", callback_data="profile_mama"),
        InlineKeyboardButton("🤰 Беременная", callback_data="profile_pregnant"),
        InlineKeyboardButton("🩺 Специалист", callback_data="profile_doctor")
    ]]
    await query.edit_message_text(
        "🌸 Давайте начнём с выбора, кто вы?" if lang == "ru" else "🌸 Алдымен кім екеніңізді таңдаңыз:",
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
    profile = profile_map.get(query.data)
    context.user_data["profile"] = profile
    lang = user_lang.get(query.from_user.id, "ru")
    await query.edit_message_text(
        "✅ Профиль сохранён! Вот что я умею 👇" if lang == "ru" else "✅ Профиль сақталды! Мен істей аламын 👇",
        reply_markup=get_main_menu(profile, lang)
    )

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = user_lang.get(query.from_user.id, "ru")

    # Примеры поведения
    if data == "services":
        await query.edit_message_text(
            "🩺 Услуги врача-неонатолога:\n\n- Онлайн-консультации\n- Выезд на дом\n- Сопровождение после родов\n\nВыберите в меню ниже, чтобы узнать подробнее.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 Анкета", callback_data="form"),
                InlineKeyboardButton("📋 Главное меню", callback_data="menu")
            ]])
        )
    elif data == "courses":
        await query.edit_message_text(
            "📚 Курсы для родителей:\n\n- 0–3 месяцев\n- 3–6 месяцев\n- Температура и иммунитет\n\n🔜 Подробности скоро появятся!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 Анкета", callback_data="form"),
                InlineKeyboardButton("📋 Главное меню", callback_data="menu")
            ]])
        )
    elif data == "contacts":
        await query.edit_message_text(
            "📱 Контакты:\n\nWhatsApp: +7 771 147 10 34\nTelegram: @merey_neonatologist\nКанал: https://t.me/+ohgaSD3VEQc5MGZi",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📥 Заполнить анкету", callback_data="form"),
                InlineKeyboardButton("📋 Главное меню", callback_data="menu")
            ]])
        )
    elif data == "form":
        context.user_data["question"] = NAME
        await query.edit_message_text("📝 Давайте начнём анкету!", parse_mode="HTML")
        return await ask_question(update, context)
    elif data == "menu":
        profile = context.user_data.get("profile", "🤱 Я мама")
        await query.edit_message_text("📋 Главное меню:", reply_markup=get_main_menu(profile, lang))

# --- Вопросы анкеты ---
questions = {
    NAME: "📝 Как вас зовут?",
    LOCATION: "🌍 В каком вы городе/стране?",
    DOB: "📅 Дата родов?",
    CONCERN: "🤔 Что вас беспокоит?",
    FORMAT: "📌 Предпочтительный формат: онлайн / оффлайн / выезд?",
    TRIED: "🔄 Что уже пробовали?",
    READY: "💬 Готовы к работе и оплате?"
}

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_index = context.user_data.get("question", NAME)
    total = READY - NAME + 1
    progress = q_index - NAME + 1
    text = questions[q_index]
    await update.callback_query.message.reply_text(
        f"{text}\n\n📊 Шаг {progress} из {total}"
    )
    context.user_data["question"] = q_index
    return q_index

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_index = context.user_data.get("question", NAME)
    context.user_data[q_index] = update.message.text
    q_index += 1
    if q_index > READY:
        if sheet:
            row = [context.user_data.get(q) for q in range(NAME, READY + 1)]
            sheet.append_row(row)
        lang = user_lang.get(update.effective_user.id, "ru")
        await update.message.reply_text(
            "✅ Анкета получена! Мы с вами свяжемся в течение 24ч." if lang == "ru" else "✅ Сауалнама қабылданды! Біз сізбен 24 сағат ішінде хабарласамыз."
        )
        profile = context.user_data.get("profile", "🤱 Я мама")
        await update.message.reply_text("📋 Главное меню:", reply_markup=get_main_menu(profile, lang))
        return ConversationHandler.END
    context.user_data["question"] = q_index
    return await ask_question(update, context)

# --- Неизвестное сообщение ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤗 Я рядом. Пожалуйста, используйте меню.")

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