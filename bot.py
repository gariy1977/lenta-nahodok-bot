import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Основная клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=url)]
    ])

# Хранилище временных данных {user_id: {"photos": [...], "text": str}}
pending_products = {}

# Старт
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

# Инструкция
@dp.message(F.text == "➕ Добавить товар")
async def add_product_instruction(message: types.Message):
    await message.answer(
        "📦 Надішли фото товару (можна кілька) та текст у підписі у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання\n\n"
        "Після цього ти зможеш редагувати текст перед публікацією."
    )

# Прием фото и текста
@dp.message()
async def handle_product(message: types.Message):
    user_id = message.from_user.id

    # Проверка фото
    if not (message.photo or (message.document and message.document.mime_type.startswith("image/"))):
        await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
        return

    if user_id not in pending_products:
        pending_products[user_id] = {"photos": [], "text": ""}

    # Сохраняем фото
    if message.photo:
        pending_products[user_id]["photos"].append(message.photo[-1].file_id)
    elif message.document and message.document.mime_type.startswith("image/"):
        pending_products[user_id]["photos"].append(message.document.file_id)

    # Если есть подпись, сохраняем текст
    if message.caption:
        lines = [line.strip() for line in message.caption.split("\n") if line.strip()]
        if len(lines) < 5:
            await message.answer(
                "❌ Формат тексту невірний.\n\nПотрібно 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання",
                reply_markup=main_keyboard
            )
            return
        pending_products[user_id]["text"] = message.caption

        # Предпросмотр и кнопки
        await message.answer(
            "✅ Товар готовий до публікації. Можеш відредагувати текст або опублікувати.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редагувати текст", callback_data="edit_text")],
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )
    else:
        await message.answer(
            "✅ Фото додано. Надішли текст опису після всіх фото у форматі:\n"
            "Назва\nОпис\nЦіна\nДоставка\nПосилання"
        )

# Кнопки редактирования/публикации
@dp.callback_query()
async def handle_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)

    if not data or not data.get("photos") or not data.get("text"):
        await callback.message.answer("❌ Немає повного товару для редагування або публікації.")
        return

    if callback.data == "edit_text":
        await callback.message.answer(
            "✏️ Відредагуй текст нижче і надішли його назад:",
            reply_markup=None
        )
        await callback.message.answer(data["text"])

    elif callback.data == "publish":
        lines = [line.strip() for line in data["text"].split("\n") if line.strip()]
        title, description, price, delivery, url = lines[:5]
        caption = f"{title}\n\n{description}\n\n{price}\n{delivery}"

        # Создаем галерею фото
        media = [types.InputMediaPhoto(media=photo_id) for photo_id in data["photos"]]
        media[0].caption = caption  # caption только к первому фото

        try:
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
            await bot.send_message(chat_id=CHANNEL_ID, text="Подивитись та купити", reply_markup=buy_keyboard(url))
            await callback.message.answer("✅ Товар опубліковано!", reply_markup=main_keyboard)
            pending_products.pop(user_id, None)
        except Exception as e:
            await callback.message.answer(f"❌ Помилка публікації:\n{e}")

# Прием отредактированного текста
@dp.message()
async def receive_edited_text(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_products and pending_products[user_id].get("photos"):
        pending_products[user_id]["text"] = message.text
        await message.answer(
            "Текст збережено. Тепер можеш опублікувати товар.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
