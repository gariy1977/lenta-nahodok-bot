import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Кнопка "Добавить товар"
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить товар")]
    ],
    resize_keyboard=True
)

# Кнопка "Купить"
def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Подивитись та купити", url=url)]
    ])

# Старт
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни кнопку ➕ Додати товар, щоб опублікувати товар у канал.",
        reply_markup=main_keyboard
    )

# Инструкция по кнопке
@dp.message(F.text == "➕ Добавить товар")
async def add_product_instruction(message: types.Message):
    await message.answer(
        "📦 Надішли фото товару з підписом у форматі:\n\n"
        "Назва\n"
        "Ціна\n"
        "Коротко\n"
        "Опис\n"
        "Посилання\n\n"
        "📌 Приклад:\n"
        "Назва товару\n"
        "1284 грн\n"
        "Набір для волосся\n"
        "Повний опис товару\n"
        "https://link.com"
    )

# Отправка товара в канал
async def send_product(photo_bytes: bytes, caption: str, url: str):
    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo_bytes,
        caption=caption,
        reply_markup=buy_keyboard(url)
    )

# Приём товара
@dp.message()
async def handle_product(message: types.Message):
    photo_bytes = None

    # Получаем фото
    if message.photo:
        photo_bytes = await message.photo[-1].download(destination=bytes)
    elif message.document and message.document.mime_type.startswith("image/"):
        photo_bytes = await message.document.download(destination=bytes)

    if not photo_bytes:
        await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
        return

    # Проверяем подпись
    if not message.caption:
        await message.answer("❌ Додай опис у підписі до фото.", reply_markup=main_keyboard)
        return

    lines = [line.strip() for line in message.caption.split("\n") if line.strip()]

    if len(lines) < 5:
        await message.answer(
            "❌ Формат невірний.\n\n"
            "Потрібно 5 рядків:\n"
            "Назва\nЦіна\nКоротко\nОпис\nПосилання",
            reply_markup=main_keyboard
        )
        return

    title = lines[0]
    price = lines[1]
    short = lines[2]
    description = lines[3]
    url = lines[-1]

    caption = (
        f"🛍 {title}\n\n"
        f"💰 Ціна: {price}\n"
        f"✨ {short}\n\n"
        f"📄 {description}"
    )

    await send_product(photo_bytes, caption, url)

    await message.answer(
        "✅ Товар опубліковано в канал!\n\n"
        "Можеш додати ще один товар 👇",
        reply_markup=main_keyboard
    )

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
