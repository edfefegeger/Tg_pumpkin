import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import CreateChannelRequest
from telethon.tl.functions.messages import EditChatAdminRequest
from telethon.tl.types import ChatAdminRights

# Загружаем переменные из .env
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
channel_username = "@pumpfun_migration"
admin_username = "@safeguard"  # Кого добавлять в админы

# Используем существующую сессию
session_file = "my_session"

client = TelegramClient(session_file, api_id, api_hash)

async def main():
    await client.connect()
    
    if not await client.is_user_authorized():
        print("Сессия не авторизована! Войдите в аккаунт вручную.")
        await client.disconnect()
        return

    @client.on(events.NewMessage(chats=channel_username))
    async def new_message_handler(event):
        message_text = event.text.strip()
        print(f"Новое сообщение в {channel_username}: {message_text}")

        if not message_text:
            print("Сообщение пустое, пропускаем...")
            return

        # 1️⃣ Создаем группу
        try:
            result = await client(CreateChannelRequest(
                title=message_text[:30],
                about="Автоматически созданная группа",
                megagroup=True
            ))
            group_id = result.chats[0].id
            print(f"Группа '{message_text[:30]}' создана! ID: {group_id}")

            # 2️⃣ Ищем пользователя @safeguard
            admin = await client.get_entity(admin_username)

            # 3️⃣ Назначаем @safeguard админом
            await client(EditChatAdminRequest(
                chat_id=group_id,
                user_id=admin.id,
                is_admin=True,
                admin_rights=ChatAdminRights(
                    change_info=True, post_messages=True, edit_messages=True,
                    delete_messages=True, ban_users=True, invite_users=True,
                    pin_messages=True, add_admins=True, anonymous=False,
                    manage_call=True
                )
            ))

            print(f"Пользователь {admin_username} назначен админом в группе!")

        except Exception as e:
            print(f"Ошибка при создании группы или добавлении админа: {e}")

    print("Бот запущен и слушает новые сообщения...")
    await client.run_until_disconnected()

# Запуск
with client:
    client.loop.run_until_complete(main())
