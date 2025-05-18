from pydub import AudioSegment
from aiogram import Bot, types
from io import BytesIO

async def load_file_to_memory(bot: Bot, file: types.File | types.PhotoSize) -> BytesIO:
    buffer = BytesIO()
    await bot.download(file, buffer)
    buffer.seek(0)
    return buffer



def ogg_to_wav_bytes(ogg_bytes_io: BytesIO) -> BytesIO:
    ogg_bytes_io.seek(0)
    audio = AudioSegment.from_file(ogg_bytes_io, format="ogg")

    wav_io = BytesIO()
    audio.export(wav_io, format="wav")
    wav_io.name = "voice.wav" 
    wav_io.seek(0)
    
    return wav_io