from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from database_sqlite import db
from config import PRIMARY_ADMIN_USERNAME
from utils import check_chat_membership
from logger import log


class PrimaryAdminCheckMiddleware(BaseMiddleware):
    """
    Мидлварь для проверки, является ли пользователь ГЛАВНЫМ администратором.
    Срабатывает только если у хендлера есть флаг "primary_admin_check": True.
    """
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем наличие флага в хендлере
        if not data.get("primary_admin_check"):
            return await handler(event, data)

        # Пропускаем, если нет пользователя
        if not event.from_user or not event.from_user.username:
            return

        # Выполняем проверку
        if f"@{event.from_user.username}" != PRIMARY_ADMIN_USERNAME:
            log(f"Пользователь @{event.from_user.username} попытался выполнить команду для главного админа.")
            await event.answer("эта команда только для главного дундука")
            return
            
        return await handler(event, data)


class ChatMemberCheckMiddleware(BaseMiddleware):
    """
    Мидлварь для проверки, что пользователь является участником основного чата.
    """
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Пропускаем, если нет пользователя (например, для channel post)
        if not event.from_user or not event.from_user.username:
            return await handler(event, data)

        # Пропускаем личные сообщения для команды /у
        if event.chat.type == "private" and event.text and event.text.startswith("/у"):
             return await handler(event, data)

        # Выполняем проверку
        is_member = await check_chat_membership(
            bot=data.get('bot'), 
            user_id=event.from_user.id, 
            username=f"@{event.from_user.username}"
        )
        
        if not is_member:
            log(f"Пользователь @{event.from_user.username} не является участником чата. Доступ отклонен.")
            # Можно отправить сообщение пользователю, но лучше просто игнорировать
            return

        return await handler(event, data)


class AdminCheckMiddleware(BaseMiddleware):
    """
    Мидлварь для проверки, является ли пользователь администратором.
    Срабатывает только если у хендлера есть флаг "admin_check": True.
    """
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем наличие флага в хендлере
        if not data.get("admin_check"):
            return await handler(event, data)

        # Пропускаем, если нет пользователя
        if not event.from_user or not event.from_user.username:
            return

        # Выполняем проверку
        if not db.is_admin(event.from_user.username):
            log(f"Пользователь @{event.from_user.username} попытался выполнить админ-команду.")
            await event.answer("(▀ Ĺ̯▀   ) это было слишком самоуверено")
            return
            
        return await handler(event, data)
