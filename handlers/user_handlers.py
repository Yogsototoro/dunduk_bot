# handlers/user_handlers.py
import asyncio
from aiogram import types, F, Bot
from database_sqlite import db
from utils import generate_msr_list, generate_cancel_art, normalize_username
from logger import log
from keyboards import get_reply_keyboard
from config import PRIMARY_ADMIN_USERNAME

# --- Вспомогательные функции ---

async def delayed_delete_message(bot: Bot, chat_id: int, message_id: int, delay_seconds: int = 5):
    """Удаляет сообщение с задержкой."""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        log(f"Ошибка при удалении сообщения {message_id}: {e}")

async def _delete_user_message(message: types.Message):
    """Безопасно удаляет сообщение пользователя."""
    try:
        await message.delete()
    except Exception:
        pass # Игнорируем ошибки, если сообщение уже удалено

async def _update_bot_message(message: types.Message, text: str, reply_markup: types.ReplyKeyboardMarkup = None):
    """Удаляет старое сообщение бота и отправляет новое, сохраняя ID."""
    chat_id = message.chat.id
    last_message_id = db.get_last_bot_message_id(chat_id)
    if last_message_id:
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=last_message_id)
        except Exception:
            pass
    
    sent_message = await message.answer(text, reply_markup=reply_markup)
    db.save_last_bot_message_id(chat_id, sent_message.message_id)

async def _handle_cancelled_event(message: types.Message) -> bool:
    """Проверяет, отменено ли событие. Если да - отправляет арт и возвращает True."""
    if db.is_mece_cancelled():
        art = generate_cancel_art()
        if art:
            # В группе админу не нужны WebApp кнопки, поэтому проверяем тип чата
            is_admin_priv = (message.from_user.username == PRIMARY_ADMIN_USERNAME.replace('@', '') 
                             and message.chat.type == "private")
            await _update_bot_message(message, art, reply_markup=get_reply_keyboard(is_admin=is_admin_priv))
        return True
    return False

# --- Обработчики команд ---

async def start(message: types.Message):
    """Обработчик команды /start."""
    if message.from_user is None or message.from_user.username is None:
        return
    await _delete_user_message(message)
    
    # Кнопки WebApp только для лички админа
    is_admin_priv = (message.from_user.username == PRIMARY_ADMIN_USERNAME.replace('@', '') 
                     and message.chat.type == "private")
    
    log(f"Команда старт от @{message.from_user.username} (AdminPriv: {is_admin_priv})")
    sent_message = await message.answer("(▀ Ĺ̯▀   ) жми кнопке", reply_markup=get_reply_keyboard(is_admin=is_admin_priv))
    db.save_last_bot_message_id(message.chat.id, sent_message.message_id)


async def show_list(message: types.Message):
    """Показывает текущий список участников."""
    if message.from_user is None or message.from_user.username is None:
        return
    await _delete_user_message(message)
    
    if await _handle_cancelled_event(message):
        return
        
    text = generate_msr_list()
    is_admin_priv = (message.from_user.username == PRIMARY_ADMIN_USERNAME.replace('@', '') 
                     and message.chat.type == "private")
    await _update_bot_message(message, text, reply_markup=get_reply_keyboard(is_admin=is_admin_priv))


async def add_user(message: types.Message):
    """Добавляет пользователя в список."""
    if message.from_user is None or message.from_user.username is None or message.from_user.id is None:
        return
    await _delete_user_message(message)

    if await _handle_cancelled_event(message):
        return

    nick = normalize_username(message.from_user.username)
    is_admin_priv = (message.from_user.username == PRIMARY_ADMIN_USERNAME.replace('@', '') 
                     and message.chat.type == "private")
    keyboard = get_reply_keyboard(is_admin=is_admin_priv)
    
    if db.is_participant(nick):
        # Если уже в списке, просто показываем актуальный список
        text = generate_msr_list()
        await _update_bot_message(message, text, reply_markup=keyboard)
        return

    max_participants = db.get_max_participants()
    if max_participants > 0 and db.get_participant_count() >= max_participants:
        await _update_bot_message(message, "не успел (⁠°⁠ ⁠-⁠°  )", reply_markup=keyboard)
        return

    db.add_user_to_list(nick, user_id=message.from_user.id)
    log(f"{nick} добавлен в список")
    
    text = generate_msr_list()
    await _update_bot_message(message, text, reply_markup=keyboard)


async def remove_user(message: types.Message):
    """Удаляет пользователя из списка."""
    if message.from_user is None or message.from_user.username is None:
        return
    await _delete_user_message(message)
    
    if await _handle_cancelled_event(message):
        return
    
    nick = normalize_username(message.from_user.username)
    is_admin_priv = (message.from_user.username == PRIMARY_ADMIN_USERNAME.replace('@', '') 
                     and message.chat.type == "private")
    keyboard = get_reply_keyboard(is_admin=is_admin_priv)
    
    if not db.is_participant(nick):
        # Если не в списке, просто показываем актуальный список
        text = generate_msr_list()
        await _update_bot_message(message, text, reply_markup=keyboard)
        return
    
    db.remove_user_from_list_only(nick) 
    log(f"{nick} удалён из списка")
    
    text = generate_msr_list()
    await _update_bot_message(message, text, reply_markup=keyboard)


async def toggle_notifications(message: types.Message):
    """Переключает получение уведомлений в ЛС."""
    if message.from_user is None or message.from_user.username is None:
        return
        
    if message.chat.type != "private":
        await message.answer("( •_•)>⌐■-■ пиши в личный чат с ботом")
        return
    
    username = normalize_username(message.from_user.username)
    new_status = db.toggle_notifications(username)
    status_text = "включены" if new_status else "выключены"
    await message.answer(f"(⌐■_■) уведомления {status_text}")
