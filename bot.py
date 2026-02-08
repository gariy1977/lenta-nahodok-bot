import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.redis import RedisStorage2

# --- Загружаем переменные из окружения ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
REDIS_URL = os.getenv("REDIS_URL")

# --- Настройка бота и хранилища FSM ---
storage = RedisStorage2.from_url(REDIS_URL) if REDIS_URL else None
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# --- Обработчик фото с подписью (в одной подписи: название, описание, ссылка) ---
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_product_photo(message: types.Message):
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

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="Подивитись та купити", url=ref_link))

    photo = message.photo[-1].file_id  # берём самое большое фото

    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo,
        caption=f"{title}\n{description}",
        reply_markup=keyboard
    )

    await message.reply("✅ Товар отправлен в канал!")

# --- Запуск бота через polling ---
if __name__ == "__main__":
    print("Братанчик, бот запускается...")
    executor.start_polling(dp, skip_updates=True)
