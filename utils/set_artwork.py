from mutagen.mp4 import MP4, MP4Cover
from utils.thumbnail import get_thumbnail


def set_artist(path, artist):
    MP4file = MP4(path)
    MP4file.tags['\xa9ART'] = artist
    MP4file.save(path)


async def set_cover(directory, path, cover_url):
    MP4file = MP4(path)
    thumbnail = await get_thumbnail(cover_url, directory / 'cover.jpg')
    with open(thumbnail, 'rb') as f:
        albumart = MP4Cover(f.read())
    MP4file.tags['covr'] = [albumart]
    MP4file.save(path)