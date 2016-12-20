import json
import re
from hashlib import md5
from random import random
import time
import logging

from tornado.options import options
import tornado.web
import redis

from core.models import read_write_database
from urvip.models import Admin


_int_pattern, _float_pattern = re.compile('^-?[0-9]+$'), re.compile('^-?[0-9]+(\.[0-9]+)?$')

_redis_session_db_pool = redis.ConnectionPool(host=options.redis_session_db_host,
                                              port=options.redis_session_db_port,
                                              db=options.redis_session_db_database,
                                              decode_responses=True,
                                              socket_timeout=options.redis_session_db_timeout)

_redis_cache_db_pool = redis.ConnectionPool(host=options.redis_cache_db_host,
                                            port=options.redis_cache_db_port,
                                            db=options.redis_cache_db_database,
                                            decode_responses=True,
                                            socket_timeout=options.redis_cache_db_timeout)


class BaseHandler(tornado.web.RequestHandler):
    """Base class for page handlers and API handlers.
    """
    def initialize(self):
        # Ensure that we are getting the real IP.
        if 'X-Real-Ip' in self.request.headers:
            self.request.remote_ip = self.request.headers['X-Real-Ip']

    def prepare(self):
        """Prepare database connection.
        """
        self.db = read_write_database()

    def on_finish(self):
        """Close database connection.
        """
        self.db.close()

    def get_str_argument(self, name, default='', strip=True):
        """Returns str value of the argument.
        """
        value = self.get_argument(name, default=default, strip=strip)
        return value if value else default

    def get_int_argument(self, name, default=0):
        """Returns int value of the argument.
        """
        raw_value = self.get_argument(name, '', strip=True)
        return int(raw_value) if _int_pattern.match(raw_value) else default

    def get_float_argument(self, name, default=0.0):
        """Returns float value of the argument.
        """
        raw_value = self.get_argument(name, '', strip=True)
        return float(raw_value) if _float_pattern.match(raw_value) else default

    def get_json_argument(self, name, default=None):
        """Returns JSON value of the argument.
        """
        raw_value = self.get_argument(name, None, strip=True)
        return json.loads(raw_value) if raw_value else default

    def generate_session(self, user_id, **session_data):
        """Generate a new session and return the session ID.
        """
        session_id = None
        session_data['userId'] = user_id
        session_data_str = json.dumps(session_data)
        timestamp = hex(int(time.time()))[2:]
        redis_client = redis.StrictRedis(connection_pool=_redis_session_db_pool)
        for retry_times in range(3):
            if retry_times > 0:
                logging.warning('Generated duplicate session ID, will try a new one.')
            session_id = md5(str(user_id).encode('utf-8')).hexdigest()
            session_id = '{1}{0}'.format(session_id, random())
            session_id = md5(session_id.encode('utf-8')).hexdigest()
            session_id = '{0}{1}'.format(session_id, random())
            session_id = md5(session_id.encode('utf-8')).hexdigest()
            session_id = '{0}{1}{2}'.format(timestamp, session_id[len(timestamp):len(session_id) - 1], retry_times)
            if redis_client.set(session_id, session_data_str, ex=options.session_expire_after, nx=True):
                break
        if redis_client.get(session_id) == session_data_str:
            return session_id, time.time() + options.session_expire_after
        else:
            return None, 0

    def get_session(self):
        """Get session data.
        """
        if not self.session_id:
            return None
        try:
            redis_client = redis.StrictRedis(connection_pool=_redis_session_db_pool)
            session_data = redis_client.get(self.session_id)
            return json.loads(session_data) if session_data else None
        except:
            return None

    def set_session(self, session_data):
        """Save session data.
        """
        if not self.session_id:
            return False
        session_data_str = json.dumps(session_data)
        redis_client = redis.StrictRedis(connection_pool=_redis_session_db_pool)
        return redis_client.set(self.session_id, session_data_str, ex=options.session_expire_after, xx=True)

    def invalidate_session(self):
        """Invalidate current session.
        """
        if not self.session_id:
            return
        redis_client = redis.StrictRedis(connection_pool=_redis_session_db_pool)
        redis_client.delete(self.session_id)

    def get_current_user(self):
        """Returns a fake user.
        """
        session = self.get_session()
        return Admin(id=session['userId'], sellerId=session['sellerId'],
                     cellphone=session['cellphone']) if session else None

    @property
    def session_id(self):
        """Returns current session ID.
        """
        raise NotImplementedError

    def on_login_required(self):
        """Generates output when login is required.
        """
        raise NotImplementedError

    def get_cache(self, key):
        """Get cached value.
        """
        redis_client = redis.StrictRedis(connection_pool=_redis_cache_db_pool)
        return redis_client.get(key)

    def set_cache(self, key, value, ex=None):
        """Set cache value.
        """
        redis_client = redis.StrictRedis(connection_pool=_redis_cache_db_pool)
        return redis_client.set(key, value, ex=ex)


class PageHandler(BaseHandler):
    """Base class for handlers rendering web pages.
    """
    @property
    def session_id(self):
        return self.get_secure_cookie('sessionId')

    def on_login_required(self):
        self.redirect('/login')


class ApiHandler(BaseHandler):
    def api_succeed(self, data=None):
        """Call this method when the API execution succeed.
        """
        self._api_finished(0, None, data)

    def api_failed(self, status=5, message='Failed.'):
        """Call this method when the API execution failed.
        """
        self._api_finished(status, message, None)

    def _api_finished(self, status, message, data):
        result = {'status': status}
        if message:
            result['message'] = message
        if data:
            result['data'] = data
        result_bytes = json.dumps(result).encode('utf-8')
        if options.debug and len(result_bytes) < 10000:
            logging.info(result)
        logging.info('Returned {0} bytes.'.format(len(result_bytes)))
        self.finish(result_bytes)

    @property
    def session_id(self):
        return self.get_secure_cookie('sessionId')

    def on_login_required(self):
        self.api_failed(7, 'Login required.')

    def write_error(self, status_code, **kwargs):
        """Customize error response.
        """
        if status_code == 403:
            self.api_failed(4, 'Forbidden.')
        elif status_code == 404:
            self.api_failed(4, 'Forbidden.')
            logging.warning('Invalid URL. ({0})'.format(self.request.remote_ip))
        elif status_code == 405:
            self.api_failed(4, 'Forbidden.')
            logging.warning('Invalid request method. ({0})'.format(self.request.remote_ip))
        elif status_code == 500:
            self.api_failed(5, 'Internal error.')
            logging.warning('Internal error. ({0})'.format(self.request.remote_ip))
        else:
            self.api_failed(5, 'Internal error.')
            logging.warning('HTTP error {0}. ({1})'.format(status_code, self.request.remote_ip))


class InvalidUrlHandler(BaseHandler):
    """Handles invalid URLs.
    """
    def head(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def get(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def post(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def delete(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def patch(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def put(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)

    def options(self, *args, **kwargs):
        raise tornado.web.HTTPError(404)
