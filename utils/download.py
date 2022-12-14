import asyncio


async def download(video_url, download_type, video_format, path):
    command = f'yt-dlp -f {video_format}+bestaudio/best --merge-output-format mkv -o {path} {video_url} --quiet'

    if download_type == "audio":
        command = f'yt-dlp -f ba -x --audio-format m4a -o {path} {video_url} --quiet'

    process = await asyncio.create_subprocess_shell(
        command
    )

    await process.communicate()

    while process.returncode != 0:
        pass
    else:
        return path