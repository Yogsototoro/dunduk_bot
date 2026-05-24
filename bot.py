import asyncio
import psutil
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from datetime import datetime
import re

# Импорты
from config import BOT_TOKEN, ADMIN_USERNAMES
from logger import log
from reminders import reminder_task, cat_meme_task
from security_monitor import monitor_auth_log
from database_sqlite import db
from middlewares import ChatMemberCheckMiddleware, AdminCheckMiddleware, PrimaryAdminCheckMiddleware

# Хендлеры
from handlers.user_handlers import start, show_list, add_user, remove_user
from handlers.admin_system_handlers import (
    cmd_stats, cmd_security, cmd_sh, cmd_help, cmd_chart,
    cmd_top, cmd_restart_bot, cmd_vpn_settings, 
    vpn_callback_handler, process_vpn_add_name, VPNStates, cmd_backup, handle_document
)

async def log_stats():
    psutil.cpu_percent(interval=None)
    await asyncio.sleep(1)
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1.0)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            net = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            db._execute("""
                INSERT INTO system_stats (timestamp, cpu_usage, ram_usage, disk_usage, net_rx, net_tx, disk_read, disk_write) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, cpu, ram, disk, net.bytes_recv, net.bytes_sent, disk_io.read_bytes, disk_io.write_bytes), commit=True)

            # --- Port Stats ---
            ports_count = {}
            # Filter for meaningful ports (listen or > 1 conns)
            listening_ports = {c.laddr.port for c in psutil.net_connections(kind="inet") if c.status == "LISTEN"}
            ports_count = {}
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "ESTABLISHED" and conn.laddr.port:
                    port = conn.laddr.port
                    if port in listening_ports or port in [22, 8080, 8000, 2040]:
                        ports_count[port] = ports_count.get(port, 0) + 1
                if conn.status == "ESTABLISHED" and conn.laddr.port:
                    ports_count[conn.laddr.port] = ports_count.get(conn.laddr.port, 0) + 1
            
            for port, count in ports_count.items():
                db._execute("INSERT INTO port_stats (timestamp, port, connections) VALUES (?, ?, ?)", (now, port, count), commit=True)
                
        except Exception as e:
            log(f"Ошибка логирования: {e}")
        await asyncio.sleep(899)

async def main():
    if not BOT_TOKEN: return
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=MemoryStorage()); db.create_tables()

    dp.message.middleware(ChatMemberCheckMiddleware())
    dp.message.middleware(AdminCheckMiddleware())
    dp.message.middleware(PrimaryAdminCheckMiddleware())

    # Регистрация
    dp.message.register(start, Command("start"))
    dp.message.register(cmd_help, F.text.in_({"🤖 Помощь", "/help"}))
    dp.message.register(show_list, F.text == "?")
    dp.message.register(add_user, F.text == "+")
    dp.message.register(remove_user, F.text == "-")
    dp.message.register(cmd_stats, F.text.in_({"📊 Статистика", "/stats"}))
    dp.message.register(cmd_chart, F.text.in_({"📈 График", "/chart"}))
    dp.message.register(cmd_top, F.text.in_({"🔝 Топ", "/top"}))
    dp.message.register(cmd_security, F.text.in_({"🛡 Безопасность", "/security"}))
    dp.message.register(cmd_backup, F.text.in_({"💾 Бэкап бота", "/backup"}))
    dp.message.register(cmd_restart_bot, F.text == "🔄 Рестарт бота")
    dp.message.register(cmd_vpn_settings, F.text.in_({"🔧 VPN Настройка", "/vpn"}))
    
    dp.message.register(process_vpn_add_name, StateFilter(VPNStates.waiting_for_name))
    dp.callback_query.register(vpn_callback_handler, lambda c: c.data and (c.data.startswith("vpn") or c.data.startswith("vpndel") or c.data.startswith("vpnget")))
    dp.message.register(cmd_sh, lambda m: m.text and m.text.startswith("/sh "))
    dp.message.register(handle_document, F.document)

    # Админ хендлеры
    from handlers.admin_handlers import cmd_remove_user_admin, cmd_cancel_mece, cmd_clear_dunduk, cmd_clear_list, cmd_set_location, cmd_set_schedule, cmd_set_limit, debug_chat_id, cmd_list_admins
    admin_h = [(cmd_remove_user_admin, lambda m: m.text and m.text.startswith('/ь ')), (cmd_cancel_mece, Command("атмена")), (cmd_clear_dunduk, lambda m: m.text and re.match(r'^/штош+', m.text)), (cmd_clear_list, Command("о")), (cmd_set_location, Command("локация")), (cmd_set_schedule, Command("расписание")), (cmd_set_limit, Command("ограничение")), (debug_chat_id, Command("getchatid")), (cmd_list_admins, Command("list_admins"))]
    for h, *f in admin_h: dp.message.register(h, *f)

    try:
        asyncio.create_task(reminder_task(bot))
        asyncio.create_task(cat_meme_task(bot))
        asyncio.create_task(monitor_auth_log(bot))
        asyncio.create_task(log_stats())
        log("Бот ОЖИЛ")
        await dp.start_polling(bot)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
