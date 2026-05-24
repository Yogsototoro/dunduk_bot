from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_reply_keyboard(is_admin=False):
    user_row = [types.KeyboardButton(text="+"), types.KeyboardButton(text="-"), types.KeyboardButton(text="?")]
    if not is_admin: return types.ReplyKeyboardMarkup(keyboard=[user_row], resize_keyboard=True)
    
    from config import WEB_PANEL_URL, PANEL_TOKEN, MARZBAN_WEB_URL
    
    # Наша панель
    panel_url = WEB_PANEL_URL + "?token=" + PANEL_TOKEN
    
    # Marzban Dashboard со слешем в конце (критично для корректной загрузки ресурсов)
    marzban_url = MARZBAN_WEB_URL.rstrip('/') + "/dashboard/"
    
    admin_keyboard = [
        [
            types.KeyboardButton(text="🖥 Панель управления", web_app=types.WebAppInfo(url=panel_url)),
            types.KeyboardButton(text="🌐 Marzban VPN", web_app=types.WebAppInfo(url=marzban_url))
        ],
        [types.KeyboardButton(text="📊 Статистика"), types.KeyboardButton(text="📈 График"), types.KeyboardButton(text="🔝 Топ")],
        [types.KeyboardButton(text="🛡 Безопасность"), types.KeyboardButton(text="🔧 VPN Настройка"), types.KeyboardButton(text="💾 Бэкап бота")],
        [types.KeyboardButton(text="🤖 Помощь"), types.KeyboardButton(text="🔄 Рестарт бота")],
        user_row
    ]
    return types.ReplyKeyboardMarkup(keyboard=admin_keyboard, resize_keyboard=True)

def get_marzban_menu():
    buttons = [
        [types.InlineKeyboardButton(text="📊 Статус", callback_data="vpn_status"), types.InlineKeyboardButton(text="🔍 Инфо / QR", callback_data="vpn_get_list")],
        [types.InlineKeyboardButton(text="➕ Добавить", callback_data="vpn_add_start"), types.InlineKeyboardButton(text="🗑 Удалить", callback_data="vpn_del_list")],
        [types.InlineKeyboardButton(text="👥 Топ Трафик", callback_data="vpn_users"), types.InlineKeyboardButton(text="🔄 Рестарт", callback_data="vpn_restart")],
        [types.InlineKeyboardButton(text="❌ Закрыть", callback_data="vpn_close")]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_selection_keyboard(users, action_prefix):
    builder = InlineKeyboardBuilder()
    for user in users: builder.button(text=user, callback_data=action_prefix + ":" + user)
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="vpn_back"))
    return builder.as_markup()
