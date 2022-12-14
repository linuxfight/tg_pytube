from httpx import AsyncClient
import aiofiles


async def get_thumbnail(url, path):
    async with aiofiles.open(path, 'wb') as file:
        async with AsyncClient() as client:
            async with client.stream('GET', url) as stream:
                async for chunk in stream.aiter_bytes():
                    await file.write(chunk)

    return str(path)
