import asyncio


async def download(video_url, download_type, video_format, directory):
    output = directory / 'video.webm'
    command = f'yt-dlp -f {video_format}+bestaudio/best -o {output} {video_url} --quiet'

    if download_type == "audio":
        output = directory / 'audio.m4a'
        command = f'yt-dlp -f ba -x --audio-format m4a -o {output} {video_url} --quiet'

    process = await asyncio.create_subprocess_shell(
        command
    )

    await process.communicate()

    while process.returncode != 0:
        pass
    else:
        return output
