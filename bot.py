import os
import uuid
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import from_url as RedisFromURL

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.info("Бот запускается...")

# ===== SECRETS =====
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
REDIS_URL = os.getenv("REDIS_URL")  # Например: rediss://default:63b9cac5873c4abead1146f565ef7dff@fly-ra-redis.upstash.io:6379

if not all([TOKEN, CHANNEL_ID, REDIS_URL]):
    raise RuntimeError("Не переданы секреты BOT_TOKEN, CHANNEL_ID или REDIS_URL")

# ===== SINGLE INSTANCE LOCK =====
LOCK_FILE = "/tmp/ra_bot.lock"
if os.path.exists(LOCK_FILE):
    logger.warning("Бот уже запущен, выходим...")
    exit(0)
with open(LOCK_FILE, "w") as f:
    f.write(str(os.getpid()))

# ===== KEYBOARDS =====
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="▶️ Старт")]],
    resize_keyboard=True,
    one_time_keyboard=True
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

# ===== HANDLERS =====
def register_handlers(dp: Dispatcher):
    # --- START ---
    @dp.message(Command("start"))
    async def start(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Привіт 🌿 Натисни «Старт»", reply_markup=start_kb)

    @dp.message(lambda m: m.text == "▶️ Старт")
    async def start_btn(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("Готово. Додавай товар 👇", reply_markup=main_kb)

    # --- ADD PRODUCT ---
    @dp.message(lambda m: m.text == "➕ Додати товар")
    async def add_product(message: types.Message, state: FSMContext):
        if await state.get_state():
            await message.answer("⚠️ Ти вже додаєш товар. Заверши поточний.")
            return
        sid = str(uuid.uuid4())
        await state.update_data(session_id=sid, photo_ids=[])
        await state.set_state(AddProduct.name)
        await message.answer("✏️ Введи назву товару:")

    # --- FSM STEPS ---
    @dp.message(AddProduct.name)
    async def name_step(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text.strip())
        await state.set_state(AddProduct.description)
        await message.answer("📝 Введи опис:")

    @dp.message(AddProduct.description)
    async def desc_step(message: types.Message, state: FSMContext):
        await state.update_data(description=message.text.strip())
        await state.set_state(AddProduct.price)
        await message.answer("💰 Вкажи ціну:")

    @dp.message(AddProduct.price)
    async def price_step(message: types.Message, state: FSMContext):
        await state.update_data(price=message.text.strip())
        await state.set_state(AddProduct.link)
        await message.answer("🔗 Встав посилання:")

    @dp.message(AddProduct.link)
    async def link_step(message: types.Message, state: FSMContext):
        await state.update_data(link=message.text.strip())
        await state.set_state(AddProduct.photos)
        await message.answer("📸 Надішли фото. Коли все — натисни ✅ Готово.")

    @dp.message(AddProduct.photos, lambda m: m.photo)
    async def photos_step(message: types.Message, state: FSMContext):
        data = await state.get_data()
        photos = data.get("photo_ids", [])
        photos.append(message.photo[-1].file_id)
        await state.update_data(photo_ids=photos)
        sid = data["session_id"]

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="➕ Ще фото", callback_data=f"more:{sid}"),
                              InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{sid}")]]
        )
        await message.answer(f"📸 Додано фото: {len(photos)}", reply_markup=kb)

    # --- CALLBACK ---
    @dp.callback_query(lambda c: c.data.startswith(("more:", "done:", "publish:", "cancel:")))
    async def callback_handler(query: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        sid = data.get("session_id")
        if not sid:
            await query.answer("⚠️ Сесія втрачена", show_alert=True)
            return

        action, callback_sid = query.data.split(":")
        if callback_sid != sid:
            await query.answer("⚠️ Старий товар", show_alert=True)
            return

        if action == "more":
            await query.message.answer("Надішли ще фото 📸")
            await query.answer()
            return

        if action == "done":
            await state.set_state(AddProduct.preview)
            text = f"<b>{data['name']}</b>\n\n{data['description']}\n\n💰 {data['price']}\n\n👇 Подивитись та купити"
            photos = data.get("photo_ids", [])
            for i, p in enumerate(photos):
                await bot.send_photo(chat_id=query.message.chat.id, photo=p, caption=text if i == 0 else None, parse_mode="HTML")
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🛒 Подивитись та купити", url=data['link']),
                                  InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish:{sid}"),
                                  InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel:{sid}")]]
            )
            await query.message.answer("Перевір товар 👇", reply_markup=kb)
            await query.answer()
            return

        if action == "cancel":
            await state.clear()
            await query.message.answer("❌ Скасовано", reply_markup=main_kb)
            await query.answer()
            return

        if action == "publish":
            photos = data.get("photo_ids", [])
            text = f"<b>{data['name']}</b>\n\n{data['description']}\n\n💰 {data['price']}\n\n👇 Подивитись та купити"
            for i, p in enumerate(photos):
                await bot.send_photo(chat_id=CHANNEL_ID, photo=p, caption=text if i == 0 else None, parse_mode="HTML")
            await state.clear()
            await query.message.answer("✅ Товар опубліковано!", reply_markup=main_kb)
            await query.answer()

    # --- FALLBACK ---
    @dp.message()
    async def fallback(message: types.Message, state: FSMContext):
        current = await state.get_state()
        if current:
            await message.answer("⚠️ Ти у процесі додавання товару. Продовжуй.")
        else:
            await message.answer("Натисни «➕ Додати товар»", reply_markup=main_kb)

# ===== CLEAR WEBHOOK =====
async def clear_webhook(bot: Bot):
    info = await bot.get_webhook_info()
    if info.url:
        logger.info(f"Удаляем старый webhook: {info.url}")
        await bot.delete_webhook(drop_pending_updates=True)
        await asyncio.sleep(1)

# ===== MAIN =====
async def main():
    # ===== REDIS =====
    redis_client = RedisFromURL(REDIS_URL, decode_responses=True)
    storage = RedisStorage(redis=redis_client)

    # ===== BOT & DISPATCHER =====
    global bot
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=storage)

    # ===== Регистрируем хэндлеры =====
    register_handlers(dp)

    # ===== CLEAR WEBHOOK =====
    await clear_webhook(bot)

    # ===== START POLLING =====
    try:
        logger.info("Запускаем polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis_client.close()
        await storage.close()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

if __name__ == "__main__":
    asyncio.run(main())
