from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio
import os

# === Конфиг ===
TOKEN = os.getenv("BOT_TOKEN") or "8439066571:AAE80bkMrNF1J6jJwR2qumjkDSs0EPFGLfI"
CHANNEL_ID = os.getenv("CHANNEL_ID") or "-1003571651319"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === Клавиатуры ===
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="▶️ Старт")]],
    resize_keyboard=True
)

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Додати товар")]],
    resize_keyboard=True
)

# === FSM состояния ===
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    link = State()
    photos = State()
    preview = State()

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт 🌿\nНатисни «Старт», щоб почати роботу.",
        reply_markup=start_kb
    )

# === Кнопка Старт ===
@dp.message(F.text == "▶️ Старт")
async def start_by_button(message: types.Message):
    await message.answer(
        "✨ Відмінно! Тепер можеш додати товар.",
        reply_markup=main_kb
    )

# === Кнопка Додати товар ===
@dp.message(F.text == "➕ Додати товар")
async def add_by_button(message: types.Message, state: FSMContext):
    await state.set_state(AddProduct.name)
    await message.answer("✏️ Введи назву товару:")

# === Название ===
@dp.message(AddProduct.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("📝 Введи опис товару:")

# === Описание ===
@dp.message(AddProduct.description, F.text)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("💰 Вкажи ціну:")

# === Цена ===
@dp.message(AddProduct.price, F.text)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProduct.link)
    await message.answer("🔗 Встав партнёрське посилання:")

# === Ссылка ===
@dp.message(AddProduct.link, F.text)
async def process_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await state.set_state(AddProduct.photos)
    await message.answer(
        "📸 Надішли фото товару (можна кілька). Коли все готово — натисни ✅ Готово."
    )

# === Фото ===
@dp.message(AddProduct.photos, F.photo)
async def process_photos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_ids=photo_ids)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Додати ще фото", callback_data="add_more_photos"),
                InlineKeyboardButton(text="✅ Готово", callback_data="done_photos")
            ]
        ]
    )

    await message.answer(
        f"Фото додано. Всього зараз: {len(photo_ids)}",
        reply_markup=keyboard
    )

# === Callback фото ===
@dp.callback_query(F.data.in_(["add_more_photos", "done_photos"]))
async def photos_callback(query: types.CallbackQuery, state: FSMContext):
    if query.data == "done_photos":
        data = await state.get_data()
        await state.set_state(AddProduct.preview)

        # Превью с мини-анимациями и рамками
        preview_text = (
            f"✨🧸 <b>{data['name']}</b> 🧸✨\n\n"
            f"📝 {data['description']}\n\n"
            f"💰 Ціна: {data['price']} 💰\n"
            f"🎉🐱🎩 Лови свій бонус і купуй зараз! 🌟✨"
        )

        # Кнопки предпросмотра
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Подивитися та Купити", url=data['link'])],
                [
                    InlineKeyboardButton(text="✅ Опублікувати", callback_data="publish"),
                    InlineKeyboardButton(text="❌ Відміна", callback_data="cancel")
                ]
            ]
        )

        # Сетка фото как карусель с рамками и эмодзи
        media = []
        for pid in data["photo_ids"]:
            caption = "✨🌟"  # простая рамка эмодзи вокруг фото
            media.append(InputMediaPhoto(media=pid, caption=caption))

        await query.message.answer_media_group(media=media)
        await query.message.answer(preview_text, reply_markup=keyboard)
    else:
        await query.message.answer("📸 Надішли ще фото товару")

# === Callback предпросмотра ===
@dp.callback_query(AddProduct.preview, F.data.in_(["publish", "cancel"]))
async def preview_callback(query: types.CallbackQuery, state: FSMContext):
    if query.data == "publish":
        data = await state.get_data()

        text = (
            f"✨🧸 <b>{data['name']}</b> 🧸✨\n\n"
            f"📝 {data['description']}\n\n"
            f"💰 Ціна: {data['price']} 💰\n"
            f"🎉 Купуй зараз та отримай свій бонус 🐱🎩"
        )

        buy_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Подивитися та Купити", url=data['link'])]
            ]
        )

        # Публикуем фото как карусель с рамками
        media = []
        for pid in data["photo_ids"]:
            media.append(InputMediaPhoto(media=pid, caption="✨🌟"))
        await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        await bot.send_message(chat_id=CHANNEL_ID, text=text, reply_markup=buy_keyboard)

        await query.message.edit_reply_markup()
        await query.message.answer(
            "✅ Товар опубліковано!",
            reply_markup=main_kb
        )
        await state.clear()
    else:
        await query.message.edit_reply_markup()
        await query.message.answer(
            "❌ Додавання відмінено",
            reply_markup=main_kb
        )
        await state.clear()

# === Запуск ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
