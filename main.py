import asyncio
import os
import json
import re
import yt_dlp
import aiofiles

from os.path import exists
from pyrogram import Client, filters, enums
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
        with open("save.json", 'r') as file:
            data = file.read()
        return json.loads(data)
    else:
        data = {}
        with open("save.json", 'w') as file:
            file.write(json.dumps(data))
        return load()


async def save(self):
    async with aiofiles.open("save.json", 'w') as file:
        await file.write(json.dumps(self))


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
    video_id = get_video_id(video_url)
    output_filename = video_id + '.mkv'
    command = f'yt-dlp --merge-output-format mkv -o "{output_filename}" {video_url} --quiet'

    if download_type == "audio":
        output_filename = video_id + '.mp3'
        command = f'yt-dlp -f "ba" -x --audio-format mp3 -o "{output_filename}" {video_url} --quiet'

    process = await asyncio.create_subprocess_shell(
        command
    )

    await process.communicate()

    while process.returncode != 0:
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
    text = None
    try:
        text = msg.text.split()
    except:
        pass
    url = None
    try:
        for t in text:
            if is_url(t):
                url = t
    except:
        pass
    if not url:
        return

    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(url, download=False)
    title = info.get('title', None)
    description = info.get('description', None)

    await app.send_message(
        chat_id=msg.chat.id,
        reply_to_message_id=msg.id,
        reply_markup=generate_keyboard(get_video_id(url)),
        text=f"Название: {title}\n"
             f"Ссылка: {url}\n"
             f"Описание: \n{description}"
    )


@app.on_callback_query()
async def on_callback_query(client, callback_query: CallbackQuery):
    data = callback_query.data.split(':')
    video_id = data[0]
    download_type = data[1]
    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(
            download=False,
            url=f'https://youtu.be/{video_id}'
        )
    filename = video_id + '.mkv'
    telegram_filename = info['title'] + '.mkv'
    if download_type == 'audio':
        filename = video_id + '.mp3'
        telegram_filename = info['title'] + '.mp3'

    if f'{video_id}_{download_type}' in storage:
        if storage[f'{video_id}_{download_type}'] != None:
            if storage[f'{video_id}_{download_type}'] != "Working":
                file = storage[f'{video_id}_{download_type}']
                if download_type == 'video':
                    await app.send_chat_action(
                        chat_id=callback_query.message.chat.id,
                        action=enums.ChatAction.UPLOAD_VIDEO
                    )
                    await app.send_document(
                        chat_id=callback_query.message.chat.id,
                        reply_to_message_id=callback_query.message.id,
                        document=file,
                        file_name=telegram_filename
                    )
                else:
                    await app.send_chat_action(
                        chat_id=callback_query.message.chat.id,
                        action=enums.ChatAction.UPLOAD_AUDIO
                    )
                    await app.send_audio(
                        chat_id=callback_query.message.chat.id,
                        reply_to_message_id=callback_query.message.id,
                        audio=file,
                        file_name=telegram_filename
                    )
                return

    try:
        if f'{video_id}_{download_type}' in storage and storage[f'{video_id}_{download_type}'] == "Working":
            await callback_query.answer(
                text="⚙ Производится скачивание, пожалуйста подождите"
            )
            return

        await callback_query.answer(
            text="⚙ Обработка запроса"
        )
    except:
        return

    storage.update({f'{video_id}_{download_type}': "Working"})

    file_path = await download(f'https://youtu.be/{video_id}', download_type)
    await app.send_chat_action(
        chat_id=callback_query.message.chat.id,
        action=enums.ChatAction.UPLOAD_DOCUMENT
    )
    file = None
    if download_type == 'video':
        await app.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=enums.ChatAction.UPLOAD_VIDEO
        )
        file = await app.send_document(
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.id,
            document=file_path,
            file_name=telegram_filename
        )
    else:
        await app.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=enums.ChatAction.UPLOAD_AUDIO
        )
        file = await app.send_audio(
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.id,
            audio=file_path,
            file_name=telegram_filename
        )
    file_id = None
    if file.document:
        file_id = file.document.file_id
    elif file.video:
        file_id = file.video.file_id
    else:
        file_id = file.audio.file_id
    storage.update({f'{video_id}_{download_type}': file_id})
    os.remove(file_path)
    await save(storage)


if __name__ == '__main__':
    try:
        print("Bot is running")
        app.run()
    except KeyboardInterrupt:
        app.stop()
        pass