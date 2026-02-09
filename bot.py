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
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

# Кнопки для предпросмотра
def preview_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опублікувати", callback_data="publish")],
        [InlineKeyboardButton(text="Редагувати", callback_data="edit")]
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
        "Надішли фото товару з підписом у порядку:\n"
        "Назва\nОпис\nЦіна\nДоставка від магазину\nПосилання"
    )

# Хранилище временных товаров для редактирования
temp_products = {}

@dp.message()
async def handle_product(message: types.Message):
    if not message.photo and not (message.document and message.document.mime_type.startswith("image/")):
        await message.answer("❌ Надішли фото товару.", reply_markup=main_keyboard)
        return

    if not message.caption:
        await message.answer("❌ Додай підпис до фото.", reply_markup=main_keyboard)
        return

    photo_file = message.photo[-1].file_id if message.photo else message.document.file_id
    caption_text = message.caption  # оставляем полностью как есть

    # Сохраняем временно для редактирования
    temp_products[message.from_user.id] = {"photo": photo_file, "caption": caption_text}

    await message.answer(
        "Ось як виглядатиме твій товар у каналі:\n\n" + caption_text,
        reply_markup=preview_keyboard()
    )

# Обработка кнопок предпросмотра
@dp.callback_query()
async def handle_preview_buttons(query: types.CallbackQuery):
    user_id = query.from_user.id
    if user_id not in temp_products:
        await query.answer("❌ Немає товару для публікації.")
        return

    data = temp_products[user_id]

    if query.data == "publish":
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["photo"],
            caption=data["caption"]
        )
        await query.message.edit_text("✅ Товар опубліковано!\nМожеш додати ще один товар 👇", reply_markup=main_keyboard)
        temp_products.pop(user_id, None)

    elif query.data == "edit":
        await query.message.edit_text(
            "Надішли новий підпис для товару у тому ж порядку:\n"
            "Назва\nОпис\nЦіна\nДоставка від магазину\nПосилання"
        )
        await query.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
