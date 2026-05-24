#!/bin/bash
cd /root/dunduk_bot
pkill -9 -f web_panel_api.py
pkill -9 -f cloudflared
pkill -9 -f serveo

# 1. Запуск нашей API панели (8080)
/root/dunduk_bot/venv/bin/python3 web_panel_api.py > web_api.log 2>&1 &
sleep 2

# 2. Запуск туннеля для нашей панели
rm -f cf.log
nohup cloudflared tunnel --url http://localhost:8080 > cf.log 2>&1 &

# 3. Запуск туннеля для Marzban (8000)
rm -f cf_marzban.log
nohup cloudflared tunnel --url http://localhost:8000 > cf_marzban.log 2>&1 &

# 4. Ждем получения обоих URL
MAX_RETRIES=30
URL_PANEL=""
URL_MARZBAN=""

for i in $(seq 1 $MAX_RETRIES); do
    sleep 3
    if [ -z "$URL_PANEL" ]; then
        URL_PANEL=$(grep -o "https://[-a-z0-9.]*trycloudflare.com" cf.log | head -n 1)
    fi
    if [ -z "$URL_MARZBAN" ]; then
        URL_MARZBAN=$(grep -o "https://[-a-z0-9.]*trycloudflare.com" cf_marzban.log | head -n 1)
    fi
    
    if [ ! -z "$URL_PANEL" ] && [ ! -z "$URL_MARZBAN" ]; then
        echo "Panel URL: $URL_PANEL"
        echo "Marzban URL: $URL_MARZBAN"
        
        # Обновляем конфиг с кавычками
        sed -i "s|WEB_PANEL_URL = .*|WEB_PANEL_URL = \"$URL_PANEL\"|" /root/dunduk_bot/config.py
        sed -i "s|MARZBAN_WEB_URL = .*|MARZBAN_WEB_URL = \"$URL_MARZBAN\"|" /root/dunduk_bot/config.py
        
        # Жесткий рестарт бота
        pkill -9 -f bot.py
        systemctl stop dunduk-bot.service
        sleep 1
        systemctl start dunduk-bot.service
        
        echo "Bot restarted with both URLs"
        exit 0
    fi
done

echo "Failed to establish tunnels"
exit 1
