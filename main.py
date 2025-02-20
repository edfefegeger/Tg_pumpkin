import os
from dotenv import load_dotenv
from telethon import TelegramClient, events

# Загружаем переменные из .env
load_dotenv()

# Получаем данные
api_id = int(os.getenv("API_ID"))  # Переводим в int
api_hash = os.getenv("API_HASH")
channel_username = "@pumpfun_migration"  # Канал для отслеживания

# Подключаемся к Telegram
client = TelegramClient("my_session", api_id, api_hash)

@client.on(events.NewMessage(chats=channel_username))
async def new_message_handler(event):
    print(f"Новое сообщение в {channel_username}: {event.text}")

# Запуск
client.start()
client.run_until_disconnected()
