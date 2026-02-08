import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.redis import RedisStorage

# --- Загружаем переменные окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
REDIS_URL = os.getenv("REDIS_URL")

# --- Настройка FSM через Redis (если нужно) ---
storage = RedisStorage.from_url(REDIS_URL) if REDIS_URL else None
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# --- Обработчик фото с подписью (в одной подписи: название, описание, ссылка) ---
@dp.message()
async def handle_product_photo(message: types.Message):
    if not message.photo:
        return  # Игнорируем не-фото сообщения

    if not message.caption:
        await message.reply("Братанчик, подпись к фото нужна: Название, Описание, Ссылка!")
        return

    lines = message.caption.split("\n")
    if len(lines) < 3:
        await message.reply("Братанчик, подпись должна содержать 3 строки: Название, Описание, Ссылка!")
        return

    title = lines[0].replace("Название: ", "").strip()
    description = lines[1].replace("Описание: ", "").strip()
    ref_link = lines[2].replace("Ссылка: ", "").strip()

    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="Подивитись та купити", url=ref_link)
    )

    photo = message.photo[-1].file_id  # берём самое большое фото

    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo,
        caption=f"{title}\n{description}",
        reply_markup=keyboard
    )

    await message.reply("✅ Товар отправлен в канал!")

# --- Запуск бота через asyncio.run ---
async def main():
    print("Братанчик, бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
