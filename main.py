import os
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest
from telethon.tl.functions.messages import StartBotRequest
from telethon.tl.types import ChatAdminRights
from urllib.parse import urlparse, parse_qs

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
channel_username = "@pumpkin128"
admin_username = "@safeguard"  

session_file = "my_session2"

client = TelegramClient(session_file, api_id, api_hash)

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
                channel=group,  
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
                    return 
                sender = await event.get_sender()
                if event.buttons:
                    print("🔘 Обнаружены кнопки в сообщении:")
                    for row in event.buttons:
                        for button in row:
                            button_text = button.text
                            button_url = button.url if hasattr(button, 'url') else 'Нет URL'
                            print(f"  - Текст кнопки: {button_text}")
                            print(f"  - URL кнопки: {button_url}")

                            if button_url != 'Нет URL':
                                parsed_url = urlparse(button_url)
                                query_params = parse_qs(parsed_url.query)
                                
                                bot_username = parsed_url.path.lstrip('/')
                                start_param = query_params.get('start', [None])[0]

                                if bot_username and start_param:
                                    print(f"Запускаем бота @{bot_username} с параметром {start_param}")
                                    await client(StartBotRequest(
                                        bot=bot_username,
                                        peer=bot_username,
                                        start_param=start_param
                                    ))
                                    user_token_count = {}
                                    user_button_clicks = {}
                                    MAX_TOKENS = 1
                                    MAX_CLICKS = 1

                                    @client.on(events.NewMessage(from_users=bot_username))
                                    async def bot_message_handler(event):
                                        user_id = event.sender_id 

                                        if user_id not in user_token_count:
                                            user_token_count[user_id] = 0
                                        if user_id not in user_button_clicks:
                                            user_button_clicks[user_id] = 0

                                        if event.buttons:
   
                                            if len(event.buttons) > 1 and user_button_clicks[user_id] < MAX_CLICKS:
                                                await event.click(1)  
                                                user_button_clicks[user_id] += 1
                                                print(f"Нажата вторая кнопка. Нажатий: {user_button_clicks[user_id]}")

                                                if token_address and user_token_count[user_id] < MAX_TOKENS: 
                                                    try:
                                                        await client.send_message(bot_username, token_address)
                                                        user_token_count[user_id] += 1 
                                                        print(f"Токен {token_address} отправлен боту. Отправок: {user_token_count[user_id]}")
                                                    except Exception as e:
                                                        print(f"Ошибка при отправке токена: {e}")
                                                else:
                                                    print("Токен не найден или лимит отправок превышен.")

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