import os
import asyncio
from io import BytesIO

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise RuntimeError("BOT_TOKEN или CHANNEL_ID не заданы")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Формирование кнопки
def build_keyboard(referral_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=referral_url)]
    ])

# Отправка товара
async def send_product(channel_id: str, photo_bytes: bytes, caption: str, referral_url: str):
    photo_file = BufferedInputFile(photo_bytes, filename="product.jpg")
    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_file,
        caption=caption,
        reply_markup=build_keyboard(referral_url)
    )

# Обработчик сообщений
@dp.message()
async def handle_message(message: types.Message):
    # Получаем фото
    file_bytes = None

    if message.photo:
        file = await bot.get_file(message.photo[-1].file_id)
        file_bytes = await bot.download_file(file.file_path)
    elif message.document and message.document.mime_type.startswith("image/"):
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)

    if not file_bytes:
        await message.reply("📸 Пришли картинку товара")
        return

    # Проверяем подпись
    if not message.caption or ";" not in message.caption:
        await message.reply(
            "Подпись в формате:\n"
            "Название; Цена; Кратко; Описание; Ссылка"
        )
        return

    parts = list(map(str.strip, message.caption.split(";")))

    if len(parts) < 5:
        await message.reply("❌ Недостаточно данных в подписи")
        return

    title, price, short, description, referral_url = parts[:5]

    caption = (
        f"🛍 <b>{title}</b>\n"
        f"💰 <b>{price}</b>\n\n"
        f"📌 {short}\n\n"
        f"📝 {description}"
    )

    await send_product(CHANNEL_ID, file_bytes.read(), caption, referral_url)

    await message.reply("✅ Товар опубликован в канале")

# Запуск
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
