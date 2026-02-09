import os
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise RuntimeError("BOT_TOKEN или CHANNEL_ID не заданы")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def build_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=url)]
    ])

async def send_product(channel_id: str, photo_bytes: bytes, caption: str, referral_url: str):
    photo_file = BufferedInputFile(photo_bytes, filename="product.jpg")
    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_file,
        caption=caption,
        reply_markup=build_keyboard(referral_url),
        parse_mode="HTML"
    )

@dp.message()
async def handle_message(message: types.Message):
    # ❌ если нет фото — игнорируем сразу
    if not message.photo and not (message.document and message.document.mime_type.startswith("image/")):
        await message.reply("📸 Пришли ОДНО сообщение: фото + подпись")
        return

    # ❌ если нет подписи — сразу ошибка
    if not message.caption:
        await message.reply(
            "✍️ Добавь подпись:\n"
            "Название; Цена; Кратко; Описание; Ссылка"
        )
        return

    # Получаем файл
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    file = await bot.get_file(file_id)
    stream = await bot.download_file(file.file_path)
    photo_bytes = stream.read()

    # Парсим подпись
    parts = list(map(str.strip, message.caption.split(";")))

    if len(parts) < 5:
        await message.reply(
            "❌ Формат неверный\n"
            "Пример:\n"
            "Название; Цена; Кратко; Описание; Ссылка"
        )
        return

    title, price, short, description, referral_url = parts[:5]

    caption = (
        f"🛍 <b>{title}</b>\n"
        f"💰 <b>{price}</b>\n\n"
        f"📌 {short}\n\n"
        f"📝 {description}"
    )

    await send_product(CHANNEL_ID, photo_bytes, caption, referral_url)

    await message.reply("✅ Товар опубликован в канал")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
