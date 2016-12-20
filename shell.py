import config
from core.models import _engine, BaseModel, read_write_database
from urvip.models import Seller, Admin, ChargeRule, Customer, Transaction


BaseModel.metadata.create_all(_engine)
db = read_write_database()
