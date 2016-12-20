import math

from tornado.options import options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


_engine = create_engine('mysql+pymysql://{3}:{4}@{0}:{1}/{2}?charset=utf8mb4'
                        .format(options.mysql_host, options.mysql_port, options.mysql_database,
                                options.mysql_user, options.mysql_password),
                        echo=options.debug)
_read_write_database = sessionmaker(bind=_engine)()
BaseModel = declarative_base()


def read_write_database():
    """Connect to the master database
    """
    return _read_write_database


def paginate(total_count, page_num, page_size):
    """Calculate page number and page count
    """
    page_count = max(math.ceil(total_count / page_size), 1)
    if page_num > page_count - 1:
        page_num = page_count - 1
    if page_num < 0:
        page_num = 0
    return page_num, page_count
