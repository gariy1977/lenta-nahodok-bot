from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os

TOKEN = "8439066571:AAE80bkMrNF1J6jJwR2qumjkDSs0EPFGLfI"
CHANNEL_ID = "-1003571651319"  # или ID канала через -100...

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === FSM состояния ===
class AddProduct(StatesGroup):
    name = State()
    description = State()
    price = State()
    link = State()
    photo = State()
    preview = State()

# === Старт добавления ===
@dp.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    await state.set_state(AddProduct.name)
    await message.answer("✏️ Вставь название товара:")

# === Название ===
@dp.message(AddProduct.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("📝 Вставь описание товара:")

# === Описание ===
@dp.message(AddProduct.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("💰 Укажи цену:")

# === Цена ===
@dp.message(AddProduct.price)
async def process_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddProduct.link)
    await message.answer("🔗 Вставь партнёрскую ссылку:")

# === Ссылка ===
@dp.message(AddProduct.link)
async def process_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await state.set_state(AddProduct.photo)
    await message.answer("📸 Пришли фото товара:")

# === Фото ===
@dp.message(AddProduct.photo, content_types=types.ContentType.PHOTO)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    data = await state.get_data()
    # Формируем предпросмотр
    preview_text = f"🧸 {data['name']}\n\n{data['description']}\n\n💰 Цена: {data['price']}"
    
    # Кнопка купить
    buy_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить", url=data['link'])],
            [InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )
    
    await message.answer_photo(photo=photo_id, caption=preview_text, reply_markup=buy_button)
    await state.set_state(AddProduct.preview)

# === Callback для публикации или отмены ===
@dp.callback_query(AddProduct.preview)
async def preview_callback(query: types.CallbackQuery, state: FSMContext):
    if query.data == "publish":
        data = await state.get_data()
        preview_text = f"🧸 {data['name']}\n\n{data['description']}\n\n💰 Цена: {data['price']}"
        buy_button = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", url=data['link'])]]
        )
        await bot.send_photo(chat_id=CHANNEL_ID, photo=data['photo_id'], caption=preview_text, reply_markup=buy_button)
        await query.message.edit_reply_markup(None)  # убираем кнопки
        await query.message.answer("✅ Товар опубликован в канале")
        await state.clear()
    elif query.data == "cancel":
        await query.message.edit_reply_markup(None)
        await query.message.answer("❌ Добавление товара отменено")
        await state.clear()

# === Запуск бота ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
