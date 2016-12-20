from io import BytesIO
from uuid import uuid4
import os

from PIL import Image
from mutagen import File as mutagenFile

from core.handlers import PageHandler, ApiHandler
from core.utils.oss import upload_oss


class HomePageHandler(PageHandler):
    """Home page
    """
    def get(self, *args, **kwargs):
        if not self.get_session():
            return self.redirect('/login', permanent=False)
        else:
            return self.redirect('/customers', permanent=False)


class UploadImageHandler(ApiHandler):
    """Upload image, only GIF, JPEG and PNG formats are allowed.
    """
    def post(self, *args, **kwargs):
        contents = self.request.files['file'][0]['body']
        if len(contents) > 2 * 1024 * 1024:
            return self.api_failed(4, 'Image file too large.')
        with Image.open(BytesIO(contents)) as image:
            if image.format not in {'GIF', 'JPEG', 'PNG'}:
                return self.api_failed(4, 'Invalid image format.')
            extension = 'jpg' if image.format == 'JPEG' else image.format.lower()
            url = upload_oss(contents, extension, image=True)
            return self.api_succeed({'url': url, 'width': image.width, 'height': image.height})


class UploadAudioHandler(ApiHandler):
    """Upload audio, only MP3 format is allowed.
    """
    def post(self, *args, **kwargs):
        contents = self.request.files['file'][0]['body']
        if len(contents) > 5 * 1024 * 1024:
            return self.api_failed(4, 'Audio file too large.')
        audio = mutagenFile(BytesIO(contents))
        if audio.mime[0] not in {'audio/mp3'}:
            return self.api_failed(4, 'Invalid audio format.')
        extension = audio.mime[0].split('/')[1].lower()
        url = upload_oss(contents, extension)
        return self.api_succeed({'url': url, 'duration': int(audio.info.length)})


class UploadVideoHandler(ApiHandler):
    """Upload video, only MP4 format is allowed.
    """
    def post(self, *args, **kwargs):
        # Video
        video_contents = self.request.files['file'][0]['body']
        if len(video_contents) > 10 * 1024 * 1024:
            return self.api_failed(4, 'Video file too large.')
        video_info = mutagenFile(BytesIO(video_contents))
        if video_info.mime[0] not in {'audio/mp4'}:
            return self.api_failed(4, 'Invalid video format.')
        video_extension = video_info.mime[0].split('/')[1].lower()
        # Cover image
        video_duration = int(video_info.info.length)
        cover_contents, cover_extension = self.capture(video_contents, video_extension, video_duration)
        # Do upload video and cover image
        video_url = upload_oss(video_contents, video_extension)
        with Image.open(BytesIO(cover_contents)) as cover:
            cover_url = upload_oss(cover_contents, cover_extension, image=True)
            return self.api_succeed({'url': video_url, 'duration': video_duration,
                                     'cover': {'url': cover_url, 'width': cover.width, 'height': cover.height}})

    @staticmethod
    def capture(video_contents, video_extension, video_duration):
        cover_extension = 'jpeg'
        name = str(uuid4()).replace('-', '')
        video_name = '{0}.{1}'.format(name, video_extension)
        cover_name = '{0}.{1}'.format(name, cover_extension)
        with open(video_name, 'wb') as video_file:
            video_file.write(video_contents)
        os.system('ffmpeg -loglevel error -y -ss {0} -i {1} -vframes 1 {2}'.format(min(1, video_duration),
                                                                                   video_name, cover_name))
        with open(cover_name, 'rb') as cover_file:
            cover_contents = cover_file.read()
        os.system('rm {0} {1}'.format(video_name, cover_name))
        return cover_contents, cover_extension


__handlers__ = [
    (r'^/$', HomePageHandler),
    (r'^/uploadImage$', UploadImageHandler),
    (r'^/uploadAudio$', UploadAudioHandler),
    (r'^/uploadVideo$', UploadVideoHandler)
]
