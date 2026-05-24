#!/bin/bash
cd /root/dunduk_bot
pkill -f web_panel_api.py
pkill -f "ssh -R"

# Запуск API
/root/dunduk_bot/venv/bin/python3 web_panel_api.py > web_api.log 2>&1 &
sleep 2

# Запуск туннеля с попыткой фиксации имени
rm -f serveo.log
ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R dunduk:80:localhost:8080 serveo.net > serveo.log 2>&1 &

# Ждем появления URL в логах
MAX_RETRIES=10
COUNT=0
URL=""

while [ $COUNT -lt $MAX_RETRIES ]; do
    sleep 3
    URL=$(grep -o "https://[a-zA-Z0-9.-]*\.serveo[a-z.-]*" serveo.log | head -n 1)
    if [ ! -z "$URL" ]; then
        echo "Found URL: $URL"
        # Обновляем конфиг бота
        sed -i "s|WEB_PANEL_URL = .*|WEB_PANEL_URL = \"$URL\"|" /root/dunduk_bot/config.py
        # Перезапускаем бота, чтобы обновить кнопку
        pkill -f bot.py
        nohup /root/dunduk_bot/venv/bin/python3 /root/dunduk_bot/bot.py > /root/dunduk_bot/logs/bot.log 2>&1 &
        break
    fi
    COUNT=$((COUNT+1))
done
