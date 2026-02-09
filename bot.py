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
        [InlineKeyboardButton(text="🛒 Купить", url=url)]
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
        "Привет! Нажми ➕ Добавить товар",
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
        "📸 Отправь фото товара.\n"
        "✍️ Потом отправь текст:\n\n"
        "Название\nОписание\nЦена\nДоставка\nСсылка"
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
        await message.answer("Фото принято 👍")
        return

    # ТЕКСТ
    if message.text:
        lines = [l.strip() for l in message.text.split("\n") if l.strip()]

        if len(lines) < 5:
            await message.answer("❌ Нужно 5 строк:\nНазвание\nОписание\nЦена\nДоставка\nСсылка")
            return

        data["text"] = message.text

        await message.answer(
            "✅ Товар готов! Нажми кнопку для публикации",
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
        await callback.answer("❌ Нет данных", show_alert=True)
        return

    lines = [l.strip() for l in data["text"].split("\n") if l.strip()]
    url = lines[-1]

    if not re.match(r"^https?://", url):
        await callback.answer("❌ Последняя строка — ссылка", show_alert=True)
        return

    caption = "\n".join(lines[:-1])[:1024]

    media = []
    for i, photo in enumerate(data["photos"]):
        if i == 0:
            media.append(types.InputMediaPhoto(media=photo, caption=caption))
        else:
            media.append(types.InputMediaPhoto(media=photo))

    try:
        await bot.send_media_group(CHANNEL_ID, media)
        await bot.send_message(CHANNEL_ID, "🛒 Купить", reply_markup=buy_keyboard(url))

        await callback.message.answer("✅ Опубликовано!", reply_markup=main_keyboard)
        user_data.pop(uid, None)

    except Exception as e:
        await callback.message.answer(f"❌ Ошибка:\n{e}")

    await callback.answer()

# ======================
# ЗАПУСК
# ======================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
