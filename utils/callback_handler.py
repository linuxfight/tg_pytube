import yt_dlp
import os
from pyrogram import enums, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.storage import save, load
from utils.download import download


storage = load()
video_resolutions = [144, 240, 360, 480, 720, 1080, 1440, 2160]


def generate_keyboard(video_id):
    buttons = []

    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(
            download=False,
            url=f'https://youtu.be/{video_id}'
        )

    formats = info['formats']

    for f in formats:
        if f['resolution'] != 'audio only':
            if f['height'] in video_resolutions and f['video_ext'] == 'mp4' and not f['acodec'] and 'avc1' in f['vcodec']:
                buttons.append(
                    InlineKeyboardButton(
                        text=str(f['height']) + 'p',
                        callback_data=video_id + ':video:' + str(f['format_id'])
                    )
                )

    return InlineKeyboardMarkup(
        [buttons]
    )


async def on_callback_query(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split(':')
    video_id = data[0]
    download_type = data[1]
    video_format = 'only'

    if len(data) == 3:
        video_format = f'{data[2]}'
    else:
        if download_type == 'video':
            print(generate_keyboard(video_id))
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                text='Выберите разрешение видео',
                reply_markup=generate_keyboard(video_id)
            )
            return

    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(
            download=False,
            url=f'https://youtu.be/{video_id}'
        )
    telegram_filename = info['title'] + '.mkv'
    if download_type == 'audio':
        telegram_filename = info['title'] + '.mp3'

    if f'{video_id}_{download_type}_{video_format}' in storage:
        if storage[f'{video_id}_{download_type}_{video_format}'] is None:
            return
        if storage[f'{video_id}_{download_type}_{video_format}'] != "Working":
            file = storage[f'{video_id}_{download_type}_{video_format}']
            if download_type == 'video':
                await client.send_chat_action(
                    chat_id=callback_query.message.chat.id,
                    action=enums.ChatAction.UPLOAD_VIDEO
                )
                await client.send_document(
                    chat_id=callback_query.message.chat.id,
                    reply_to_message_id=callback_query.message.id,
                    document=file,
                    file_name=telegram_filename,
                    caption=f'[Ссылка](https://youtu.be/{video_id})'
                )
            else:
                await client.send_chat_action(
                    chat_id=callback_query.message.chat.id,
                    action=enums.ChatAction.UPLOAD_AUDIO
                )
                await client.send_audio(
                    chat_id=callback_query.message.chat.id,
                    reply_to_message_id=callback_query.message.id,
                    audio=file,
                    file_name=telegram_filename,
                    caption=f'[Ссылка](https://youtu.be/{video_id})'
                )
            return

    try:
        if f'{video_id}_{download_type}_{video_format}' in storage and storage[f'{video_id}_{download_type}_{video_format}'] == "Working":
            await callback_query.answer(
                text="⚙ Производится скачивание, пожалуйста подождите"
            )
            return

        await callback_query.answer(
            text="⚙ Обработка запроса"
        )
    except:
        return

    storage.update({f'{video_id}_{download_type}_{video_format}': "Working"})

    file_path = await download(f'https://youtu.be/{video_id}', download_type, video_format)
    await client.send_chat_action(
        chat_id=callback_query.message.chat.id,
        action=enums.ChatAction.UPLOAD_DOCUMENT
    )
    file = None
    if download_type == 'video':
        await client.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=enums.ChatAction.UPLOAD_VIDEO
        )
        file = await client.send_document(
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.id,
            document=file_path,
            file_name=telegram_filename,
            caption=f'[Ссылка](https://youtu.be/{video_id})'
        )
    else:
        await client.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=enums.ChatAction.UPLOAD_AUDIO
        )
        file = await client.send_audio(
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.id,
            audio=file_path,
            file_name=telegram_filename,
            caption=f'[Ссылка](https://youtu.be/{video_id})'
        )
    file_id = None
    if file.document:
        file_id = file.document.file_id
    elif file.video:
        file_id = file.video.file_id
    else:
        file_id = file.audio.file_id
    storage.update({f'{video_id}_{download_type}_{video_format}': file_id})
    os.remove(file_path)
    await save(storage)
