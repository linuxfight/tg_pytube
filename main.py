import os
import json
import re

import httpx


from threading import Thread
from os.path import exists
from pytube import YouTube
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


def load():
    if exists("save.json"):
        data = open("save.json", 'r').read()
        return json.loads(data)
    else:
        data = {}
        open("save.json", 'w').write(json.dumps(data))
        return load()


def save(self):
    open("save.json", 'w').write(json.dumps(self))


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
storage = load()


def get_video_id(url: str):
    regex = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9\-=_]{11})')

    match = regex.match(url)

    if not match:
        return None
    return match.group('id')


def is_url(url):
    match_obj = re.match(r'^((?:https?:)?//)?((?:www|m)\.)?(youtube(-nocookie)?\.com|youtu.be)(/(?:[\w\-]+\?v=|embed/|v'
                         r'/)?)([\w\-]+)(\S+)?$', url)
    if match_obj:
         return True
    return False


#CHUNK_SIZE = 3 * 2 ** 20  # bytes
chunk_size = 3145728


async def download_video(client, video_url, filename, bot_msg):
    stream = YouTube(video_url).streams.filter(progressive=False, file_extension='mp4', mime_type='video/mp4')\
        .order_by('resolution').desc().first()
    url = stream.url

    await app.edit_message_text(chat_id=bot_msg.chat.id, message_id=bot_msg.id,
                                text="Скачивание видео, пожалуйста подождите")

    with open(filename, 'wb') as outfile:
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url) as response:
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    outfile.write(chunk)


async def download_audio(client, video_url, filename, bot_msg):
    stream = YouTube(video_url).streams.filter(only_audio=True, mime_type='audio/mp4').order_by('abr').desc().first()
    url = stream.url

    await app.edit_message_text(chat_id=bot_msg.chat.id, message_id=bot_msg.id, text="Скачивание аудио, пожалуйста подождите")

    with open(filename, 'wb') as outfile:
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', url) as response:
                async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                    outfile.write(chunk)


async def download(video_url, video_id, bot_msg):
    video_filename = video_id + '_video.mp4'
    audio_filename = video_id + '_audio.mp4'
    output_filename = video_id + '.mp4'
    await download_audio(client=app, video_url=video_url, filename=audio_filename, bot_msg=bot_msg)
    await download_video(client=app, video_url=video_url, filename=video_filename, bot_msg=bot_msg)
    command: str = 'ffmpeg -i ' + video_filename + ' -i ' + audio_filename + ' -c:v copy -c:a copy ' + output_filename + ' -hide_banner -loglevel error'
    thread = Thread(group=None, target=lambda:os.system(command))
    thread.run()
    while thread.is_alive():
        pass
    else:
        os.remove(video_filename)
        os.remove(audio_filename)
        await app.edit_message_text(chat_id=bot_msg.chat.id, message_id=bot_msg.id, text='Готово!')

        return output_filename


@app.on_message(filters.command("start"))
async def start_message(client, message: Message):
    await app.send_message(
        chat_id=message.chat.id,
        text="Привет, я помогу тебе скачать видео с Youtube! Отправь мне ссылку и я отправлю тебе видео.",
        reply_to_message_id=message.id
    )


@app.on_message()
async def on_link(client, msg: Message):
    if not is_url(msg.text):
        await app.send_message(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            text="Сообщение не является ссылкой"
        )
        return
    video_id = get_video_id(msg.text)
    filename = video_id + '.mp4'
    bot_msg: Message = await app.send_message(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        text="Обработка запроса"
    )
    if get_video_id(msg.text) in storage:
        video = storage[get_video_id(msg.text)]
        await app.send_document(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            document=video,
            file_name=filename
        )
        await app.delete_messages(chat_id=bot_msg.chat.id, message_ids=bot_msg.id)
        return
    video = await app.send_document(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        document=await download(msg.text, get_video_id(msg.text), bot_msg),
        file_name=filename
    )
    file_id = None
    if video.document.file_id:
        file_id = video.document.file_id
    else:
        file_id = video.video.file_id
    storage.update({f'{get_video_id(msg.text)}': file_id})
    video_path = get_video_id(msg.text) + '.mp4'
    os.remove(video_path)
    save(storage)
    await app.delete_messages(chat_id=bot_msg.chat.id, message_ids=bot_msg.id)


if __name__ == '__main__':
    try:
        print("Bot is running")
        app.run()
    except KeyboardInterrupt:
        app.stop()
        pass
