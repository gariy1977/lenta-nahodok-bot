import os
import asyncio
import re

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    raise RuntimeError("BOT_TOKEN или CHANNEL_ID не заданы")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Главное меню
def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Додати товар", callback_data="add_product")]
        ]
    )

# Кнопка покупки
def buy_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Подивитись та купити", url=url)]
        ]
    )

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.reply(
        "Привіт! Я бот для додавання товарів у канал 📦\n\n"
        "Натисни кнопку нижче, щоб додати товар 👇",
        reply_markup=main_menu()
    )

# Кнопка "Додати товар"
@dp.callback_query(lambda c: c.data == "add_product")
async def add_product_callback(callback: types.CallbackQuery):
    await callback.message.reply(
        "📸 Надішли ОДНЕ повідомлення:\n\n"
        "1️⃣ Фото товару\n"
        "2️⃣ Опис (у будь-якому форматі)\n"
        "3️⃣ Партнерське посилання (https://...)\n\n"
        "Приклад:\n"
        "💆‍♀️ Набір для волосся\n"
        "💰 Ціна: 1284 грн\n"
        "🚚 Доставка Nutritive\n"
        "https://site.com/product"
    )
    await callback.answer()

# Отправка товара в канал
async def send_product(channel_id: str, photo_bytes: bytes, caption: str, referral_url: str):
    photo_file = BufferedInputFile(photo_bytes, filename="product.jpg")

    await bot.send_photo(
        chat_id=channel_id,
        photo=photo_file,
        caption=caption,
        reply_markup=buy_keyboard(referral_url),
        parse_mode="HTML"
    )

# Основной обработчик товаров
@dp.message()
async def handle_message(message: types.Message):
    # Проверка фото
    if not message.photo and not (
        message.document and message.document.mime_type and message.document.mime_type.startswith("image/")
    ):
        return

    # Проверка текста
    if not message.caption:
        await message.reply("✍️ Додай опис товару та партнерське посилання")
        return

    # Получаем file_id
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    # Скачиваем файл
    file = await bot.get_file(file_id)
    stream = await bot.download_file(file.file_path)
    photo_bytes = stream.read()

    raw_text = message.caption.strip()

    # Ищем ссылку
    url_match = re.search(r"(https?://\S+)", raw_text)
    if not url_match:
        await message.reply("❌ Додай партнерське посилання (https://...)")
        return

    referral_url = url_match.group(1)

    # Убираем ссылку из описания
    caption_text = raw_text.replace(referral_url, "").strip()

    caption = caption_text.replace("\n\n\n", "\n\n").strip()

    # Отправляем в канал
    await send_product(CHANNEL_ID, photo_bytes, caption, referral_url)

    await message.reply("✅ Товар опубліковано в канал")

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
