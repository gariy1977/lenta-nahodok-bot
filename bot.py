import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ======================
# КНОПКИ
# ======================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def publish_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликовать", callback_data="publish")]
    ])

def buy_keyboard(url):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Подивитись та купити", url=url)]
    ])

# ======================
# ПАМЯТЬ
# ======================
user_data = {}

# ======================
# СТАРТ
# ======================
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет! Нажми ➕ Добавить товар.\n\n"
        "Загрузите фотографию товара (одну или несколько).",
        reply_markup=main_keyboard
    )

# ======================
# ДОБАВИТЬ ТОВАР
# ======================
@dp.message(F.text == "➕ Добавить товар")
async def add_product(message: types.Message):
    user_data[message.from_user.id] = {
        "photos": [],
        "text": ""
    }

    await message.answer(
        "📸 Загрузите фотографию товара (одну или несколько)."
    )

# ======================
# ПОЛУЧЕНИЕ ФОТО И ТЕКСТА
# ======================
@dp.message()
async def handle(message: types.Message):
    uid = message.from_user.id
    data = user_data.get(uid)

    if not data:
        return

    # ФОТО
    if message.photo:
        data["photos"].append(message.photo[-1].file_id)
        await message.answer(
            "✅ Фото принято.\n"
            "Теперь загрузите описание товара и партнёрскую ссылку.\n\n"
            "Формат:\n"
            "Название\nОписание\nЦена\nДоставка\nСсылка"
        )
        return

    # ТЕКСТ
    if message.text:
        lines = [l.strip() for l in message.text.split("\n") if l.strip()]

        if len(lines) < 5:
            await message.answer(
                "❌ Нужно 5 строк:\n"
                "Название\nОписание\nЦена\nДоставка\nСсылка"
            )
            return

        data["text"] = message.text

        await message.answer(
            "✅ Товар готов к публикации. Нажмите кнопку ниже.",
            reply_markup=publish_keyboard()
        )

# ======================
# CALLBACK — ПУБЛИКАЦИЯ
# ======================
@dp.callback_query(F.data == "publish")
async def publish(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = user_data.get(uid)

    if not data or not data["photos"] or not data["text"]:
        await callback.answer("❌ Нет данных для публикации", show_alert=True)
        return

    lines = [l.strip() for l in data["text"].split("\n") if l.strip()]
    url = lines[-1]

    if not re.match(r"^https?://", url):
        await callback.answer("❌ Последняя строка должна быть ссылкой", show_alert=True)
        return

    caption = "\n".join(lines[:-1])[:1024]

    try:
        # Первая фотка — с текстом и кнопкой
        first_photo = data["photos"][0]

        await bot.send_photo(
            CHANNEL_ID,
            photo=first_photo,
            caption=caption,
            reply_markup=buy_keyboard(url)
        )

        # Остальные фото — без кнопок
        if len(data["photos"]) > 1:
            media = [types.InputMediaPhoto(media=p) for p in data["photos"][1:]]
            await bot.send_media_group(CHANNEL_ID, media)

        await callback.message.answer("✅ Товар опубликован!", reply_markup=main_keyboard)
        user_data.pop(uid, None)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка публикации:\n{e}")

    await callback.answer()

# ======================
# ЗАПУСК
# ======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
