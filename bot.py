import os
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Основная клавиатура
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="➕ Добавить товар")]],
    resize_keyboard=True
)

def buy_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подивитись та купити", url=url)]
    ])

# Хранилище товаров {user_id: {"photos": [], "text": str, "ready": bool, "notified_photo": bool}}
pending_products = {}
editing_users = set()

# ==========================
# Старт
# ==========================
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни ➕ Додати товар для публікації.",
        reply_markup=main_keyboard
    )

# ==========================
# Инструкция добавления
# ==========================
@dp.message(F.text == "➕ Добавить товар")
async def add_product_instruction(message: types.Message):
    user_id = message.from_user.id
    pending_products[user_id] = {"photos": [], "text": "", "ready": False, "notified_photo": False}
    editing_users.discard(user_id)
    await message.answer(
        "📦 Надішли фото товару (можна кілька) та текст у підписі у форматі:\n\n"
        "Назва\nОпис\nЦіна\nДоставка\nПосилання\n\n"
        "Після цього ти зможеш редагувати текст перед публікацією."
    )

# ==========================
# Обработка фото и текста
# ==========================
@dp.message()
async def handle_product(message: types.Message):
    user_id = message.from_user.id
    data = pending_products.get(user_id)

    if not data:
        await message.answer("Спочатку натисни ➕ Додати товар.", reply_markup=main_keyboard)
        return

    # Пользователь редактирует текст
    if user_id in editing_users:
        data["text"] = message.text
        data["ready"] = True
        editing_users.remove(user_id)
        await message.answer(
            "Текст збережено. Тепер можеш опублікувати товар.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Редагувати текст", callback_data="edit_text")],
                [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
            ])
        )
        return

    # Обработка фото
    is_photo = message.photo or (message.document and message.document.mime_type.startswith("image/"))
    if is_photo:
        if message.photo:
            data["photos"].append(message.photo[-1].file_id)
        else:
            data["photos"].append(message.document.file_id)

    # Сообщение о том, что фото добавлено, только один раз
    if is_photo and not message.caption and not data["notified_photo"]:
        data["notified_photo"] = True
        await message.answer(
            "✅ Фото додано. Надішли текст опису після всіх фото у форматі:\n"
            "Назва\nОпис\nЦіна\nДоставка\nПосилання"
        )
        return

    # Обработка текста (caption или сообщение)
    text = message.caption if message.caption else message.text
    if text:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) < 5:
            await message.answer(
                "❌ Формат тексту невірний.\n\nПотрібно мінімум 5 рядків:\nНазва\nОпис\nЦіна\nДоставка\nПосилання",
                reply_markup=main_keyboard
            )
            return
        data["text"] = text
        data["ready"] = True

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Редагувати текст", callback_data="edit_text")],
            [InlineKeyboardButton(text="Опублікувати", callback_data="publish")]
        ])
        await message.answer("✅ Товар готовий до публікації.", reply_markup=keyboard)

# ==========================
# Редактирование и публикация
# ==========================
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = pending_products.get(user_id)

    if callback.data == "edit_text":
        if not data or not data.get("photos") or not data.get("text"):
            await callback.answer("❌ Немає товару для редагування.", show_alert=True)
            return
        editing_users.add(user_id)
        await callback.message.answer("✏️ Відредагуй текст нижче і надішли його назад:", reply_markup=None)
        await callback.message.answer(data["text"])
        await callback.answer()
        return

    if callback.data == "publish":
        if not data or not data.get("photos") or not data.get("text") or not data.get("ready"):
            await callback.answer("❌ Товар ще не готовий до публікації.", show_alert=True)
            return

        lines = [line.strip() for line in data["text"].split("\n") if line.strip()]
        if len(lines) < 5 or not re.match(r'^https?://', lines[-1]):
            await callback.answer("❌ Останній рядок повинен бути валідним URL.", show_alert=True)
            return

        url = lines[-1]
        caption = "\n".join(lines[:-1])
        media = [types.InputMediaPhoto(media=photo_id) for photo_id in data["photos"]]
        media[0].caption = caption if caption else " "

        try:
            channel_id_int = int(CHANNEL_ID)
            if media:
                await bot.send_media_group(chat_id=channel_id_int, media=media)
            await bot.send_message(chat_id=channel_id_int, text="Подивитись та купити", reply_markup=buy_keyboard(url))
            await callback.message.answer("✅ Товар опубліковано!", reply_markup=main_keyboard)
            pending_products.pop(user_id, None)
        except Exception as e:
            print(f"[ERROR] Publish failed: {e}")
            await callback.message.answer(f"❌ Помилка публікації:\n{e}")

        await callback.answer()

# ==========================
# Запуск
# ==========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
