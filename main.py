import os
import json
import re
import yt_dlp

from threading import Thread
from os.path import exists
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
    regex = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.'
                       r'(com|be)/(watch\?v=|embed/|v/|.+\?v=)?(?P<id>[A-Za-z0-9\-=_]{11})')

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


async def download(video_url):
    info_file = 'info.json'
    video_id = get_video_id(video_url)
    output_filename = video_id + '.webm'
    # os.system(f'yt-dlp --list-formats {video_url}')
    command = f'yt-dlp -o "{output_filename}" {video_url} --quiet'
    # -f "bv*[height=1080][fps=60]+ba*"   THERE IS NO 60 FPS, FPS IS A LIE
    # -S res,ext:mp4:m4a --recode mp4   My pc will die in pain, so no mp4 :)
    with yt_dlp.YoutubeDL() as ydl:
        thread = Thread(
            group=None,
            target=lambda: os.system(command)
        )
    thread.run()
    while thread.is_alive():
        pass
    else:
        while not exists(output_filename):
            pass
        else:
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
    text = msg.text.split()
    url = None
    for t in text:
        if is_url(t):
            url = t
    if not url:
        await app.send_message(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            text="Сообщение не является ссылкой"
        )
        return
    video_id = get_video_id(url)
    filename = video_id + '.webm'
    bot_msg: Message = await app.send_message(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        text="Обработка запроса"
    )
    if get_video_id(url) in storage:
        video = storage[get_video_id(url)]
        await app.send_document(
            chat_id=msg.chat.id,
            reply_to_message_id=msg.id,
            document=video,
            file_name=filename
        )
        await app.delete_messages(chat_id=bot_msg.chat.id, message_ids=bot_msg.id)
        return
    video_path = await download(url)
    video = await app.send_document(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        document=video_path,
        file_name=filename
    )
    file_id = None
    if video.document.file_id:
        file_id = video.document.file_id
    else:
        file_id = video.video.file_id
    storage.update({f'{get_video_id(msg.text)}': file_id})
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
