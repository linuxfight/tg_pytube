import asyncio
import logging

from utils.get_video_id import get_video_id
from os.path import exists


async def download(video_url, download_type, video_format):
    logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
    video_id = get_video_id(video_url)
    output_filename = video_id + '.mkv'
    command = f'yt-dlp -f {video_format}+bestaudio/best --merge-output-format mkv -o "{output_filename}" {video_url}' # --quiet

    if download_type == "audio":
        output_filename = video_id + '.m4a'
        command = f'yt-dlp -f "ba" -x --audio-format m4a -o "{output_filename}" {video_url} --quiet'

    process = await asyncio.create_subprocess_shell(
        command
    )

    await process.communicate()

    while process.returncode != 0:
        if process.returncode == 1:
            logging.exception("message")
        pass
    else:
        while not exists(output_filename):
            pass
        else:
            return output_filename
