import os
from datetime import datetime
from config import LOG_FILE

# логгирование
def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    
    try:
        # Убедимся, что директория существует
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (PermissionError, Exception):
        pass
    
    # Пишем в stdout (для journalctl)
    print(line)
