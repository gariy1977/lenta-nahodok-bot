import os
import asyncio
from io import BytesIO
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Подивитись та купити", url=url)]
    ])

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

@dp.message(F.text == "➕ Добавить товар")
async def add_product_instruction(message: types.Message):
    await message.answer(
        "📦 Надішли фото товару з підписом у форматі:\n\n"
        "Назва, Ціна, Опис\nПартнерське посилання\n\n"
    )

async def send_product(photo_file, caption: str, url: str):
    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=photo_file,
        caption=caption,
        reply_markup=buy_keyboard(url)
    )

@dp.message()
async def handle_product(message: types.Message):
    photo_file = None

    # Фото
    if message.photo:
        photo_file = message.photo[-1].file_id
    elif message.document and message.document.mime_type.startswith("image/"):
        photo_file = message.document.file_id

    if not photo_file:
        await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
        return

    # Подпись
    if not message.caption:
        await message.answer("❌ Додай опис у підписі.", reply_markup=main_keyboard)
        return

    lines = [line.strip() for line in message.caption.split("\n") if line.strip()]

    if len(lines) < 5:
        await message.answer(
            "❌ Формат невірний.\n\nПотрібно:\nНазва\nЦіна\nКоротко\nОпис\nПосилання",
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

    try:
        await send_product(photo_file, caption, url)
        await message.answer(
            "✅ Товар опубліковано!\n\nМожеш додати ще 👇",
            reply_markup=main_keyboard
        )
    except Exception as e:
        await message.answer(f"❌ Помилка публікації:\n{e}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
