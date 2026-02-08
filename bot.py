import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== Функция отправки товара =====
async def send_product(channel_id: str, photo_bytes: bytes, description: str, referral_url: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=referral_url)]
    ])
    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_bytes,
        caption=description,
        reply_markup=keyboard
    )

# ===== Обработчик команд =====
@dp.message()
async def handle_message(message: types.Message):
    if message.photo:
        photo = await message.photo[-1].download(destination=bytes)
    elif message.document and message.document.mime_type.startswith("image/"):
        photo = await message.document.download(destination=bytes)
    else:
        await message.reply("Пришли картинку товара.")
        return

    if not message.caption or ";" not in message.caption:
        await message.reply("Подпись должна быть в формате: описание; ссылка")
        return

    description, referral_url = map(str.strip, message.caption.split(";", 1))
    await send_product(CHANNEL_ID, photo, description, referral_url)
    await message.reply("Товар отправлен в канал ✅")

# ===== Запуск бота =====
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
