import asyncio


async def download(video_url, download_type, video_format, file_ext, directory):
    output = directory / f'video.{file_ext}'
    command = f'yt-dlp -f {video_format}+bestaudio/best --merge-output-format {file_ext} -o {output} {video_url} --quiet'

    if download_type == "audio":
        output = directory / f'audio.{file_ext}'
        command = f'yt-dlp -f ba -x --audio-format {file_ext} -o {output} {video_url} --quiet'

    process = await asyncio.create_subprocess_shell(
        command
    )

    await process.communicate()

    while process.returncode != 0:
        pass
    else:
        return output
