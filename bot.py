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
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    client = gspread.authorize(credentials)
    sheet = client.open("MyHelperBot_Анкеты").sheet1
except Exception as e:
    logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
    sheet = None

# --- Состояния ---
LANG, PROFILE, NAME, LOCATION, DOB, CONCERN, FORMAT, TRIED, READY = range(9)
user_lang = {}

# --- Меню по профилю ---
def main_menu(profile):
    def btn(text, cb): return InlineKeyboardButton(text, callback_data=cb)
    if profile == "🤱 Я мама":
        return InlineKeyboardMarkup([
            [btn("🩺 Консультации", "services"), btn("📚 Курсы", "courses")],
            [btn("📥 Заполнить анкету", "form")],
            [btn("📍 Контакты", "contacts")]
        ])
    elif profile == "🤰 Беременная":
        return InlineKeyboardMarkup([
            [btn("🤱 Подготовка к родам", "doula")],
            [btn("📚 Курс для беременных", "pregnancy_course")],
            [btn("📍 Контакты", "contacts")]
        ])
    elif profile == "🩺 Специалист":
        return InlineKeyboardMarkup([
            [btn("🌟 Наставничество", "mentorship")],
            [btn("📍 Контакты", "contacts")]
        ])
    return InlineKeyboardMarkup([[btn("📥 Анкета", "form")]])

# --- Старт ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz")
    ]]
    await update.message.reply_text(
        "👶 <b>Добро пожаловать в MyHelperBot!</b>\n\nВыберите язык обслуживания:",
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
    await query.edit_message_text("Кто вы?", reply_markup=InlineKeyboardMarkup(keyboard))

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
    await query.edit_message_text("✅ Профиль выбран!", reply_markup=main_menu(profile))

# --- Анкета ---
questions = {
    NAME: "Как вас зовут?",
    LOCATION: "Город/страна:",
    DOB: "Дата родов (дд.мм.гггг):",
    CONCERN: "Что вас беспокоит?",
    FORMAT: "Формат: онлайн / оффлайн / выезд?",
    TRIED: "Что уже пробовали?",
    READY: "Готовы к работе и оплате?"
}

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get("question", NAME)
    step = idx - NAME + 1
    await update.callback_query.message.reply_text(f"{questions[idx]}\n\n📊 Шаг {step} из 7")
    context.user_data["question"] = idx
    return idx

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data.get("question")
    answer = update.message.text.strip()

    if idx == DOB:
        try:
            datetime.datetime.strptime(answer, "%d.%m.%Y")
        except:
            await update.message.reply_text("❗ Пожалуйста, укажите дату в формате дд.мм.гггг")
            return idx

    context.user_data[idx] = answer
    idx += 1
    if idx > READY:
        if sheet:
            row = [context.user_data.get(i, '') for i in range(NAME, READY + 1)]
            sheet.append_row(row)
        await update.message.reply_text("✅ Спасибо! Мы с вами свяжемся в течение 24ч.")
        profile = context.user_data.get("profile")
        await update.message.reply_text("📋 Главное меню:", reply_markup=main_menu(profile))
        return ConversationHandler.END
    context.user_data["question"] = idx
    await update.message.reply_text(questions[idx])
    return idx

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "services":
        await query.edit_message_text("🩺 Онлайн или офлайн?", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🧑‍💻 Онлайн", callback_data="online")],
            [InlineKeyboardButton("🏠 Выезд на дом", callback_data="offline")],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu")]
        ]))
    elif data == "online":
        await query.edit_message_text(
            "📞 <b>Онлайн-консультация</b> — 2 часа видеосозвона, 7 дней WhatsApp-сопровождения.\nЦена: 120 000 тг",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Записаться", callback_data="form")],
                [InlineKeyboardButton("🔙 Назад", callback_data="services")]
            ]), parse_mode="HTML"
        )
    elif data == "offline":
        await query.edit_message_text(
            "🏠 <b>Выезд на дом</b> — осмотр, обучение, поддержка 7 дней.\nЦена: 170 000 тг (Шымкент) / 300 000 тг + перелёт",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📥 Записаться", callback_data="form")],
                [InlineKeyboardButton("🔙 Назад", callback_data="services")]
            ]), parse_mode="HTML"
        )
    elif data == "form":
        context.user_data["question"] = NAME
        return await ask_question(update, context)
    elif data == "contacts":
        await query.edit_message_text(
            "📱 Контакты:\nWhatsApp: +7 771 147 10 34\nTelegram: @merey_neonatologist\nКанал: https://t.me/+ohgaSD3VEQc5MGZi",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 Главное меню", callback_data="menu")]])
        )
    elif data == "menu":
        profile = context.user_data.get("profile")
        await query.edit_message_text("📋 Главное меню:", reply_markup=main_menu(profile))

# --- Неизвестное сообщение ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ Пожалуйста, воспользуйтесь меню. Я здесь, чтобы помочь 🌸")

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