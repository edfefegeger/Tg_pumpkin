import os
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, DeleteChannelRequest
from telethon.tl.functions.messages import StartBotRequest
from telethon.tl.types import ChatAdminRights
from urllib.parse import urlparse, parse_qs

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
channel_username = "@pumpfun_migration"
admin_username = "@safeguard"  

session_file = "my_session"

client = TelegramClient(session_file, api_id, api_hash)
bot_started = False
token_pattern = re.compile(r"([A-Za-z0-9]{34,})")


async def delete_old_groups():
    # Получаем все каналы, к которым есть доступ
    all_chats = await client.get_dialogs()

    # Фильтруем только группы (каналы)
    groups = [chat for chat in all_chats if chat.is_group]
    group_count = len(groups)

    print(f"Всего групп на аккаунте: {group_count}")

    # Если групп больше 100, удаляем старые
    if group_count > 100:
        groups_to_delete = groups[:group_count - 100]  # Удаляем все группы, которые больше лимита

        for group in groups_to_delete:
            try:
                await client(DeleteChannelRequest(group.id))  # Удаляем канал по ID
                print(f"Группа {group.title} удалена.")
            except Exception as e:
                print(f"Ошибка при удалении группы {group.title}: {e}")
    else:
        print("Групп на аккаунте меньше 100, удаление не требуется.")


processed_chats = set()  # Множество для хранения ID обработанных чатов

async def main():
    await client.connect()

    if not await client.is_user_authorized():
        print("Сессия не авторизована! Войдите в аккаунт вручную.")
        await client.disconnect()
        return

    # Проверяем и удаляем старые группы перед основной логикой
    await delete_old_groups()

    @client.on(events.NewMessage(chats=channel_username))
    async def new_message_handler(event):
        global bot_started
        message_text = event.text.strip()
        chat_id = event.chat.id  # Получаем ID чата
        print(f"Новое сообщение в {channel_username}: {message_text}")

        # Если чат уже обработан, пропускаем его
        if chat_id in processed_chats:
            print(f"Чат {chat_id} уже обработан, пропускаем.")
            return

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
                


        except Exception as e:
            print(f"Ошибка при создании группы или добавлении админа: {e}")

    print("Бот запущен и слушает новые сообщения...")
    await client.run_until_disconnected()

# Запуск
with client:
    client.loop.run_until_complete(main())



