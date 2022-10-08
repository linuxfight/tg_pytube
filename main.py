import os
import json
import re
import yt_dlp

from threading import Thread
from os.path import exists
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery


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


def generate_keyboard(video_id):
    buttons = [[
        InlineKeyboardButton(
            text="⬇ Скачать видео 🎥",
            callback_data=video_id + ":video"
        ),
        InlineKeyboardButton(
            text="⬇ Скачать аудио 🎙",
            callback_data=video_id + ":audio"
        )]]
    return InlineKeyboardMarkup(
        buttons
    )


async def download(video_url, download_type):
    info_file = 'info.json'
    video_id = get_video_id(video_url)
    output_filename = video_id + '.webm'
    command = f'yt-dlp -o "{output_filename}" {video_url} --quiet'

    if download_type == "audio":
        output_filename = video_id + '.mp3'
        command = f'yt-dlp -f "ba" -x --audio-format mp3 -o "{output_filename}" {video_url} --quiet'

    # os.system(f'yt-dlp --list-formats {video_url}')
    # -f "bv*[height=1080][fps=60]+ba*"   THERE IS NO 60 FPS, FPS IS A LIE
    # -S res,ext:mp4:m4a --recode mp4   My pc will die in pain, so no mp4 :)
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
        # await app.send_message(
        #    chat_id=msg.chat.id,
        #    reply_to_message_id=msg.id,
        #    text="❌ Сообщение не является ссылкой"
        # )
        return

    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
    title = info.get('title', None)

    await app.send_message(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        reply_markup=generate_keyboard(get_video_id(url)),
        text=f"Название: {title}\n"
             f"Ссылка: {url}"
    )


@app.on_callback_query()
async def on_callback_query(client, callback_query: CallbackQuery):
    data = callback_query.data.split(':')
    video_id = data[0]
    download_type = data[1]
    filename = video_id + '.webm'
    if download_type == 'audio':
        filename = video_id + '.mp3'

    bot_msg: Message = await app.send_message(
        chat_id=callback_query.message.chat.id,
        reply_to_message_id=callback_query.message.id,
        text="⚙ Обработка запроса"
    )

    if f'{video_id}_{download_type}' in storage:
        video = storage[f'{video_id}_{download_type}']
        await callback_query.answer(
            text="✅ Готово!"
        )
        if download_type == 'video':
            await app.send_document(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                document=video,
                file_name=filename
            )
        else:
            await app.send_audio(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                audio=video,
                file_name=filename
            )
        await app.delete_messages(chat_id=bot_msg.chat.id, message_ids=bot_msg.id)
        return

    video_path = await download(f'https://youtu.be/{video_id}', download_type)
    video = await app.send_document(
        chat_id=callback_query.message.chat.id,
        reply_to_message_id=callback_query.message.id,
        document=video_path,
        file_name=filename
    )
    await callback_query.answer(
        text="✅ Готово!"
    )
    file_id = None
    if video.document:
        file_id = video.document.file_id
    elif video.video:
        file_id = video.video.file_id
    else:
        file_id = video.audio.file_id
    storage.update({f'{video_id}_{download_type}': file_id})
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
