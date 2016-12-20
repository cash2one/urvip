from datetime import datetime
from uuid import uuid4

from tornado.options import options
from oss2 import Auth, Bucket


__auth = Auth(options.oss_access_key_id, options.oss_access_key_secret)
__bucket = Bucket(__auth, 'http://{0}'.format(options.oss_endpoint), options.oss_bucket_name)


def upload_oss(contents, extension, image=False, cache=False):
    for i in range(3):
        if cache:
            name = 'cache/{0}'.format(extension)
        else:
            name = '{0}.{1}'.format(str(uuid4()).replace('-', '')[:-len(extension) - 1], extension)
            name = '{0}/{1}'.format(datetime.now().year, name)
        if __bucket.object_exists(name):
            continue
        __bucket.put_object(name, contents)
        return 'http://{0}.{1}/{2}'.format(options.oss_bucket_name,
                                           options.oss_img_endpoint if image else options.oss_endpoint,
                                           name)
    raise Exception('Failed to upload to OSS due to duplicate object name.')
