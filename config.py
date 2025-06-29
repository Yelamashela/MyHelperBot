import os
import json
import gspread
from google.oauth2.service_account import Credentials

# Название Google-таблицы
SPREADSHEET_NAME = "MyHelperBot_Анкеты"

# Получаем JSON из переменной окружения
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

# Настройка доступа
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
gc = gspread.authorize(credentials)

# Получаем нужный лист
def get_worksheet():
    sh = gc.open(SPREADSHEET_NAME)
    return sh.sheet1  # можно заменить на .worksheet("Лист1")