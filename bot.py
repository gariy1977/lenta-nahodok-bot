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

# Клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=url)]
    ])

# Словарь для хранения временных данных товаров {user_id: {"photo":..., "text":...}}
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

# Прием фото с текстом
@dp.message()
async def handle_product(message: types.Message):
    user_id = message.from_user.id
    photo_file = None

    # Получаем фото
    if message.photo:
        photo_file = message.photo[-1].file_id
    elif message.document and message.document.mime_type.startswith("image/"):
        photo_file = message.document.file_id

    if not photo_file:
        await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
        return

    # Получаем текст
    if not message.caption:
        await message.answer("❌ Додай опис у підписі до фото.", reply_markup=main_keyboard)
        return

    lines = [line.strip() for line in message.caption.split("\n") if line.strip()]
    if len(lines) < 5:
        await message.answer(
            "❌ Формат невірний.\n\nПотрібно 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання",
            reply_markup=main_keyboard
        )
        return

    # Сохраняем временно
    pending_products[user_id] = {
        "photo": photo_file,
        "text": message.caption
    }

    # Показываем предпросмотр с кнопками
    await message.answer(
        "✅ Товар готовий до публікації. Можеш відредагувати текст або опублікувати.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редагувати", callback_data="edit_text")],
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

# Прием отредактированного текста
@dp.message()
async def receive_edited_text(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_products:
        # Обновляем текст
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
