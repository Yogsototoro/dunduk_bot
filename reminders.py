import random
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from config import CHAT_ID, REMINDER_HOUR, REMINDER_MINUTE, REMINDER_INTERVAL
from utils import get_next_mece_datetime, generate_chaotic_reminder
from logger import log
from database_sqlite import db

# функция отправки напоминаний
async def reminder_task(bot: Bot):
    while True:
        try:
            now = datetime.now()
            next_mece_dt = get_next_mece_datetime()
            reminder_time = next_mece_dt - timedelta(days=1)
            reminder_time = reminder_time.replace(hour=REMINDER_HOUR, minute=REMINDER_MINUTE)
            mece_time = next_mece_dt

            # Получаем дату последнего напоминания из БД
            last_reminder_date_str = db.get_last_reminder_date()
            last_reminder_date = datetime.strptime(last_reminder_date_str, "%Y-%m-%d").date() if last_reminder_date_str else None

            # проверка начала меса
            if now >= mece_time and now.date() == mece_time.date():
                if not last_reminder_date or last_reminder_date != next_mece_dt.date():
                    db.clear_list_only()
                    db.set_last_reminder_date(next_mece_dt.date().isoformat())
                    log("список месарей очищен")

            # Проверка, если текущая дата уже прошла дату месы, сбрасываем счетчик
            if now.date() > next_mece_dt.date():
                if last_reminder_date:
                    db.set_last_reminder_date(None)
                    log("мес прошел, чек отправки сообщения сброшен")

            # проверяем, отправляли ли уже напоминание для этой даты
            if last_reminder_date and last_reminder_date == next_mece_dt.date():
                await asyncio.sleep(REMINDER_INTERVAL)
                continue

            # отправляем напоминание если сегодня 1 день до даты меса
            if now >= reminder_time and now.date() == reminder_time.date():
                if db.is_mece_cancelled():
                    log("mece отменено, напоминание не отправлено")
                    await asyncio.sleep(REMINDER_INTERVAL)
                    continue
                
                chaotic_text = generate_chaotic_reminder()
                
                # отправляем в чат
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=chaotic_text)
                except Exception as e:
                    log(f"ошибка отправки напоминания в чат: {e}")
                
                # отправляем в личку участникам
                users_to_notify = db.get_users_with_notifications()
                for user in users_to_notify:
                    if user['user_id']:
                        try:
                            await bot.send_message(chat_id=user['user_id'], text=chaotic_text)
                        except TelegramForbiddenError:
                            log(f"пользователь {user['username']} заблокировал бота, отключаем ему уведомления")
                            db.toggle_notifications(user['username']) # отключаем, чтобы не спамить
                        except Exception as e:
                            log(f"ошибка отправки личного уведомления {user['username']}: {e}")

                db.set_last_reminder_date(next_mece_dt.date().isoformat())
                log("напоминание о месе отправлено")

            await asyncio.sleep(REMINDER_INTERVAL)

        except Exception as e:
            log(f"Ошибка в reminder_task: {e}")
            await asyncio.sleep(REMINDER_INTERVAL)

async def cat_meme_task(bot: Bot):
    """Отправляет ежедневного кота в чат."""
    import aiohttp
    CAT_API_URL = "https://api.thecatapi.com/v1/images/search"
    # Время отправки кота (например, 10:30 утра по МСК)
    TARGET_HOUR = 10
    TARGET_MINUTE = 30

    while True:
        try:
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            last_cat = db.get_last_cat_date()

            # Если сегодня еще не отправляли и время пришло
            if last_cat != today_str and now.hour == TARGET_HOUR and now.minute >= TARGET_MINUTE:
                async with aiohttp.ClientSession() as session:
                    async with session.get(CAT_API_URL) as response:
                        if response.status == 200:
                            data = await response.json()
                            cat_url = data[0]['url']
                            
                            # Каомодзи для подписи
                            kaomojis = ["ฅ^•ﻌ•^ฅ", "(ﾐㅇ ㅡ ㅇﾐ)", "(=^-ω-^=)", "(๑ↀᆺↀ๑)", "ฅ(≈>ㅅ<≈)ฅ"]
                            caption = f"{random.choice(kaomojis)} Ежедневный дундук-кот!"
                            
                            await bot.send_photo(chat_id=CHAT_ID, photo=cat_url, caption=caption)
                            db.set_last_cat_date(today_str)
                            log("Ежедневный кот отправлен успешно")
                        else:
                            log(f"Не удалось получить кота: статус {response.status}")
            
            await asyncio.sleep(60) # Проверяем раз в минуту
        except Exception as e:
            log(f"Ошибка в cat_meme_task: {e}")
            await asyncio.sleep(60)
