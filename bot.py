import os
import json
import logging
import datetime
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
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
    logger.error("❌ Ошибка подключения к Google Sheets:", e)
    sheet = None

# --- Состояния анкеты ---
LANG, PROFILE, NAME, LOCATION, DOB, CONCERN, FORMAT, TRIED, READY, FEEDBACK_SCORE, FEEDBACK_TEXT = range(11)
user_lang = {}
user_data_progress = {}

# --- Основное меню ---
def main_menu(lang):
    return ReplyKeyboardMarkup([
        ["👩 Профиль", "📚 Курсы и консультации"],
        ["📥 Заполнить анкету", "💬 Поддержка"],
        ["📍 Контакты", "📊 Обратная связь"]
    ] if lang == "ru" else [
        ["👩 Профиль", "📚 Курстар мен консультациялар"],
        ["📥 Сауалнама толтыру", "💬 Қолдау"],
        ["📍 Байланыс", "📊 Кері байланыс"]
    ], resize_keyboard=True)

# --- Старт / Язык ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["🇷🇺 Русский", "🇰🇿 Қазақша"]]
    await update.message.reply_text(
        "👶 <b>Добро пожаловать в MyHelperBot!</b>\n\n"
        "✨ Я помогу вам с заботой, профессионализмом и теплом.\n\n"
        "Выберите язык / Тілді таңдаңыз:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )
    return LANG

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = "ru" if "Рус" in update.message.text else "kz"
    user_lang[update.effective_user.id] = lang
    await update.message.reply_text(
        "🌸 Давайте начнём с выбора, кто вы?" if lang == "ru" else "🌸 Алдымен кім екеніңізді таңдаңыз:",
        reply_markup=ReplyKeyboardMarkup([
            ["🤱 Я мама", "🤰 Беременная", "🩺 Специалист"]
        ], resize_keyboard=True)
    )
    return PROFILE

# --- Профиль и меню ---
async def set_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    profile = update.message.text
    context.user_data["profile"] = profile
    await update.message.reply_text(
        "✅ Профиль сохранён! Вот что я умею 👇" if lang == "ru" else "✅ Профиль сақталды! Мен істей аламын 👇",
        reply_markup=main_menu(lang)
    )
    return ConversationHandler.END

# --- Анкета с шагами и прогрессом ---
questions = {
    NAME: ("📝 Как вас зовут?", "📝 Атыңыз кім?"),
    LOCATION: ("🌍 В каком вы городе/стране?", "🌍 Қай қала/елде тұрасыз?"),
    DOB: ("📅 Дата родов?", "📅 Босану күні?"),
    CONCERN: ("🤔 Что вас беспокоит?", "🤔 Не мазасызданасыз ба?"),
    FORMAT: ("📌 Предпочтительный формат: онлайн / оффлайн / выезд?", "📌 Қандай формат ыңғайлы: онлайн / оффлайн / шығу?"),
    TRIED: ("🔄 Что уже пробовали?", "🔄 Не істеп көрдіңіз?"),
    READY: ("💬 Готовы к работе и оплате?", "💬 Жұмыс істеуге және төлеуге дайынсыз ба?")
}

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    q_index = context.user_data.get("question", NAME)
    total = len(questions)
    text = questions[q_index][0] if lang == "ru" else questions[q_index][1]
    await update.message.reply_text(f"{text}\n({q_index - NAME + 1} из {total})")
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
            "✅ Анкета получена! Мы с вами свяжемся в течение 24ч." if lang == "ru" else "✅ Сауалнама қабылданды! Біз сізбен 24 сағат ішінде хабарласамыз.",
            reply_markup=main_menu(lang)
        )
        return ConversationHandler.END
    context.user_data["question"] = q_index
    return await ask_question(update, context)

# --- Поддержка (чат с заботой) ---
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    now = datetime.datetime.now().hour
    if 22 <= now or now < 6:
        text = "Сейчас поздно, но я с тобой. Вот несколько советов от меня на ночь 💫"
    else:
        text = "💬 Выберите или напишите, что вас беспокоит:\n\n🍼 У ребёнка колики\n😴 Плохо спит\n❓ Что спросить?" if lang == "ru" else "💬 Сұрағыңызды жазыңыз немесе таңдаңыз:\n\n🍼 Балада іш қату\n😴 Ұйқысы нашар\n❓ Не сұрау?"
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True))

# --- Обратная связь ---
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    await update.message.reply_text("📊 Оцените работу бота от 1 до 5:", reply_markup=ReplyKeyboardMarkup([["1", "2", "3", "4", "5"]], resize_keyboard=True))
    return FEEDBACK_SCORE

async def feedback_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = update.message.text.strip()
    context.user_data["score"] = score
    if score == "5":
        await update.message.reply_text("💛 Спасибо за высокую оценку!")
        return ConversationHandler.END
    await update.message.reply_text("Что бы вы хотели улучшить?")
    return FEEDBACK_TEXT

async def feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    logger.info(f"Оценка: {context.user_data.get('score')}, Отзыв: {text}")
    await update.message.reply_text("Благодарим за обратную связь!")
    return ConversationHandler.END

# --- Неизвестное сообщение ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = user_lang.get(update.effective_user.id, "ru")
    text = "🤗 Ты всё делаешь правильно. Я рядом." if lang == "ru" else "🤗 Сен бәрін дұрыс істеп жатырсың. Мен осындамын."
    await update.message.reply_text(text, reply_markup=main_menu(lang))

# --- Основной запуск ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    form_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Заполнить анкету|Сауалнама толтыру"), ask_question)],
        states={q: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)] for q in range(NAME, READY + 1)},
        fallbacks=[]
    )

    feedback_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Обратная связь|Кері байланыс"), feedback_start)],
        states={FEEDBACK_SCORE: [MessageHandler(filters.TEXT, feedback_score)], FEEDBACK_TEXT: [MessageHandler(filters.TEXT, feedback_text)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("Русский|Қазақша"), set_language))
    app.add_handler(MessageHandler(filters.Regex("🤱|🤰|🩺"), set_profile))
    app.add_handler(MessageHandler(filters.Regex("Курсы|Курстар"), support))
    app.add_handler(MessageHandler(filters.Regex("Контакты|Байланыс"), support))
    app.add_handler(MessageHandler(filters.Regex("Поддержка|Қолдау"), support))
    app.add_handler(MessageHandler(filters.Regex("Назад|Қайту"), start))
    app.add_handler(form_conv)
    app.add_handler(feedback_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()