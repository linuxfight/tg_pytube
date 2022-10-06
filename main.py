import asyncio
import os
import json
import re
import yt_dlp
import aiofiles


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


def format_selector(ctx):
    """ Select the best video and the best audio that won't result in an mkv.
    NOTE: This is just an example and does not handle all cases """

    # acodec='none' means there is no audio
    best_video = next(f for f in formats
                      if f['vcodec'] != 'none' and f['acodec'] == 'none')

    # find compatible audio extension
    audio_ext = {'mp4': 'm4a', 'webm': 'webm'}[best_video['ext']]
    # vcodec='none' means there is no video
    best_audio = next(f for f in formats if (
        f['acodec'] != 'none' and f['vcodec'] == 'none' and f['ext'] == audio_ext))

    # These are the minimum required fields for a merged format
    yield {
        'format_id': f'{best_video["format_id"]}+{best_audio["format_id"]}',
        'ext': best_video['ext'],
        'requested_formats': [best_video, best_audio],
        # Must be + separated list of protocols
        'protocol': f'{best_video["protocol"]}+{best_audio["protocol"]}'
    }


async def download(video_url, bot_msg):
    info_file = 'info.json'
    ydl_opts = {
        'format': format_selector,
    }
    output_filename = get_video_id(video_url) + '.webm'
    print(ydl_opts)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        thread = Thread(
            group=None,
            target=lambda: ydl.download([video_url])
        )
        info = ydl.extract_info(video_url, download=False)
    thread.run()
    while thread.is_alive():
        pass
    else:
        #await app.edit_message_text(chat_id=bot_msg.chat.id, message_id=bot_msg.id, text='Готово!')
        async with aiofiles.open(info_file, 'w') as file:
            await file.write(json.dumps(ydl.sanitize_info(info)))
        while not exists(info['title'] + f' [{get_video_id(video_url)}].webm'):
            print()
        else:
            return info['title'] + f' [{get_video_id(video_url)}].webm'


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
    filename = video_id + '.webm'
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
    video_path = await download(msg.text, bot_msg)
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
