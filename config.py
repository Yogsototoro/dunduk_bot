import os
from dotenv import load_dotenv

load_dotenv()

# настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", 0)
ADMIN_USERNAMES = {"@yogsototoro"} 
PRIMARY_ADMIN_USERNAME = os.getenv("PRIMARY_ADMIN_USERNAME", "@yogsototoro")

# пути
DATA_DIR = "./data"
LOGS_DIR = "./logs"
LOG_FILE = f"{LOGS_DIR}/bot.log"

# время меса (UTC)
TIMEZONE_OFFSET = 3
MECE_HOUR = 16
MECE_END_HOUR = 19
MECE_MINUTE = 0

# время напоминания
REMINDER_HOUR = 9
REMINDER_MINUTE = 0
REMINDER_INTERVAL = 600

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Настройки Web-панели
WEB_PANEL_URL = "https://specially-width-cycle-eden.trycloudflare.com"
PANEL_TOKEN = "72636e898132f30a94f4c6d3e686fd93"
MARZBAN_WEB_URL = "https://south-brisbane-marina-regard.trycloudflare.com"
