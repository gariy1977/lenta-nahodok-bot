import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.context import FSMContext
from redis.asyncio import Redis

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.info("Бот запускается...")

# ===== SECRETS =====
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
REDIS_URL = os.getenv("REDIS_URL")

if not all([TOKEN, CHANNEL_ID, REDIS_URL]):
    raise RuntimeError("Не переданы секреты BOT_TOKEN, CHANNEL_ID или REDIS_URL")

# ===== REDIS STORAGE =====
logger.info("Подключаем Redis...")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True, ssl=True)
storage = RedisStorage(redis=redis_client)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# ===== KEYBOARDS =====
start_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("▶️ Старт")]], resize_keyboard=True, one_time_keyboard=True)
main_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton("➕ Додати товар")]], resize_keyboard=True)

# ===== FSM =====
class AddProduct(StatesGroup):
    description = State()
    referral_link = State()
    media = State()
    preview = State()

# ===== START =====
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Привіт 🌿 Натисни «Старт»", reply_markup=start_kb)

@dp.message(lambda m: m.text == "▶️ Старт")
async def start_btn(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Готово. Додавай товар 👇", reply_markup=main_kb)

# ===== ADD PRODUCT =====
@dp.message(lambda m: m.text == "➕ Додати товар")
async def add_product(message: types.Message, state: FSMContext):
    await state.update_data(media=None)
    await state.set_state(AddProduct.description)
    await message.answer("✏️ Введи опис товару:")

@dp.message(AddProduct.description)
async def get_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProduct.referral_link)
    await message.answer("🔗 Встав реферальну ссылку:")

@dp.message(AddProduct.referral_link)
async def get_link(message: types.Message, state: FSMContext):
    await state.update_data(referral_link=message.text.strip())
    await state.set_state(AddProduct.media)
    await message.answer("📸 Надішли фото або відео:")

@dp.message(AddProduct.media, content_types=types.ContentType.PHOTO | types.ContentType.VIDEO)
async def get_media(message: types.Message, state: FSMContext):
    await state.update_data(media=message)
    data = await state.get_data()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Опублікувати", callback_data="publish"),
         InlineKeyboardButton(text="❌ Відмінити", callback_data="cancel")]
    ])

    if message.photo:
        file_id = message.photo[-1].file_id
        await message.answer_photo(file_id, caption=data["description"], reply_markup=kb)
    elif message.video:
        file_id = message.video.file_id
        await message.answer_video(file_id, caption=data["description"], reply_markup=kb)

    await state.set_state(AddProduct.preview)

# ===== CALLBACK =====
@dp.callback_query()
async def handle_callback(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    media_msg = data.get("media")

    if call.data == "publish":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подивитись та купити", url=data["referral_link"])]
        ])
        if media_msg.photo:
            file_id = media_msg.photo[-1].file_id
            await bot.send_photo(CHANNEL_ID, file_id, caption=data["description"], reply_markup=kb)
        elif media_msg.video:
            file_id = media_msg.video.file_id
            await bot.send_video(CHANNEL_ID, file_id, caption=data["description"], reply_markup=kb)

        await call.message.edit_text("✅ Товар опубліковано!", reply_markup=main_kb)
        await state.clear()
        await call.answer()
        return

    if call.data == "cancel":
        await call.message.edit_text("❌ Додавання товару скасовано", reply_markup=main_kb)
        await state.clear()
        await call.answer()
        return

# ===== FALLBACK =====
@dp.message()
async def fallback(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await message.answer("⚠️ Ти у процесі додавання товару. Продовжуй.")
    else:
        await message.answer("Натисни «➕ Додати товар»", reply_markup=main_kb)

# ===== RUN BOT =====
async def main():
    logger.info("Запускаем polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
