import os
import asyncio
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

DATA_FILE = "pending_products.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================
# ЗАГРУЗКА / СОХРАНЕНИЕ
# ==========================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

pending_products = load_data()

# ==========================
# КЛАВИАТУРА
# ==========================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Подивитись та купити", url=url)]
        ]
    )

# ==========================
# СТАРТ
# ==========================
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

# ==========================
# ДОБАВИТЬ ТОВАР
# ==========================
@dp.message(F.text == "➕ Добавить товар")
async def add_product(message: types.Message):
    pending_products[str(message.from_user.id)] = {
        "photos": [],
        "text": "",
        "editing": False
    }
    save_data(pending_products)

    await message.answer(
        "📦 Надішли фото товару (можна кілька).\n"
        "Потім надішли текст у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання"
    )

# ==========================
# ОБРАБОТКА
# ==========================
@dp.message()
async def handle_product(message: types.Message):
    user_id = str(message.from_user.id)
    data = pending_products.get(user_id)

    if not data:
        return

    # ✏️ РЕДАКТИРОВАНИЕ
    if data["editing"] and message.text:
        data["text"] = message.text
        data["editing"] = False
        save_data(pending_products)
        await send_preview(message, user_id)
        return

    # 🖼 ФОТО
    if message.photo:
        data["photos"].append(message.photo[-1].file_id)
        save_data(pending_products)
        await send_preview(message, user_id)
        return

    # 📝 ТЕКСТ
    if message.text:
        lines = [l.strip() for l in message.text.split("\n") if l.strip()]

        if len(lines) < 5:
            await message.answer(
                "❌ Формат неправильний.\n\n"
                "Потрібно:\nНазва\nОпис\nЦіна\nДоставка\nПосилання"
            )
            return

        data["text"] = message.text
        save_data(pending_products)
        await send_preview(message, user_id)

# ==========================
# ПРЕДПРОСМОТР
# ==========================
async def send_preview(message, user_id):
    data = pending_products[user_id]

    if not data["photos"] or not data["text"]:
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати текст", callback_data="edit_text")],
        [InlineKeyboardButton(text="📢 Опублікувати", callback_data="publish")]
    ])

    await message.answer("✅ Товар готовий до публікації.", reply_markup=keyboard)

# ==========================
# CALLBACK
# ==========================
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    data = pending_products.get(user_id)

    if not data:
        await callback.answer("❌ Товар не знайдено", show_alert=True)
        return

    # ✏️ РЕДАКТИРОВАТЬ
    if callback.data == "edit_text":
        data["editing"] = True
        save_data(pending_products)
        await callback.message.answer("✏️ Надішли новий текст:")
        await callback.answer()
        return

    # 📢 ПУБЛИКАЦИЯ
    if callback.data == "publish":
        if not data["photos"] or not data["text"]:
            await callback.answer("❌ Товар не готовий", show_alert=True)
            return

        lines = [l.strip() for l in data["text"].split("\n") if l.strip()]
        url = lines[-1]

        if not re.match(r"^https?://", url):
            await callback.answer("❌ Останній рядок має бути URL", show_alert=True)
            return

        caption = "\n".join(lines[:-1])[:1024]

        media = []
        for i, p in enumerate(data["photos"]):
            if i == 0:
                media.append(types.InputMediaPhoto(media=p, caption=caption))
            else:
                media.append(types.InputMediaPhoto(media=p))

        try:
            await bot.send_media_group(CHANNEL_ID, media)
            await bot.send_message(CHANNEL_ID, "🛒 Купити", reply_markup=buy_keyboard(url))

            await callback.message.answer("✅ Опубліковано!", reply_markup=main_keyboard)
            pending_products.pop(user_id, None)
            save_data(pending_products)

        except Exception as e:
            await callback.message.answer(f"❌ Помилка публікації:\n{e}")

        await callback.answer()

# ==========================
# ЗАПУСК
# ==========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
