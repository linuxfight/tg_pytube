import os
import asyncio
import json

from os.path import exists
from pytube import YouTube
from functools import partial
from pyrogram import Client, filters
from pyrogram.types import Message


def config(key):
    if exists("config.txt"):
        data = json.loads(open("config.txt", 'r').read())
        return str(data[key])
    else:
        data = {
            'bot_token': 'BOT_TOKEN',
            'api_hash': 'API_HASH',
            'api_id': 'API_ID'
        }
        open("config.txt", 'w').write(json.dumps(data))
        quit(0)


def login():
    if exists("tgdl_bot.session"):
        return Client("tgdl_bot")
    return Client(
        "tgdl_bot",
        api_id=config('api_id'),
        api_hash=config('api_hash'),
        bot_token=config('bot_token')
    )


app = login()
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


async def send_video(msg: Message):
    if not is_url(msg.text):
        await app.send_message(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            text="Сообщение не является ссылкой"
        )
        return
    video_id = get_video_id(msg.text)
    filename = video_id + '.mp4'
    if os.path.exists(os.path.join(path + filename)):
        video = os.path.join(path + filename)
        await app.send_document(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            document=video,
            file_name=filename
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
    await app.send_document(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        document=video,
        file_name=filename
    )


@app.on_message(filters.command("/start"))
async def start_message(client, message: Message):
    await app.send_message(
        chat_id=message.chat.id,
        text="Привет, я помогу тебе скачать видео с Youtube! Отправь мне ссылку и я отправлю тебе видео.",
        reply_to_message_id=message.reply_to_message.id
    )


@app.on_message()
async def download_video(client, msg: Message):
    await send_video(msg)


if __name__ == '__main__':
    try:
        print("Bot is running")
        app.run()
    except KeyboardInterrupt:
        app.stop()
        pass
