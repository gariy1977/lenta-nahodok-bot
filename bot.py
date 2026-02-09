import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart, Text

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

# Временное хранилище товаров {user_id: {"photos": [...], "text": str}}
pending_products = {}
# Пользователи, которые редактируют текст
editing_users = set()

# Старт
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

# Инструкция
@dp.message(Text("➕ Добавить товар"))
async def add_product_instruction(message: types.Message):
    user_id = message.from_user.id
    pending_products.pop(user_id, None)
    editing_users.discard(user_id)
    await message.answer(
        "📦 Надішли фото товару (можна кілька) та текст у підписі у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання\n\n"
        "Після цього ти зможеш редагувати текст перед публікацією."
    )

# Прием фото и текста
@dp.message()
async def handle_product(message: types.Message):
    user_id = message.from_user.id

    # Если пользователь редактирует текст
    if user_id in editing_users:
        pending_products[user_id]["text"] = message.text
        editing_users.remove(user_id)
        await message.answer(
            "Текст збережено. Тепер можеш опублікувати товар.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редагувати текст", callback_data="edit_text")],
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )
        return

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
                "❌ Формат тексту невірний.\n\nПотрібно мінімум 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання",
                reply_markup=main_keyboard
            )
            return
        pending_products[user_id]["text"] = message.caption

        # Предпросмотр и кнопки
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редагувати текст", callback_data="edit_text")],
            [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
        ])
        await message.answer("✅ Товар готовий до публікації.", reply_markup=keyboard)
    else:
        await message.answer(
            "✅ Фото додано. Надішли текст опису після всіх фото у форматі:\n"
            "Назва\nОпис\nЦіна\nДоставка\nПосилання"
        )

# Кнопка редактирования текста
@dp.callback_query(Text("edit_text"))
async def edit_text(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)
    if not data or not data.get("photos") or not data.get("text"):
        await callback.answer("❌ Немає товару для редагування.", show_alert=True)
        return
    editing_users.add(user_id)
    await callback.message.answer("✏️ Відредагуй текст нижче і надішли його назад:", reply_markup=None)
    await callback.message.answer(data["text"])
    await callback.answer()

# Кнопка публикации
@dp.callback_query(Text("publish"))
async def publish_product(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)
    if not data or not data.get("photos") or not data.get("text"):
        await callback.answer("❌ Немає повного товару для публікації.", show_alert=True)
        return

    lines = [line.strip() for line in data["text"].split("\n") if line.strip()]
    if len(lines) < 5:
        await callback.answer("❌ Текст має містити мінімум 5 рядків, останній рядок - URL.", show_alert=True)
        return

    url_candidate = lines[-1]
    if not re.match(r'^https?://', url_candidate):
        await callback.answer("❌ Останній рядок повинен бути валідним URL.", show_alert=True)
        return
    url = url_candidate

    caption = "\n".join(lines[:-1])  # Все кроме последнего ряда

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

    await callback.answer()  # Подтверждаем callback_query

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
