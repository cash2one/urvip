import os

from tornado.options import options
import tornado.web
import tornado.httpserver
import tornado.ioloop

import config
from common.handlers import __handlers__ as common_handlers
from urvip.handlers import __handlers__ as urvip_handlers
from core.handlers import InvalidUrlHandler


def main():
    handlers = list()
    handlers.extend(common_handlers)
    handlers.extend(urvip_handlers)
    handlers.extend([(r'^.*$', InvalidUrlHandler)])
    application = tornado.web.Application(handlers=handlers, debug=options.debug, cookie_secret=options.cookie_secret,
                                          template_path=os.path.join(os.path.dirname(__file__), 'templates'))
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.bind(options.port)
    http_server.start(options.num_processes)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    main()
