from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio, os, uuid

TOKEN = os.getenv("BOT_TOKEN") or "YOUR_TOKEN"
CHANNEL_ID = os.getenv("CHANNEL_ID") or "-100XXXXXXXXXX"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== KEYBOARDS =====
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="▶️ Старт")]],
    resize_keyboard=True
)

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Додати товар")]],
    resize_keyboard=True
)

# ===== FSM =====
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    link = State()
    photos = State()
    preview = State()

# ===== START =====
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привіт 🌿 Натисни «Старт»", reply_markup=start_kb)

@dp.message(F.text == "▶️ Старт")
async def start_btn(message: types.Message):
    await message.answer("Готово. Додавай товар 👇", reply_markup=main_kb)

# ===== NEW PRODUCT SESSION =====
@dp.message(F.text == "➕ Додати товар")
async def add_product(message: types.Message, state: FSMContext):
    await state.clear()
    session_id = str(uuid.uuid4())

    await state.update_data(
        session_id=session_id,
        photo_ids=[]
    )

    await state.set_state(AddProduct.name)
    await message.answer("✏️ Введи назву товару:")

# ===== NAME =====
@dp.message(AddProduct.name, F.text)
async def name_step(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer("📝 Введи опис:")

# ===== DESCRIPTION =====
@dp.message(AddProduct.description, F.text)
async def desc_step(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer("💰 Вкажи ціну:")

# ===== PRICE =====
@dp.message(AddProduct.price, F.text)
async def price_step(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    await state.set_state(AddProduct.link)
    await message.answer("🔗 Встав посилання:")

# ===== LINK =====
@dp.message(AddProduct.link, F.text)
async def link_step(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await state.set_state(AddProduct.photos)
    await message.answer("📸 Надішли фото. Коли все — натисни ✅ Готово.")

# ===== PHOTOS =====
@dp.message(AddProduct.photos, F.photo)
async def photos_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photo_ids", [])
    photos.append(message.photo[-1].file_id)

    await state.update_data(photo_ids=photos)

    sid = data["session_id"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="➕ Ще фото", callback_data=f"more:{sid}"),
            InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{sid}")
        ]]
    )

    await message.answer(f"📸 Фото додано: {len(photos)}", reply_markup=kb)

# ===== PHOTO CALLBACK =====
@dp.callback_query(F.data.startswith(("more:", "done:")))
async def photo_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sid = data.get("session_id")

    action, callback_sid = query.data.split(":")

    # IGNORE OLD CALLBACKS
    if callback_sid != sid:
        await query.answer("⚠️ Це старий товар", show_alert=True)
        return

    if await state.get_state() != AddProduct.photos.state:
        await query.answer("⚠️ Етап вже завершено", show_alert=True)
        return

    if action == "more":
        await query.message.answer("Надішли ще фото 📸")
        await query.answer()
        return

    # DONE PHOTOS
    photos = data.get("photo_ids", [])
    if not photos:
        await query.answer("❗ Додай хоча б одне фото", show_alert=True)
        return

    await state.set_state(AddProduct.preview)

    text = (
        f"<b>{data['name']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 {data['price']}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купити", url=data['link'])],
            [
                InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish:{sid}"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel:{sid}")
            ]
        ]
    )

    media = [InputMediaPhoto(media=p) for p in photos]
    await query.message.answer_media_group(media=media)
    await query.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await query.answer()

# ===== PREVIEW CALLBACK =====
@dp.callback_query(F.data.startswith(("publish:", "cancel:")))
async def preview_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sid = data.get("session_id")

    action, callback_sid = query.data.split(":")

    # IGNORE OLD CALLBACKS
    if callback_sid != sid:
        await query.answer("⚠️ Старий товар", show_alert=True)
        return

    if action == "cancel":
        await state.clear()
        await query.message.answer("❌ Скасовано", reply_markup=main_kb)
        await query.answer()
        return

    photos = data.get("photo_ids", [])
    if not photos:
        await query.answer("❗ Немає фото", show_alert=True)
        return

    text = (
        f"<b>{data['name']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 {data['price']}"
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

# ===== FALLBACK =====
@dp.message()
async def fallback(message: types.Message, state: FSMContext):
    if await state.get_state():
        await message.answer("⚠️ Відповідай по етапу або натисни «➕ Додати товар»")
    else:
        await message.answer("Натисни «➕ Додати товар»", reply_markup=main_kb)

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
