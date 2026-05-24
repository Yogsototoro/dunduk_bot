import os
import psutil
import subprocess
import json
import asyncio
import aiohttp
import tarfile
from urllib.parse import quote
from datetime import datetime
from aiogram import types, Bot
from aiogram.types import FSInputFile, URLInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import PRIMARY_ADMIN_USERNAME
from database_sqlite import db
from keyboards import get_marzban_menu, get_user_selection_keyboard

MARZBAN_API_URL = "http://127.0.0.1:8000/api"
MARZBAN_ADMIN = {"username": "ayd", "password": "barkerabaykaprobaykeraibabayku"}
SUB_URL_PREFIX = "http://64.188.72.234:8000"

class VPNStates(StatesGroup):
    waiting_for_name = State()

async def get_marzban_token():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{MARZBAN_API_URL}/admin/token", data=MARZBAN_ADMIN) as resp:
                data = await resp.json()
                return data.get("access_token")
        except Exception: return None

async def cmd_help(message: types.Message):
    """Максимально подробная инструкция."""
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    h = (
        "<b>🚀 ПОЛНОЕ РУКОВОДСТВО АДМИНИСТРАТОРА</b>\n\n"
        "<b>🏠 УПРАВЛЕНИЕ МЕСОМ (СОБЫТИЯ):</b>\n"
        "• <code>+</code> / <code>-</code> — Записаться / Выписаться.\n"
        "• <code>?</code> — Текущий список участников.\n"
        "• <code>/атмена</code> — Отмена мероприятия (арт).\n"
        "• <code>/о</code> — Полная очистка списка.\n"
        "• <code>/ь [ник]</code> — Удалить юзера из списка.\n"
        "• <code>/локация [текст]</code> — Место встречи.\n"
        "• <code>/расписание [0010011]</code> — Настройка дней.\n"
        "• <code>/ограничение [число]</code> — Лимит мест.\n\n"
        "<b>💻 МОНИТОРИНГ СЕРВЕРА (VDS):</b>\n"
        "• <b>📊 Статистика</b> — Глубокий текстовый отчет.\n"
        "• <b>📈 График</b> — Аналитика нагрузки (Альбом).\n"
        "• <b>🔝 Топ</b> — Самые тяжелые процессы по RAM.\n"
        "• <b>🛡 Безопасность</b> — Детальный отчет об атаках.\n\n"
        "<b>🔧 УПРАВЛЕНИЕ VPN (MARZBAN):</b>\n"
        "• <b>Меню</b> — Кнопка '🔧 VPN Настройка'.\n"
        "• <code>/vadd [имя]</code> — Создать юзера.\n"
        "• <code>/vget [имя]</code> — Ссылка и QR.\n"
        "• <code>/vdel [имя]</code> — Удалить юзера.\n\n"
        "<b>💾 СЕРВИС:</b>\n"
        "• <b>💾 Бэкап бота</b> — Архив кода и БД.\n"
        "• <b>🔄 Рестарт бота</b> — Перезагрузка службы.\n"
        "• <code>/sh [cmd]</code> — Терминал (bash)."
    )
    await message.answer(h)

async def cmd_security(message: types.Message):
    """Расширенный отчет по безопасности со счетчиками."""
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    
    # Статистика из БД
    stats_db = db._execute("SELECT COUNT(*), SUM(count) FROM ssh_attacks").fetchone()
    unique_ips = stats_db[0] if stats_db else 0
    total_hits = stats_db[1] if stats_db[1] else 0
    
    # Статистика Fail2Ban
    banned = subprocess.getoutput("fail2ban-client status sshd | grep 'Banned IP list' | cut -d: -f2").strip()
    failed_today = subprocess.getoutput("journalctl -u ssh --since today | grep 'Failed password' | wc -l")
    
    msg = (f"🛡 <b>SSH SECURITY INTELLIGENCE</b>\n"
           f"<code>────────────────────</code>\n"
           f"🔢 <b>Атак за сегодня:</b> <code>{failed_today}</code>\n"
           f"💀 <b>Всего атак в базе:</b> <code>{total_hits}</code>\n"
           f"👤 <b>Уникальных хостов:</b> <code>{unique_ips}</code>\n"
           f"<code>────────────────────</code>\n"
           f"🚫 <b>АКТИВНЫЙ БАН-ЛИСТ:</b>\n<code>{banned if banned else 'Empty'}</code>\n"
           f"<code>────────────────────</code>\n"
           f"👮 <b>Fail2Ban Mitigation:</b> 🟢 Active")
    await message.answer(msg)

async def cmd_stats(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    cpu = psutil.cpu_percent(); ram = psutil.virtual_memory(); disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    msg = f"""📊 <b>VDS LIVE STATUS</b>
<code>────────────────────</code>
🖥 <b>CPU:</b> <code>{cpu}%</code>
💾 <b>RAM:</b> <code>{ram.percent}%</code> ({ram.used//1024**2}MB)
💽 <b>Disk:</b> <code>{disk.percent}%</code>
🌐 <b>Net:</b> ↓<code>{round(net.bytes_recv/1024**3, 1)}G</code> ↑<code>{round(net.bytes_sent/1024**3, 1)}G</code>
<code>────────────────────</code>
⏱ <b>UP:</b> <code>{subprocess.getoutput('uptime -p').replace('up ', '')}</code>"""
    await message.answer(msg)

async def cmd_chart(message: types.Message, bot: Bot):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    await bot.send_chat_action(message.chat.id, "upload_photo")
    try:
        cursor = db._execute("SELECT * FROM system_stats ORDER BY timestamp DESC LIMIT 40")
        rows = cursor.fetchall()
        if not rows or len(rows) < 3: return await message.answer("🕒 Мало данных.")
        rows = rows[::-1]
        labels = [datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M') for r in rows][1:]
        cpu = [r['cpu_usage'] for r in rows][1:]
        ram = [r['ram_usage'] for r in rows][1:]
        net_rx = []
        for i in range(1, len(rows)):
            curr = rows[i]['net_rx'] or 0; prev = rows[i-1]['net_rx'] or 0
            net_rx.append(round(max(0, (curr - prev) / 1024 / 1024), 2))

        def get_url(title, datasets, y_max=None):
            cfg = {"type":"line","data":{"labels":labels,"datasets":datasets},"options":{"title":{"display":True,"text":title,"fontColor":"#fff"},"scales":{"yAxes":[{"ticks":{"min":0,"max":y_max}}]}}}
            return f"https://quickchart.io/chart?bkg=rgb(20,20,25)&c={quote(json.dumps(cfg))}&w=800&h=400"

        u1 = get_url("Load %", [{"label":"CPU","data":cpu,"borderColor":"red","fill":True},{"label":"RAM","data":ram,"borderColor":"blue","fill":False}], 100)
        u2 = get_url("Traffic MB", [{"label":"Down","data":net_rx,"borderColor":"purple","fill":False}])
        await message.answer_media_group([InputMediaPhoto(media=URLInputFile(u1), caption="📈 Resources"), InputMediaPhoto(media=URLInputFile(u2), caption="🚀 Network")])
    except Exception as e: await message.answer(f"❌ Error: {e}")

async def vpn_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    t = await get_marzban_token(); h = {"Authorization": f"Bearer {t}"}
    if callback.data == "vpn_status":
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{MARZBAN_API_URL}/users", headers=h) as r:
                d = await r.json(); total = d.get('total', 0); active = len([u for u in d.get('users', []) if u['status']=='active'])
                await callback.message.edit_text(f"📊 <b>VPN Status</b>\nTotal: <code>{total}</code>\nActive: <code>{active}</code>", reply_markup=get_marzban_menu())
    elif callback.data == "vpn_users":
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{MARZBAN_API_URL}/users?sort=-used_traffic&limit=10", headers=h) as r:
                d = await r.json(); list_u = "\n".join([f"• <code>{u['username']}</code>: {round(u['used_traffic']/1024**3, 1)} GB" for u in d.get('users', [])])
                await callback.message.edit_text(f"👥 <b>Top 10</b>\n\n{list_u}", reply_markup=get_marzban_menu())
    elif callback.data == "vpn_add_start":
        await callback.message.answer("⌨️ Введите имя юзера:"); await state.set_state(VPNStates.waiting_for_name)
    elif callback.data in ["vpn_del_list", "vpn_get_list"]:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{MARZBAN_API_URL}/users", headers=h) as r:
                names = sorted([u['username'] for u in (await r.json()).get('users', [])])
                await callback.message.edit_text("👤 Выберите юзера:", reply_markup=get_user_selection_keyboard(names, "vpndel" if "del" in callback.data else "vpnget"))
    elif callback.data.startswith("vpndel:"):
        n = callback.data.split(":")[1]
        async with aiohttp.ClientSession() as s:
            await s.delete(f"{MARZBAN_API_URL}/user/{n}", headers=h)
            await callback.message.answer(f"🗑 Юзер <code>{n}</code> удален.")
            await callback.message.delete()
    elif callback.data.startswith("vpnget:"):
        n = callback.data.split(":")[1]
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{MARZBAN_API_URL}/user/{n}", headers=h) as r:
                await send_vpn_info(callback.message, await r.json())
    elif callback.data == "vpn_back": await callback.message.edit_text("🔧 <b>VPN Panel</b>", reply_markup=get_marzban_menu())
    elif callback.data == "vpn_close": await callback.message.delete()
    await callback.answer()

async def cmd_top(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    p = sorted([p.info for p in psutil.process_iter(['name', 'memory_percent'])], key=lambda x: x['memory_percent'], reverse=True)[:7]
    res = "\n".join([f"• <code>{x['name'][:15]}</code>: <b>{x['memory_percent']:.1f}%</b>" for x in p])
    await message.answer(f"🔝 <b>ТОП-7 ПРОЦЕССОВ ПО RAM:</b>\n\n{res}")

async def cmd_backup(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    await message.answer("⏳ Создаю бэкап...")
    name = f"backup_{datetime.now().strftime('%Y%m%d')}.tar.gz"
    try:
        with tarfile.open(name, "w:gz") as tar:
            for root, dirs, files in os.walk("/root/dunduk_bot"):
                if any(x in root for x in ['venv', '__pycache__']): continue
                for f in files: tar.add(os.path.join(root, f), arcname=os.path.relpath(os.path.join(root, f), "/root/dunduk_bot"))
        await message.answer_document(FSInputFile(name)); os.remove(name)
    except Exception as e: await message.answer(f"❌ Error: {e}")

async def send_vpn_info(message: types.Message, user_data: dict):
    u = user_data.get('username'); link = user_data.get('links', [''])[0]; sub = f"{SUB_URL_PREFIX}{user_data.get('subscription_url')}"
    qr = f"https://api.qrserver.com/v1/create-qr-code/?size=400x400&data={quote(link)}"
    await message.answer_photo(URLInputFile(qr), caption=f"👤 <code>{u}</code>\n🔑 <code>{link}</code>")

async def process_vpn_add_name(message: types.Message, state: FSMContext):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    name = message.text.strip(); await state.clear(); t = await get_marzban_token(); h = {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}
    p = {"username": name, "proxies": {"vless": {"flow": "xtls-rprx-vision"}}, "inbounds": {"vless": ["VLESS TCP REALITY"]}}
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{MARZBAN_API_URL}/user", json=p, headers=h) as r:
            if r.status == 200: await message.answer(f"✅ Создан {name}"); await send_vpn_info(message, await r.json())
            else: await message.answer(f"❌ Ошибка: {await r.text()}")

async def cmd_vpn_settings(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    await message.answer("🔧 <b>VPN Panel</b>", reply_markup=get_marzban_menu())

async def cmd_restart_bot(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    await message.answer("🔄 Restarting..."); os.system("systemctl restart dunduk-bot.service")

async def cmd_sh(message: types.Message):
    if message.from_user.username != PRIMARY_ADMIN_USERNAME.replace('@', ''): return
    res = subprocess.getoutput(message.text.replace('/sh ', ''))
    await message.answer(f"<pre>{res[:4000]}</pre>")

async def handle_document(message: types.Message, bot: Bot): pass
