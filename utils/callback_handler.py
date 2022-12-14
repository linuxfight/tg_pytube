import yt_dlp

from tempfile import TemporaryDirectory
from pathlib import Path
from pyrogram import enums, Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from utils.storage import save, load
from utils.download import download
from utils.thumbnail import get_thumbnail
from utils.set_artwork import set_cover, set_artist

video_formats = [135, 136, 298, 137, 299, 400, 401]
storage: dict = load()


def resolution_keyboard(video_id):
    buttons = []

    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(
            download=False,
            url=f'https://youtu.be/{video_id}'
        )

    formats: list[dict] = info['formats']
    audio_formats = []

    for f in formats:
        if f['resolution'] == 'audio only':
            audio_formats.append(f)
        for video_format in video_formats:
            if str(video_format) == f['format_id']:
                file_size = int(f.get('filesize') / (1024 * 1024))
                if file_size is None:
                    file_size = int(f.get('filesize_approx') / (1024 * 1024))
                file_size += int(audio_formats[-1]['filesize'] / (1024 * 1024))
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=str(f['resolution']) + 'p ' + str(f['fps']) + 'fps ' + str(file_size) + 'MB',
                            callback_data=f'{video_id}:video:{str(f["format_id"])}'
                        )
                    ]
                )

    return InlineKeyboardMarkup(
        buttons
    )


async def on_callback_query(client: Client, callback_query: CallbackQuery):
    data = callback_query.data.split(':')
    video_id = data[0]
    download_type = data[1]
    video_format = 'best'
    ext = 'm4a'

    if len(data) == 3:
        video_format = data[2]
        ext = 'mkv'
    else:
        if download_type == 'video':
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                text='Выберите разрешение видео',
                reply_markup=resolution_keyboard(video_id)
            )
            return

    save_path = f'{video_id}:{download_type}:{video_format}'
    item = storage.get(save_path)

    if item == 'Working':
        await callback_query.answer(
            text='⚙ Производится скачивание, пожалуйста подождите'
        )
        return
    if item is None:
        storage.update({save_path: 'Working'})
    await callback_query.answer(
        text='⚙ Обработка запроса'
    )

    with yt_dlp.YoutubeDL() as ydl:
        info: dict = ydl.extract_info(
            download=False,
            url=f'https://youtu.be/{video_id}'
        )

        title = info['title']
        channel = info['channel']
        duration = int(info['duration'])
        thumbs: list[dict] = info['thumbnails']
        telegram_thumbs = []
        for t in thumbs:
            if 'resolution' in t:
                if t['height'] <= 320 and t['width'] <= 320:
                    telegram_thumbs.append(t)

    if item != 'Working' and item is not None:
        file = item
        if download_type == 'video':
            await client.send_chat_action(
                chat_id=callback_query.message.chat.id,
                action=enums.ChatAction.UPLOAD_VIDEO
            )
            await client.send_video(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                video=file
            )
            return
        await client.send_chat_action(
            chat_id=callback_query.message.chat.id,
            action=enums.ChatAction.UPLOAD_AUDIO
        )
        await client.send_audio(
            chat_id=callback_query.message.chat.id,
            reply_to_message_id=callback_query.message.id,
            audio=file
        )
        return

    with TemporaryDirectory() as temp:
        telegram_filename = title + f'.{ext}'
        telegram_thumb = await get_thumbnail(telegram_thumbs[-1]['url'], Path(temp) / 'telegram_thumb.jpg')
        path = await download(f'https://youtu.be/{video_id}', download_type, video_format, str(Path(temp) / f'{video_id}.{ext}'))
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
            file = await client.send_video(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                video=path,
                thumb=telegram_thumb,
                duration=duration,
                file_name=telegram_filename
            )
        else:
            await set_cover(Path(temp), path, info['thumbnails'][-1]['url'])
            set_artist(path, channel)
            await client.send_chat_action(
                chat_id=callback_query.message.chat.id,
                action=enums.ChatAction.UPLOAD_AUDIO
            )
            file = await client.send_audio(
                chat_id=callback_query.message.chat.id,
                reply_to_message_id=callback_query.message.id,
                audio=path,
                thumb=telegram_thumb,
                duration=duration,
                performer=channel,
                title=title,
                file_name=telegram_filename
            )

    file_id = None
    if file.video:
        file_id = file.video.file_id
    else:
        file_id = file.audio.file_id
    storage.update({save_path: file_id})
    await save(storage)
