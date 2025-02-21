import os
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest
from telethon.tl.functions.messages import StartBotRequest
from telethon.tl.types import ChatAdminRights
from urllib.parse import urlparse, parse_qs

# Загружаем переменные из .env
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
channel_username = "@pumpfun_migration"
admin_username = "@safeguard"  # Кого добавлять в админы

# Используем существующую сессию
session_file = "my_session2"

client = TelegramClient(session_file, api_id, api_hash)

# Флаг для отслеживания запуска бота
bot_started = False

# Регулярное выражение для поиска токен-адреса
token_pattern = re.compile(r"([A-Za-z0-9]{34,})")


async def main():
    await client.connect()

    if not await client.is_user_authorized():
        print("Сессия не авторизована! Войдите в аккаунт вручную.")
        await client.disconnect()
        return

    @client.on(events.NewMessage(chats=channel_username))
    async def new_message_handler(event):
        global bot_started
        message_text = event.text.strip()
        print(f"Новое сообщение в {channel_username}: {message_text}")

        if not message_text:
            print("Сообщение пустое, пропускаем...")
            return

        # Попытка извлечь токен из сообщения
        token_match = token_pattern.search(message_text)
        if token_match:
            token_address = token_match.group(1)
            print(f"Найден токен: {token_address}")
        else:
            print("Токен не найден.")

        # 1️⃣ Создаем группу
        try:
            result = await client(CreateChannelRequest(
                title=message_text[:30],
                about="Automatic created group",
                megagroup=True
            ))
            group = result.chats[0]
            group_id = group.id
            print(f"Группа '{message_text[:30]}' создана! ID: {group_id}")

            # 2️⃣ Ищем пользователя @safeguard
            admin = await client.get_entity(admin_username)

            # 3️⃣ Назначаем @safeguard админом
            rights = ChatAdminRights(
                change_info=True, post_messages=True, edit_messages=True,
                delete_messages=True, ban_users=True, invite_users=True,
                pin_messages=True, add_admins=True, anonymous=False,
                manage_call=True
            )

            await client(EditAdminRequest(
                channel=group,  # Передаём объект группы
                user_id=admin.id,
                admin_rights=rights,
                rank="Admin"
            ))

            print(f"Пользователь {admin_username} назначен админом в группе!")

            # 4️⃣ Отправляем сообщение в группу
            await client.send_message(group, "/add@safeguard")
            print("Сообщение '/add@safeguard' отправлено в группу!")

            # 5️⃣ Отслеживаем ответное сообщение после "/add@safeguard"
            @client.on(events.NewMessage(chats=group))
            async def response_handler(event):
                global bot_started
                if bot_started:
                    return  # Уже обработано, пропускаем

                response_text = event.text.strip()
                sender = await event.get_sender()
                sender_name = sender.username if sender.username else sender.first_name
                message_id = event.id
                date = event.date

                print("📥 Новое сообщение в группе:")
                print(f"- Отправитель: {sender_name}")
                print(f"- Текст: {response_text}")
                print(f"- ID сообщения: {message_id}")
                print(f"- Время отправки: {date}")

                # Проверяем наличие кнопок в сообщении
                if event.buttons:
                    print("🔘 Обнаружены кнопки в сообщении:")
                    for row in event.buttons:
                        for button in row:
                            button_text = button.text
                            button_url = button.url if hasattr(button, 'url') else 'Нет URL'
                            print(f"  - Текст кнопки: {button_text}")
                            print(f"  - URL кнопки: {button_url}")

                            # Если у кнопки есть URL, обрабатываем его
                            if button_url != 'Нет URL':
                                # Парсим URL, чтобы извлечь параметры
                                parsed_url = urlparse(button_url)
                                query_params = parse_qs(parsed_url.query)
                                
                                # Извлекаем имя бота и параметр start
                                bot_username = parsed_url.path.lstrip('/')
                                start_param = query_params.get('start', [None])[0]

                                if bot_username and start_param:
                                    print(f"Запускаем бота @{bot_username} с параметром {start_param}")
                                    # Отправляем StartBotRequest
                                    await client(StartBotRequest(
                                        bot=bot_username,
                                        peer=bot_username,
                                        start_param=start_param
                                    ))

                                    bot_started = True  # Устанавливаем флаг, что бот запущен

                                    @client.on(events.NewMessage(from_users=bot_username))
                                    async def bot_message_handler(event):
                                        # Проверяем наличие кнопок в сообщении
                                        if event.buttons:
                                            # Получаем все кнопки
                                            buttons = event.buttons
                                            # Проверяем, есть ли хотя бы две кнопки
                                            if len(buttons) > 1:
                                                # Нажимаем на вторую кнопку (индекс 1)
                                                await event.click(1)
                                                print("Нажата вторая кнопка.")
                                    
                                                # После нажатия на кнопку, отправляем токен
                                                if token_address:  # Если токен найден
                                                    try:
                                                        # Отправляем токен в чат с ботом
                                                        await client.send_message(bot_username, token_address)
                                                        print(f"Токен {token_address} отправлен боту.")
                                                    except Exception as e:
                                                        print(f"Ошибка при отправке токена: {e}")
                                                else:
                                                    print("Токен не найден.")
                                            else:
                                                print("В сообщении недостаточно кнопок.")

                                else:
                                    print("Не удалось извлечь имя бота или параметр start из URL.")
                else:
                    print("Кнопки в сообщении отсутствуют.")

        except Exception as e:
            print(f"Ошибка при создании группы или добавлении админа: {e}")

    print("Бот запущен и слушает новые сообщения...")
    await client.run_until_disconnected()

# Запуск
with client:
    client.loop.run_until_complete(main())
