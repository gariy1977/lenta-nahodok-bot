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

TOKEN = os.getenv("BOT_TOKEN") or "YOUR_TOKEN"
CHANNEL_ID = os.getenv("CHANNEL_ID") or "-100XXXXXXXXXX"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === KEYBOARDS ===
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="▶️ Старт")]],
    resize_keyboard=True
)

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Додати товар")]],
    resize_keyboard=True
)

# === FSM ===
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    link = State()
    photos = State()
    preview = State()

# === START ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привіт 🌿\nНатисни «Старт», щоб почати.", reply_markup=start_kb)

@dp.message(F.text == "▶️ Старт")
async def start_button(message: types.Message):
    await message.answer("✨ Готово! Додавай товар.", reply_markup=main_kb)

# === ADD PRODUCT ===
@dp.message(F.text == "➕ Додати товар")
async def add_product(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddProduct.name)
    await state.update_data(photo_ids=[])
    await message.answer("✏️ Введи назву товару:")

# === NAME ===
@dp.message(AddProduct.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer("📝 Введи опис товару:")

# === DESCRIPTION ===
@dp.message(AddProduct.description, F.text)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer("💰 Вкажи ціну:")

# === PRICE ===
@dp.message(AddProduct.price, F.text)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    await state.set_state(AddProduct.link)
    await message.answer("🔗 Встав посилання:")

# === LINK ===
@dp.message(AddProduct.link, F.text)
async def process_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await state.set_state(AddProduct.photos)
    await message.answer("📸 Надішли фото товару. Коли все — натисни ✅ Готово.")

# === PHOTOS ===
@dp.message(AddProduct.photos, F.photo)
async def add_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])

    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_ids=photo_ids)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Ще фото", callback_data="photo_more"),
                InlineKeyboardButton(text="✅ Готово", callback_data="photo_done")
            ]
        ]
    )

    await message.answer(f"📸 Додано фото: {len(photo_ids)}", reply_markup=kb)

# === PHOTO CALLBACK SAFE ===
@dp.callback_query(F.data.in_(["photo_more", "photo_done"]))
async def photo_callback(query: types.CallbackQuery, state: FSMContext):
    current = await state.get_state()

    if current != AddProduct.photos.state:
        await query.answer("⚠️ Цей етап вже завершений", show_alert=True)
        return

    if query.data == "photo_more":
        await query.message.answer("Надішли ще фото 📸")
        await query.answer()
        return

    # DONE
    data = await state.get_data()
    photos = data.get("photo_ids", [])

    if not photos:
        await query.answer("❗ Додай хоча б одне фото", show_alert=True)
        return

    await state.set_state(AddProduct.preview)

    text = (
        f"<b>{data['name']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 Ціна: {data['price']}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купити", url=data['link'])],
            [
                InlineKeyboardButton(text="✅ Опублікувати", callback_data="publish"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")
            ]
        ]
    )

    media = [InputMediaPhoto(media=p) for p in photos]
    await query.message.answer_media_group(media=media)
    await query.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await query.answer()

# === PREVIEW CALLBACK ===
@dp.callback_query(AddProduct.preview, F.data.in_(["publish", "cancel"]))
async def preview_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    if query.data == "cancel":
        await state.clear()
        await query.message.answer("❌ Скасовано", reply_markup=main_kb)
        await query.answer()
        return

    # publish
    photos = data.get("photo_ids", [])
    if not photos:
        await query.answer("❗ Немає фото", show_alert=True)
        return

    text = (
        f"<b>{data['name']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 Ціна: {data['price']}"
    )

    media = [InputMediaPhoto(media=p) for p in photos]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛒 Купити", url=data['link'])]]
    )

    await bot.send_media_group(CHANNEL_ID, media=media)
    await bot.send_message(CHANNEL_ID, text, reply_markup=kb, parse_mode="HTML")

    await state.clear()
    await query.message.answer("✅ Товар опубліковано!", reply_markup=main_kb)
    await query.answer()

# === FALLBACK ===
@dp.message()
async def fallback(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await message.answer("⚠️ Будь ласка, відповідай по етапу. Якщо зависло — натисни «➕ Додати товар»")
    else:
        await message.answer("Натисни «➕ Додати товар», щоб почати", reply_markup=main_kb)

# === RUN ===
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
