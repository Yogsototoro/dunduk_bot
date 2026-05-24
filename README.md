# dunduk bot версийа 0.000004007012

```
dunduk_bot/
├── bot.py                # Точка входа, регистрация хендлеров
├── config.py             # Настройки и конфигурация
├── database.py           # Работа с данными (JSON файлы)
├── utils.py              # Вспомогательные функции
├── keyboards.py          # Клавиатуры и кнопки
├── reminders.py          # Фоновые задачи (напоминания)
├── handlers/             # Обработчики команд
│   ├── user_handlers.py
│   ├── admin_handlers.py
│   └── callback_handlers.py
├── data/                 # Данные (создаются автоматически)
│   ├── msr_data.json
│   └── msr_list.json
└── logs/                 # Логи (создаются автоматически)
    └── bot.log
```

#### Для взееех:
- `+` — зопийсаца
- `-` — удолица
- `?` — пасматредь

#### Для аддмена:
- `/атмена` — атмена/ниатмена `mece`
- `/штошшшшшшшшшшшшшшшш @ник` — расдундуковывовать
- `/ь @ник` — удолть

#### Асобеннасти:

- напаминания пирид `mece`
- дундуковатость
- ззззззхзззззззххх

#### 🛠 Ностройкка

1. Устонавить зовисемости:
```bash
pip install -r requirements.txt
```
2. Саздац .env фаел:
```bash
BOT_TOKEN=ваш_токен
REMINDER_CHAT_ID=ID_чата_для_напоминаний
```

#### 🛠 Ностройгка systemd длья dunduk_bot
3. Сазсдай фаел сервеса:
```bash
sudo nano /etc/systemd/system/dunduk-bot.service
```
4. Дабавь садиржимае:
```bash
[Unit]
Description=Dunduk Bot
After=network.target

[Service]
Type=simple
User=ayd
WorkingDirectory=/home/ayd/dunduk_bot
ExecStart=/usr/bin/python3 /home/ayd/dunduk_bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

5. Зопузти сервес:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dunduk-bot
sudo systemctl start dunduk-bot
```

6. Праверь зтатуз:
```bash
sudo systemctl status dunduk-bot
```

7. Палезные каманды:
```bash
# Прасмотар логовб
sudo journalctl -u dunduk-bot -f

# Пиризапузг бота
sudo systemctl restart dunduk-bot

# Астановка бота
sudo systemctl stop dunduk-bot

# Прасмотр статуза
sudo systemctl status dunduk-bot

# Проверить, включен ли автозапуск
sudo systemctl is-enabled dunduk-bot

# Проверить статус
sudo systemctl status dunduk-bot

# Перезагрузить систему и проверить
sudo reboot
```