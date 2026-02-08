import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.log import setup_logging

# ===== Настройки из env =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Например: "-1003571651319"

# ===== Инициализация бота =====
setup_logging(level="INFO")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== Функция публикации товара =====
async def send_product(channel_id: str, photo_bytes: bytes, description: str, referral_url: str):
    # Создаем кнопку с партнерской ссылкой
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=referral_url)]
    ])
    
    # Отправляем фото с подписью и кнопкой
    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_bytes,
        caption=description,
        reply_markup=keyboard
    )

# ===== Обработчик команды /start =====
@dp.message()
async def start_handler(message: types.Message):
    await message.answer("Привет! Пришли мне товар в формате:\nОписание; ссылка; картинка (файл)")

# ===== Обработчик сообщений с документами (картинками) =====
@dp.message()
async def product_handler(message: types.Message):
    # Проверяем, есть ли фото или документ
    if message.photo:
        photo = await message.photo[-1].download(destination=bytes)
    elif message.document and message.document.mime_type.startswith("image/"):
        photo = await message.document.download(destination=bytes)
    else:
        await message.reply("Нужно прислать картинку товара.")
        return

    # Разделяем текст на описание и ссылку
    if not message.caption or ";" not in message.caption:
        await message.reply("Подпись должна быть в формате: Описание; Ссылка")
        return
    
    description, referral_url = map(str.strip, message.caption.split(";", 1))

    # Публикуем в канал
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
