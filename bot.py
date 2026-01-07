import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

TOKEN = "8439066571:AAE80bkMrNF1J6jJwR2qumjkDSs0EPFGLfI"
CHANNEL_ID = -1003571651319  # ВСТАВЬ ID КАНАЛА

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Привет 🌿\n"
        "Присылай текст, фото или видео — я выложу это в Ленту Находок."
    )


@dp.message()
async def forward_to_channel(message: types.Message):
    if message.photo:
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=message.photo[-1].file_id,
            caption=message.caption or ""
        )
    elif message.video:
        await bot.send_video(
            chat_id=CHANNEL_ID,
            video=message.video.file_id,
            caption=message.caption or ""
        )
    else:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message.text
        )

    await message.answer("Готово ✅ Опубликовано в канале.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
