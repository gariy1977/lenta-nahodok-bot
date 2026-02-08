import os
import uuid
import traceback
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    Update
)
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from redis.asyncio import Redis
from aiohttp import web

# ===== СЕКРЕТЫ =====
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
REDIS_URL = os.getenv("REDIS_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://lenta-nahodok-bot.fly.dev

if not all([TOKEN, CHANNEL_ID, REDIS_URL, WEBHOOK_URL]):
    raise RuntimeError("Не переданы секреты BOT_TOKEN, CHANNEL_ID, REDIS_URL или WEBHOOK_URL")

# ===== REDIS STORAGE =====
redis_client = Redis.from_url(REDIS_URL, decode_responses=True, ssl=True)
storage = RedisStorage(redis=redis_client)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# ===== KEYBOARDS =====
start_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="▶️ Старт")]],
    resize_keyboard=True,
    one_time_keyboard=True  # опционально, чтобы скрывалась после нажатия
)

main_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Додати товар")]],
    resize_keyboard=True,
    one_time_keyboard=False
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

@dp.message(lambda message: message.text == "▶️ Старт")
async def start_btn(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Готово. Додавай товар 👇", reply_markup=main_kb)

# ===== ADD PRODUCT =====
@dp.message(lambda message: message.text == "➕ Додати товар")
async def add_product(message: types.Message, state: FSMContext):
    if await state.get_state():
        await message.answer("⚠️ Ти вже додаєш товар. Заверши поточний.")
        return
    sid = str(uuid.uuid4())
    await state.update_data(session_id=sid, photo_ids=[])
    await state.set_state(AddProduct.name)
    await message.answer("✏️ Введи назву товару:")

# ===== NAME =====
@dp.message(AddProduct.name, lambda message: message.text)
async def name_step(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.description)
    await message.answer("📝 Введи опис:")

# ===== DESCRIPTION =====
@dp.message(AddProduct.description, lambda message: message.text)
async def desc_step(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer("💰 Вкажи ціну:")

# ===== PRICE =====
@dp.message(AddProduct.price, lambda message: message.text)
async def price_step(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text.strip())
    await state.set_state(AddProduct.link)
    await message.answer("🔗 Встав посилання:")

# ===== LINK =====
@dp.message(AddProduct.link, lambda message: message.text)
async def link_step(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await state.set_state(AddProduct.photos)
    await message.answer("📸 Надішли фото. Коли все — натисни ✅ Готово.")

# ===== PHOTOS =====
@dp.message(AddProduct.photos, lambda message: message.photo)
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
    await message.answer(f"📸 Додано фото: {len(photos)}", reply_markup=kb)

# ===== PHOTO CALLBACK =====
@dp.callback_query(lambda c: c.data.startswith(("more:", "done:")))
async def photo_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        await query.answer("⚠️ Стан втрачено. Натисни ще раз.", show_alert=True)
        return
    action, callback_sid = query.data.split(":")
    if callback_sid != sid:
        await query.answer("⚠️ Старий товар", show_alert=True)
        return
    if action == "more":
        await query.message.answer("Надішли ще фото 📸")
        await query.answer()
        return

    photos = data.get("photo_ids", [])
    if not photos:
        await query.answer("❗ Додай хоча б одне фото", show_alert=True)
        return

    await state.set_state(AddProduct.preview)
    text = (
        f"<b>{data['name']}</b>\n\n"
        f"{data['description']}\n\n"
        f"💰 {data['price']}\n\n"
        f"👇 Подивитись та купити"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🛒 Подивитись та купити", url=data['link']),
            InlineKeyboardButton(text="✅ Опублікувати", callback_data=f"publish:{sid}"),
            InlineKeyboardButton(text="❌ Скасувати", callback_data=f"cancel:{sid}")
        ]]
    )
    media = [
        InputMediaPhoto(media=p, caption=text, parse_mode="HTML") if i == 0 else InputMediaPhoto(media=p)
        for i, p in enumerate(photos)
    ]
    await query.message.answer_media_group(media=media)
    await query.message.answer("Перевір товар 👇", reply_markup=kb)
    await query.answer()

# ===== PREVIEW CALLBACK =====
@dp.callback_query(lambda c: c.data.startswith(("publish:", "cancel:")))
async def preview_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sid = data.get("session_id")
    if not sid:
        await query.answer("⚠️ Сесія втрачена", show_alert=True)
        return
    action, callback_sid = query.data.split(":")
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
        f"💰 {data['price']}\n\n"
        f"👇 Подивитись та купити"
    )
    await bot.send_media_group(
        chat_id=CHANNEL_ID,
        media=[InputMediaPhoto(media=p, caption=text if i == 0 else None, parse_mode="HTML") for i, p in enumerate(photos)]
    )
    await state.clear()
    await query.message.answer("✅ Товар опубліковано!", reply_markup=main_kb)
    await query.answer()

# ===== FALLBACK =====
@dp.message()
async def fallback(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await message.answer("⚠️ Ти у процесі додавання товару. Продовжуй.")
    else:
        await message.answer("Натисни «➕ Додати товар»", reply_markup=main_kb)

# === WEBHOOK & APP ===
WEBHOOK_PATH = "/webhook"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", 8080))

def create_app():
    app = web.Application()

    async def on_startup(app: web.Application):
        info = await bot.get_webhook_info()
        current_url = info.url
        target_url = WEBHOOK_URL + WEBHOOK_PATH

        if current_url != target_url:
            try:
                await bot.set_webhook(target_url)
                print("Webhook встановлено ✅")
            except TelegramRetryAfter as e:
                print(f"Too many requests, retry after {e.timeout} seconds")
                await asyncio.sleep(e.timeout)
                await bot.set_webhook(target_url)

    async def on_cleanup(app: web.Application):
        print("=== Завершаю бота ===")
        await bot.session.close()
        print("Сессия бота закрыта ✅")

    async def handle_webhook(request: web.Request):
        try:
            data = await request.json()
            update = Update(**data)
            await dp.feed_update(update)
        except Exception as e:
            print("Webhook error:", e)
            traceback.print_exc()
        return web.Response(text="ok")

    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    return app

# --- Запуск ---
if __name__ == "__main__":
    app = create_app()
    print(f"=== Запускаю сервер на {WEBAPP_HOST}:{WEBAPP_PORT} ===")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
