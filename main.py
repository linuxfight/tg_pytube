import os
import asyncio

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InputFile
from pytube import YouTube
from functools import partial


def get_token():
    token = open("token.txt", 'r').read()
    return token


bot = Bot(token=get_token())
dp = Dispatcher(bot)
path = os.path.join(os.getcwd() + '/videos/')
loop = asyncio.get_event_loop()


def get_video_id(url: str):
    url = url.replace('https://www.youtube.com/', '')
    url = url.replace('https://www.youtu.be', '')
    url = url.replace('watch?v=', '')
    url = url.replace('embed/', '')
    url = url.replace('v/', '')
    return url


def is_url(url):
    if "youtube.com" in url or "youtu.be" in url:
        return True
    return False


async def send_video(msg: types.message):
    if not is_url(msg.text):
        await bot.send_message(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.message_id,
            text="Сообщение не является ссылкой"
        )
        return
    video_id = get_video_id(msg.text)
    filename = video_id + '.mp4'
    if os.path.exists(os.path.join(path + filename)):
        video = os.path.join(path + filename)
        await bot.send_document(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.message_id,
            document=InputFile(path_or_bytesio=video, filename=filename)
        )
        return
    video = await loop.run_in_executor(
        executor=None,
        func=partial(
            YouTube(msg.text).streams.filter(file_extension='mp4').first().download,
            output_path=path,
            filename=filename
        )
    )
    await bot.send_document(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.message_id,
        document=InputFile(path_or_bytesio=video, filename=filename)
    )


@dp.message_handler()
async def download_video(msg: types.message):
    await send_video(msg)


if __name__ == '__main__':
    try:
        print("Bot is running")
        executor.start_polling(dp)
    except KeyboardInterrupt:
        pass
