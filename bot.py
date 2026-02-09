import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=url)]
    ])

# Словарь для хранения временных данных товаров {user_id: {"photo":..., "text":..., "state":...}}
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
        "📦 Надішли фото товару з підписом у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання\n\n"
        "Після цього ти зможеш редагувати текст перед публікацією."
    )
    pending_products[message.from_user.id] = {"state": "await_photo"}

# Прием фото и текста
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    data = pending_products.get(user_id)

    # Если пользователь еще не начал добавлять товар
    if not data:
        return

    state = data.get("state", "new")

    # Состояние: ожидание фото
    if state == "await_photo":
        photo_file = None
        if message.photo:
            photo_file = message.photo[-1].file_id
        elif message.document and message.document.mime_type.startswith("image/"):
            photo_file = message.document.file_id

        if not photo_file:
            await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
            return

        data["photo"] = photo_file
        data["state"] = "await_text"
        await message.answer("✅ Фото отримано. Тепер надішли текст у форматі:\nНазва\nОпис\nЦіна\nДоставка\nПосилання")
        return

    # Состояние: ожидание текста
    if state == "await_text":
        if not message.text:
            await message.answer("❌ Надішли текстовий опис товару.")
            return

        lines = [line.strip() for line in message.text.split("\n") if line.strip()]
        if len(lines) < 5:
            await message.answer(
                "❌ Формат невірний.\nПотрібно 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання"
            )
            return

        data["text"] = message.text
        data["state"] = "ready"
        # Показываем кнопки редактирования/публикации
        await message.answer(
            "✅ Товар готовий до публікації. Можеш відредагувати текст або опублікувати.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редагувати", callback_data="edit_text")],
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )
        return

    # Состояние: редактирование текста
    if state == "editing":
        if not message.text:
            await message.answer("❌ Надішли текстовий опис товару.")
            return

        lines = [line.strip() for line in message.text.split("\n") if line.strip()]
        if len(lines) < 5:
            await message.answer(
                "❌ Формат невірний.\nПотрібно 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання"
            )
            return

        data["text"] = message.text
        data["state"] = "ready"
        await message.answer(
            "Текст збережено. Тепер можеш опублікувати товар.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )

# Обработка кнопок редактирования/публикации
@dp.callback_query()
async def handle_buttons(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)

    if not data:
        await callback.message.answer("❌ Немає товару для редагування.")
        return

    if callback.data == "edit_text":
        data["state"] = "editing"
        await callback.message.answer(
            "✏️ Відредагуй текст нижче і надішли його назад:",
            reply_markup=None
        )
        # Отправляем текущий текст
        await callback.message.answer(data["text"])

    elif callback.data == "publish":
        lines = [line.strip() for line in data["text"].split("\n") if line.strip()]
        title, description, price, delivery, url = lines[:5]
        caption = f"{title}\n\n{description}\n\n{price}\n{delivery}"

        try:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=data["photo"],
                caption=caption,
                reply_markup=buy_keyboard(url)
            )
            await callback.message.answer("✅ Товар опубліковано!", reply_markup=main_keyboard)
            pending_products.pop(user_id, None)
        except Exception as e:
            await callback.message.answer(f"❌ Помилка публікації:\n{e}")

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
