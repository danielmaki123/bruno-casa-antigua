import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def get_ids():
    token = os.getenv("TELEGRAM_TOKEN")
    bot = Bot(token=token)
    print("--- Buscando mensajes en los grupos ---")
    
    updates = await bot.get_updates()
    found = False
    for update in updates:
        if update.message and update.message.chat:
            chat = update.message.chat
            if chat.type in ['group', 'supergroup']:
                print(f"[!] Grupo detectado: '{chat.title}' | ID: {chat.id}")
                found = True
    
    if not found:
        print("[-] No se encontraron mensajes nuevos. Asegúrate de que el bot esté en el grupo y hayas escrito algo RECIENTEMENTE.")

if __name__ == "__main__":
    asyncio.run(get_ids())
