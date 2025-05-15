from aiogram import Bot, types
from io import BytesIO

async def load_file_to_memory(bot: Bot, file: types.File | types.PhotoSize) -> BytesIO:
    buffer = BytesIO()
    await bot.download(file, buffer)
    buffer.seek(0)
    return buffer
