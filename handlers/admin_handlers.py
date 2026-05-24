import random
from aiogram import types
from database_sqlite import db
from utils import format_schedule, normalize_username
from logger import log
from config import PRIMARY_ADMIN_USERNAME

# /ь @ник
async def cmd_remove_user_admin(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return
        
        parts = message.text.strip().split(' ', 1)
        
        if len(parts) < 2:
            await message.answer("( •_•)>⌐■-■ ")
            return
        
        nick = normalize_username(parts[1].strip())

        if nick == "@yogsototorobot":
            await message.answer("(¬‿¬) хееехеххххехехеххехеехехех")
            return
        
        if not db.is_participant(nick):
            await message.answer(f"( •_•)>⌐■-■")
            return

        db.remove_user_completely(nick)
        db.remove_chat_member(nick)
        log(f"Админ @{message.from_user.username} удалил: {nick}")
        await message.answer(f"{nick} ヽ/⁠ᐠ⁠｡⁠ꞈ⁠｡⁠ᐟ⁠\\")
        
    except Exception as e:
        log(f"ошибка в команде удаления: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")


# /штошшшшшшшшш @ник
async def cmd_clear_dunduk(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None:
            return
        
        log(f"Команда 'штош' от @{message.from_user.username}: {message.text}")
    
        nick = None
        if message.text:
            parts = message.text.strip().split(' ', 1)
            nick = parts[1] if len(parts) > 1 else None
    
        if not nick and message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.username:
            nick = f"@{message.reply_to_message.from_user.username}"
    
        if not nick:
            await message.answer("( •_•)>⌐■-■")
            return
    
        if nick == "@yogsototorobot":
            await message.answer("сам дундук")
            return

        nick = normalize_username(nick)
    
        user_data = db.get_user(nick)
        
        if user_data and user_data['is_dunduk']:
            db.set_dunduk(nick, False)
            log(f"Админ @{message.from_user.username} снял статус дундука с {nick}")
        else:
            db.set_dunduk(nick, True)
            log(f"Админ @{message.from_user.username} назначил {nick} дундуком")
            await message.answer(f"{nick} дундук")

    except Exception as e:
        log(f"ошибка в штоошшшшшшшшшшш: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")


# /атмена
async def cmd_cancel_mece(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None:
            return
        
        log(f"команда /атмена от @{message.from_user.username}")
        
        if db.is_mece_cancelled():
            db.uncancel_mece()
            log(f"произошла атмена атмены @{message.from_user.username}")
            
            symbols = ['･', '˚', '*', '｡', ' ', '✧', 'ﾟ', ':', '･', '˚', '*', '｡']
            tail_length = random.randint(15, 30)
            tail = ''.join(random.choice(symbols) for _ in range(tail_length))

            await message.answer(f"{tail} (｀∀´)Ψ")
        else:
            db.cancel_mece() # Эта функция также очищает список
            log(f"произошла атмена @{message.from_user.username}")
            await message.answer("¯⁠\⁠_⁠〳⁠ ⁠•̀⁠ ⁠o⁠ ⁠•́⁠ ⁠〵⁠_⁠/⁠¯")
        
    except Exception as e:
        log(f"ошибка в команде отмены: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

# /o - очистка списка участников
async def cmd_clear_list(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None:
            return
        
        log(f"команда /o от @{message.from_user.username}")
        
        db.clear_list_only()
        log(f"список участников очищен админом @{message.from_user.username}")
        await message.answer("список участников очищен")
        
    except Exception as e:
        log(f"ошибка в команде /o: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

# /локация <название>
async def cmd_set_location(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return
        
        log(f"команда /локация от @{message.from_user.username}")
            
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("формат: /локация <название>")
            return
        
        location = parts[1].strip()
        if not location:
            await message.answer("укажи название локации")
            return
        
        db.set_location(location)
        log(f"локация установлена: {location} админом @{message.from_user.username}")
        await message.answer(f"получается что месим тут: {location}")
        
    except Exception as e:
        log(f"ошибка в команде /локация: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

# /расписание <дни>
async def cmd_set_schedule(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return
        
        log(f"команда /расписание от @{message.from_user.username}")
        
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("формат: /расписание 0010011")
            return
        
        schedule = parts[1].strip()
        
        if db.set_schedule(schedule):
            formatted = format_schedule(schedule)
            log(f"расписание установлено: {formatted} админом @{message.from_user.username}")
            await message.answer(f"получается расписаение такое: {formatted}")
        else:
            await message.answer("ошибка установки расписания: формат 7 цифр (0/1) и не все нули")
        
    except Exception as e:
        log(f"ошибка в команде /расписание: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

# /ограничение <число>
async def cmd_set_limit(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return
        
        log(f"команда /ограничение от @{message.from_user.username}")
            
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("формат: /ограничение <число>")
            return
        
        limit_str = parts[1].strip()
        
        try:
            limit = int(limit_str)
        except ValueError:
            await message.answer("ограничение должно быть числом")
            return
        
        if db.set_max_participants(limit):
            if limit == 0:
                log(f"ограничение участников отключено админом @{message.from_user.username}")
                await message.answer("ограничение участников отключено")
            else:
                log(f"ограничение участников установлено: {limit} админом @{message.from_user.username}")
                await message.answer(f"ограничение участников установлено: {limit}")
        else:
            await message.answer("ограничение не может быть отрицательным")
        
    except Exception as e:
        log(f"ошибка в команде /ограничение: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

async def debug_chat_id(message: types.Message):
    try:
        if message.from_user is None or message.from_user.username is None:
            return
        
        log(f"команда /getchatid от @{message.from_user.username}")

        chat_id = message.chat.id
        await message.answer(f"ID этого чата: `{chat_id}`", parse_mode="MarkdownV2")
        log(f"DEBUG: ID чата = {chat_id}")
    except Exception as e:
        log(f"ошибка в команде /getchatid: {e}")
        await message.answer("(*/ω＼*) я хз че случилось")

# --- Управление админами ---

async def cmd_add_admin(message: types.Message):
    """Добавляет нового администратора."""
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return

        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("формат: /add_admin @username")
            return
        
        new_admin_nick = normalize_username(parts[1].strip())

        db.add_admin(new_admin_nick)
        log(f"Главный админ @{message.from_user.username} добавил нового админа: {new_admin_nick}")
        await message.answer(f"админ {new_admin_nick} добавлен")

    except Exception as e:
        log(f"ошибка в команде /add_admin: {e}")
        await message.answer("произошла ошибка")

async def cmd_remove_admin(message: types.Message):
    """Удаляет администратора."""
    try:
        if message.from_user is None or message.from_user.username is None or message.text is None:
            return

        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("формат: /remove_admin @username")
            return
            
        admin_to_remove = normalize_username(parts[1].strip())

        # Нельзя удалить главного админа
        if admin_to_remove.lstrip('@') == PRIMARY_ADMIN_USERNAME.lstrip('@'):
            await message.answer("нельзя удалить главного дундука")
            return
            
        db.remove_admin(admin_to_remove)
        log(f"Главный админ @{message.from_user.username} удалил админа: {admin_to_remove}")
        await message.answer(f"админ {admin_to_remove} удален")

    except Exception as e:
        log(f"ошибка в команде /remove_admin: {e}")
        await message.answer("произошла ошибка")

async def cmd_list_admins(message: types.Message):
    """Показывает список всех администраторов."""
    try:
        if message.from_user is None or message.from_user.username is None:
            return
            
        admins = db.get_admins()
        if not admins:
            await message.answer("админов нет")
            return
            
        admin_list = [f"@{admin}" for admin in admins]
        
        primary_admin_clean = PRIMARY_ADMIN_USERNAME.lstrip('@')
        
        response_parts = []
        for admin in admin_list:
            if admin.lstrip('@') == primary_admin_clean:
                response_parts.append(f"{admin} (главный дундук)")
            else:
                response_parts.append(admin)
                
        response = "список админов:\n- " + "\n- ".join(response_parts)
        await message.answer(response)

    except Exception as e:
        log(f"ошибка в команде /list_admins: {e}")
        await message.answer("произошла ошибка")
