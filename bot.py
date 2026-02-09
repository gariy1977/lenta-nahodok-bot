import os
import asyncio
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise RuntimeError("BOT_TOKEN или CHANNEL_ID не заданы")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кнопка покупки
def build_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подивитись та купити", url=url)]
        ]
    )

# Отправка товара в канал
async def send_product(channel_id: str, photo_bytes: bytes, caption: str, referral_url: str):
    photo_file = BufferedInputFile(photo_bytes, filename="product.jpg")

    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_file,
        caption=caption,
        reply_markup=build_keyboard(referral_url),
        parse_mode="HTML"
    )

# Основной обработчик
@dp.message()
async def handle_message(message: types.Message):
    # Проверка наличия фото
    if not message.photo and not (message.document and message.document.mime_type and message.document.mime_type.startswith("image/")):
        await message.reply("📸 Надішли ОДНЕ повідомлення: фото + опис + посилання")
        return

    # Проверка наличия текста
    if not message.caption:
        await message.reply("✍️ Додай опис товару та партнерське посилання")
        return

    # Получаем file_id
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    # Скачиваем фото
    file = await bot.get_file(file_id)
    stream = await bot.download_file(file.file_path)
    photo_bytes = stream.read()

    raw_text = message.caption.strip()

    # Ищем ссылку в тексте
    url_match = re.search(r"(https?://\S+)", raw_text)
    if not url_match:
        await message.reply("❌ Додай партнерське посилання (https://...)")
        return

    referral_url = url_match.group(1)

    # Убираем ссылку из описания
    caption_text = raw_text.replace(referral_url, "").strip()

    # Мини-чистка форматирования
    caption = caption_text.replace("\n\n\n", "\n\n").strip()

    # Отправка в канал
    await send_product(CHANNEL_ID, photo_bytes, caption, referral_url)

    await message.reply("✅ Товар опубліковано в канал")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
