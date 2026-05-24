import sys
from datetime import datetime, timedelta, time
from config import LOG_FILE, MECE_HOUR, MECE_END_HOUR, MECE_MINUTE, TIMEZONE_OFFSET
import random
from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from database_sqlite import db
from config import CHAT_ID
from logger import log

def normalize_username(username: str) -> str:
    """Добавляет @ к нику, если его нет."""
    return f"@{username}" if not username.startswith('@') else username



# форматирование расписания в читаемый вид
def format_schedule(schedule: str) -> str:
    """Преобразует расписание вида '0010011' в 'ср, сб, вс'"""
    days_short = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    
    if not schedule or len(schedule) != 7 or not all(c in "01" for c in schedule):
        return "ошибка расписания"
    
    result = []
    for i, char in enumerate(schedule):
        if char == "1":
            result.append(days_short[i])
    
    return ", ".join(result) if result else "никогда"


# получение даты ближайшего меса с учетом расписания - 2025-04-05
def get_next_mece():
    today = datetime.now().date()
    current = today
    
    # Получаем расписание из базы данных
    schedule = db.get_schedule()
    
    # Ищем ближайший день по расписанию
    for i in range(7):  # Проверяем максимум на неделю вперед
        weekday = current.weekday()  # 0=понедельник, 6=воскресенье
        # Проверяем, есть ли mece в этот день недели
        if schedule[weekday] == "1":
            return current
        current += timedelta(days=1)
    
    # Если не нашли за неделю - возвращаем следующую среду (старое поведение)
    return today + timedelta(days=(2 - today.weekday()) % 7)


# получение даты и времени ближайшего меса - 2025-04-05 19:00:00
def get_next_mece_datetime():
    d = get_next_mece()
    return datetime.combine(d, time(MECE_HOUR, MECE_MINUTE))


# формирование текста с датой в виде - "05.04.2025 19ч (суббота)"
def format_date_with_weekday(date):
    MOSCOW_HOUR_MECE_START = MECE_HOUR + TIMEZONE_OFFSET
    MOSCOW_HOUR_MECE_END = MECE_END_HOUR + TIMEZONE_OFFSET
    days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
    return f"{date.strftime('%d.%m.%Y')} {MOSCOW_HOUR_MECE_START}:00 - {MOSCOW_HOUR_MECE_END}:00 ({days[date.weekday()]})"


# генерация списка месарей с пометкой о дундуковатости, локацией и ограничением
def generate_msr_list():
    next_date = get_next_mece()
    header = f'(⌐■_■) {format_date_with_weekday(next_date)}\n'
    
    # Добавляем локацию, если она установлена
    location = db.get_location()
    if location:
        header += f'• {location}\n'
    
    # Добавляем ограничение, если оно установлено
    max_participants = db.get_max_participants()
    participants = db.get_participants()
    if max_participants > 0:
        current_count = len(participants)
        header += f'[{current_count}/{max_participants}]\n'
    
    header += '\n'

    lines = []
    for i, username in enumerate(participants, 1):
        user_data = db.get_user(username)
        is_dunduk = user_data['is_dunduk'] if user_data else False
        marker = " ← дундук" if is_dunduk else ""
        lines.append(f"{i}. {str(username).lstrip('@').strip()}{marker}")

    return header + "\n".join(lines) if lines else header + "ฅ⁠^⁠•⁠ﻌ⁠•⁠^⁠ฅ"


# генерация атмены
def generate_cancel_art():
    try:
        sky_symbols = [' ', ' ', '✧', ' ', ' ', ' ', '.', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 
                       ' ', ' ', '*', ' ', ' ', ' ', '˚', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 
                       ' ', ' ', '･', ' ', '｡', ' ', ' ', ' ', '･',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', '⁘', ' ', ' ', ' ', '⁎', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 
                       ' ', ' ', '※', ' ', ' ', ' ', '⁎', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ',
                       ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', 
                       '◎', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ']
    
        # длинна строк
        width = 48
        # колличество строк
        height = 5
    
        field = []
        for _ in range(height):
            line = [random.choice(sky_symbols) for _ in range(width)]
            field.append(line)
    
        word = "атмена"
    
        # выбираем случайную позицию для слова
        row = random.randint(1, height - 2)         # строка
        col = random.randint(1, width - len(word))  # позиция в строке
    
        # вставляем слово в поле
        for i, char in enumerate(word):
            field[row][col + i] = char
    
        # преобразуем в строки
        lines = [''.join(line) for line in field]
        return '\n'.join(lines)
    except Exception as e:
        log(f"ошибка в generate_cancel_art: {e}")


# генерация напоминания о месе
def generate_chaotic_reminder():
    """Генерация напоминания с каомодзи ┻━┻︵└(´_｀└) и рандомным текстом"""
    
    kaomoji = "₍⁠₍⁠ ⁠◝⁠(⁠ ﾟ⁠∀⁠ ﾟ⁠ ⁠)⁠◟⁠ ⁠⁾⁠⁾"
    
    reminder_texts = [
        "завтра мес", "завтра замес", "месим походу", "му?",
        "тебе не впадлу?", "взмеснём?", "скоро мес", "и че?",
        "а?", "эммммм", "мес не за горами",
        "да будет мес!", "да будет взмес!", "приходи заебал", "че?", "лень, двигатель прогресса",
        "завтра? оно не существует"
    ]
    
    text = random.choice(reminder_texts)
    
    background_symbols = ['･', '˚', '*', '｡', ' ', '✧', 'ﾟ', ':', '~', '`', '°', ' ', ' ']
    
    left_padding = ''.join(random.choice(background_symbols) for _ in range(random.randint(5, 15)))
    
    result = f"{left_padding}{kaomoji} {text}"
    
    return result


# проверка участия в чате
async def check_chat_membership(bot: Bot, user_id: int, username: str) -> bool:
    """
    Проверяет, является ли пользователь участником чата
    Сначала проверяет локальный список, потом API если нужно
    """
    # проверяем локальный список
    if db.is_chat_member(username):
        return True
    
    # если нет в локальном списке - проверяем через API
    try:
        member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # добавляем в локальный список
            db.add_chat_member(username)
            return True
    except TelegramUnauthorizedError:
        log(f" бот не является администратором или нет доступа к чату {CHAT_ID}")
    except Exception as e:
        log(f" ошибка проверки участника: {e}")
    
    return False
