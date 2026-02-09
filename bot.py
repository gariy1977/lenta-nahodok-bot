import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================
# Клавиатура
# ==========================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Подивитись та купити", url=url)]]
    )

# ==========================
# Хранилище
# ==========================
pending_products = {}

# ==========================
# Старт
# ==========================
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

# ==========================
# Добавить товар
# ==========================
@dp.message(F.text == "➕ Добавить товар")
async def add_product(message: types.Message):
    user_id = message.from_user.id
    pending_products[user_id] = {
        "photos": [],
        "text": "",
        "editing": False,
        "sent_preview": False
    }

    await message.answer(
        "📦 Надішли фото товару (можна кілька).\n"
        "Після цього надішли текст у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання"
    )

# ==========================
# Обработка сообщений
# ==========================
@dp.message()
async def handle_product(message: types.Message):
    user_id = message.from_user.id
    data = pending_products.get(user_id)

    if not data:
        await message.answer("Спочатку натисни ➕ Додати товар.")
        return

    # ==========================
    # РЕДАКТИРОВАНИЕ ТЕКСТА
    # ==========================
    if data["editing"]:
        data["text"] = message.text
        data["editing"] = False
        await send_preview(message, user_id)
        return

    # ==========================
    # ФОТО
    # ==========================
    if message.photo or (message.document and message.document.mime_type.startswith("image/")):
        file_id = message.photo[-1].file_id if message.photo else message.document.file_id
        data["photos"].append(file_id)
        return  # ВАЖНО: НЕ ОТВЕЧАЕМ НА КАЖДОЕ ФОТО

    # ==========================
    # ТЕКСТ
    # ==========================
    if message.text:
        lines = [line.strip() for line in message.text.split("\n") if line.strip()]

        if len(lines) < 5:
            await message.answer(
                "❌ Формат невірний.\n\n"
                "Потрібно:\nНазва\nОпис\nЦіна\nДоставка\nПосилання"
            )
            return

        data["text"] = message.text
        await send_preview(message, user_id)

# ==========================
# Предпросмотр
# ==========================
async def send_preview(message, user_id):
    data = pending_products[user_id]

    if not data["photos"]:
        await message.answer("❌ Спочатку надішли фото товару.")
        return

    if not data["text"]:
        await message.answer("❌ Спочатку надішли текст.")
        return

    if data["sent_preview"]:
        return  # НЕ СПАМИМ ПОВТОРНО

    data["sent_preview"] = True

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редагувати текст", callback_data="edit_text")],
        [InlineKeyboardButton(text="📢 Опублікувати", callback_data="publish")]
    ])

    await message.answer("✅ Товар готовий до публікації.", reply_markup=keyboard)

# ==========================
# CALLBACK КНОПКИ
# ==========================
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)

    if not data:
        await callback.answer("❌ Товар не знайдено", show_alert=True)
        return

    # ==========================
    # РЕДАКТИРОВАТЬ
    # ==========================
    if callback.data == "edit_text":
        data["editing"] = True
        data["sent_preview"] = False
        await callback.message.answer("✏️ Надішли новий текст:")
        await callback.answer()
        return

    # ==========================
    # ПУБЛИКАЦИЯ
    # ==========================
    if callback.data == "publish":
        if not data["photos"] or not data["text"]:
            await callback.answer("❌ Товар не готовий", show_alert=True)
            return

        lines = [line.strip() for line in data["text"].split("\n") if line.strip()]
        url = lines[-1]

        if not re.match(r"^https?://", url):
            await callback.answer("❌ Останній рядок має бути URL", show_alert=True)
            return

        caption = "\n".join(lines[:-1]) or " "

        media = [types.InputMediaPhoto(media=p) for p in data["photos"]]
        media[0].caption = caption

        try:
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
            await bot.send_message(chat_id=CHANNEL_ID, text="🛒 Купити", reply_markup=buy_keyboard(url))

            await callback.message.answer("✅ Опубліковано!")
            pending_products.pop(user_id, None)

        except Exception as e:
            await callback.message.answer(f"❌ Помилка:\n{e}")

        await callback.answer()

# ==========================
# Запуск
# ==========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
