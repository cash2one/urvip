from datetime import datetime
from random import random
from uuid import uuid4

from sqlalchemy import Column, BigInteger, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from core.models import BaseModel, paginate
from core.utils.sms import send_sms


class Seller(BaseModel):
    """商户
    """
    __tablename__ = 'seller'
    id = Column('id', BigInteger, primary_key=True)
    name = Column('name', String(40))
    weChatAccount = Column('we_chat_account', String(40))
    identificationKind = Column('identification_kind', Integer)
    identification = Column('identification', String(40))
    address = Column('address', String(120))
    zipCode = Column('zip_code', String(10))
    chargeRules = relationship('ChargeRule', back_populates='seller', lazy='dynamic')
    scoreRate = Column('score_rate', Float)
    admins = relationship('Admin', back_populates='seller', lazy='dynamic')
    customers = relationship('Customer', back_populates='seller', lazy='dynamic')
    status = Column('status', Integer)
    createTime = Column('create_time', DateTime)
    updateTime = Column('update_time', DateTime)

    @staticmethod
    def add(db, name, we_chat_account, score_rate=0):
        """添加商户
        """
        now = datetime.now()
        seller = Seller(name=name, weChatAccount=we_chat_account, scoreRate=score_rate,
                        status=1, createTime=now, updateTime=now)
        db.add(seller)
        db.commit()
        return seller

    @staticmethod
    def delete(db, seller_id):
        """删除商户
        """
        now = datetime.now()
        seller = db.query(Seller).filter(Seller.id == seller_id).one()
        for admin in seller.admins:
            admin.status = 9
            admin.updateTime = now
            db.merge(admin)
        seller.status = 9
        seller.updateTime = now
        db.merge(seller)
        db.commit()

    @staticmethod
    def list_transactions_by_page(db, seller_id, page_num, page_size=10):
        """商户所有会员的充值和消费记录
        """
        cursor = db.query(Transaction).join(Transaction.customer)\
                   .filter(Customer.sellerId == seller_id)\
                   .order_by(Transaction.createTime.desc())
        total_count = cursor.count()
        page_num, page_count = paginate(total_count, page_num, page_size)
        transactions = cursor.offset(page_num * page_size).limit(page_size)
        return [t for t in transactions], page_num, page_count


class Admin(BaseModel):
    """商户管理员
    """
    __tablename__ = 'admin'
    id = Column('id', BigInteger, primary_key=True)
    sellerId = Column('seller_id', BigInteger, ForeignKey('seller.id'))
    seller = relationship('Seller', foreign_keys=sellerId, back_populates='admins')
    cellphone = Column('cellphone', String(20), unique=True)
    cellphoneAuthCaptcha = Column('cellphone_auth_captcha', String(6))
    cellphoneAuthCaptchaExpireTime = Column('cellphone_auth_captcha_expire_time', DateTime)
    status = Column('status', Integer)
    createTime = Column('create_time', DateTime)
    updateTime = Column('update_time', DateTime)

    @staticmethod
    def add(db, seller_id, cellphone):
        """为商户添加管理员帐号
        """
        now = datetime.now()
        seller = db.query(Seller).filter(Seller.id == seller_id, Seller.status == 1).one()
        admin = Admin(sellerId=seller.id, cellphone=cellphone, status=1, createTime=now, updateTime=now)
        db.add(admin)
        db.commit()
        return admin

    @staticmethod
    def send_auth_captcha(db, cellphone):
        """向商户管理员帐号发送验证码
        """
        captcha = str(random())[2:8]
        now = datetime.now()
        admin = db.query(Admin).filter(Admin.cellphone == cellphone, Admin.status == 1).one()
        admin.cellphoneAuthCaptcha = captcha
        admin.cellphoneAuthCaptchaExpireTime = datetime.fromtimestamp(now.timestamp() + 10 * 60)
        admin.updateTime = now
        db.merge(admin)
        db.commit()
        send_sms(cellphone, '登录验证码:{0}'.format(captcha))

    @staticmethod
    def auth_by_captcha(db, cellphone, captcha):
        """验证商户管理员帐号的验证码
        """
        now = datetime.now()
        admin = db.query(Admin).filter(Admin.cellphone == cellphone, Admin.status == 1,
                                       Admin.cellphoneAuthCaptcha == captcha,
                                       Admin.cellphoneAuthCaptchaExpireTime > now).one()
        admin.cellphoneAuthCaptcha = None
        admin.cellphoneAuthCaptchaExpireTime = None
        admin.updateTime = now
        db.merge(admin)
        db.commit()
        return admin


class ChargeRule(BaseModel):
    """商户充值规则
    """
    __tablename__ = 'charge_rule'
    id = Column('id', BigInteger, primary_key=True)
    sellerId = Column('seller_id', BigInteger, ForeignKey('seller.id'))
    seller = relationship('Seller', foreign_keys=sellerId, back_populates='chargeRules')
    name = Column('name', String(20))
    payout = Column('payout', Float)
    balanceChange = Column('balance_change', Float)
    quantityChange = Column('quantity_change', Integer)
    scoreChange = Column('score_change', Integer)
    status = Column('status', Integer)
    createTime = Column('create_time', DateTime)
    updateTime = Column('update_time', DateTime)

    @staticmethod
    def list(db, seller_id):
        """充值规则列表
        """
        charge_rules = db.query(ChargeRule).filter(ChargeRule.sellerId == seller_id, ChargeRule.status == 1)
        return [r for r in charge_rules]

    @staticmethod
    def add(db, seller_id, name, payout, balance_change, quantity_change, score_change):
        """创建充值规则
        """
        now = datetime.now()
        charge_rule = ChargeRule(sellerId=seller_id, name=name, payout=payout, balanceChange=balance_change,
                                 quantityChange=quantity_change, scoreChange=score_change, status=1,
                                 createTime=now, updateTime=now)
        db.add(charge_rule)
        db.commit()
        return charge_rule

    @staticmethod
    def delete(db, seller_id, charge_rule_id):
        """删除充值规则
        """
        now = datetime.now()
        charge_rule = db.query(ChargeRule).filter(ChargeRule.id == charge_rule_id,
                                                  ChargeRule.sellerId == seller_id).one()
        charge_rule.status = 9
        charge_rule.updateTime = now
        db.merge(charge_rule)
        db.commit()


class Transaction(BaseModel):
    """会员充值、消费记录
    """
    __tablename__ = 'transaction'
    id = Column('id', BigInteger, primary_key=True)
    customerId = Column('customer_id', BigInteger, ForeignKey('customer.id'))
    customer = relationship('Customer', foreign_keys=customerId, back_populates='transactions')
    kind = Column('kind', Integer)
    balanceChange = Column('balance_change', Float)
    balance = Column('balance', Float)
    quantityChange = Column('quantity_change', Integer)
    quantity = Column('quantity', Integer)
    scoreChange = Column('score_change', Integer)
    score = Column('score', Integer)
    comments = Column('comments', String(120))
    createTime = Column('create_time', DateTime)


class Customer(BaseModel):
    """会员
    """
    __tablename__ = 'customer'
    id = Column('id', BigInteger, primary_key=True)
    sellerId = Column('seller_id', BigInteger, ForeignKey('seller.id'))
    seller = relationship('Seller', foreign_keys=sellerId, back_populates='customers')
    identification = Column('identification', String(20))
    name = Column('name', String(20))
    gender = Column('gender', Integer)
    cellphone = Column('cellphone', String(20), index=True)
    weChatOpenId = Column('we_chat_open_id', String(30))
    nickName = Column('nick_name', String(20))
    avatar = Column('avatar', String(256))
    card = Column('card', String(32), unique=True)
    address = Column('address', String(120))
    zipCode = Column('zip_code', String(10))
    balance = Column('balance', Float)
    quantity = Column('quantity', Integer)
    score = Column('score', Integer)
    level = Column('level', Integer)
    cellphoneConsumeCaptcha = Column('cellphone_consume_captcha', String(6))
    cellphoneConsumeCaptchaExpireTime = Column('cellphone_consume_captcha_expire_time', DateTime)
    transactions = relationship('Transaction', order_by='Transaction.createTime.desc()',
                                back_populates='customer', lazy='dynamic')
    status = Column('status', Integer)
    createTime = Column('create_time', DateTime)
    updateTime = Column('update_time', DateTime)

    @staticmethod
    def get(db, seller_id, id=None, card=None, cellphone=None):
        """查找会员
        """
        if id:
            return db.query(Customer).filter(Customer.id == id,
                                             Customer.sellerId == seller_id,
                                             Customer.status == 1).first()
        elif card:
            return db.query(Customer).filter(Customer.card == card,
                                             Customer.sellerId == seller_id,
                                             Customer.status == 1).first()
        elif cellphone:
            return db.query(Customer).filter(Customer.cellphone == cellphone,
                                             Customer.sellerId == seller_id,
                                             Customer.status == 1).first()
        else:
            raise Exception

    @staticmethod
    def list_by_page(db, seller_id, page_num, page_size=10):
        """会员分页列表
        """
        cursor = db.query(Customer)\
                   .filter(Customer.sellerId == seller_id, Customer.status == 1)\
                   .order_by(Customer.updateTime.desc())
        total_count = cursor.count()
        page_num, page_count = paginate(total_count, page_num, page_size)
        customers = cursor.offset(page_num * page_size).limit(page_size)
        return [c for c in customers], page_num, page_count

    @staticmethod
    def add(db, seller_id, identification, name, gender, cellphone):
        """添加会员
        """
        now = datetime.now()
        customer = Customer(sellerId=seller_id, identification=identification, name=name, gender=gender,
                            cellphone=cellphone, weChatOpenId='', card=str(uuid4()).replace('-', ''),
                            address='', zipCode='', balance=0, quantity=0, score=0, level=1, status=1,
                            createTime=now, updateTime=now)
        db.add(customer)
        db.commit()
        return customer

    @staticmethod
    def delete(db, seller_id, customer_id):
        """删除会员
        """
        now = datetime.now()
        customer = db.query(Customer).filter(Customer.id == customer_id,
                                             Customer.sellerId == seller_id).one()
        customer.status = 9
        customer.updateTime = now
        db.merge(customer)
        db.commit()

    @staticmethod
    def charge(db, seller_id, customer_id, old_update_time, charge_rule_id, comments):
        """会员充值
        """
        now = datetime.now()
        customer = db.query(Customer).filter(Customer.id == customer_id,
                                             Customer.updateTime == datetime.fromtimestamp(old_update_time),
                                             Customer.sellerId == seller_id,
                                             Customer.status == 1).one()
        charge_rule = db.query(ChargeRule).filter(ChargeRule.id == charge_rule_id,
                                                  ChargeRule.sellerId == seller_id,
                                                  ChargeRule.status == 1).one()
        balance = customer.balance + charge_rule.balanceChange
        quantity = customer.quantity + charge_rule.quantityChange
        score = customer.score + charge_rule.scoreChange
        # 写充值记录
        transaction = Transaction(customerId=customer.id, kind=1,
                                  balanceChange=charge_rule.balanceChange, balance=balance,
                                  quantityChange=charge_rule.quantityChange, quantity=quantity,
                                  scoreChange=charge_rule.scoreChange, score=score,
                                  comments=comments, createTime=now)
        db.add(transaction)
        # 为帐号充值
        if db.query(Customer)\
                .filter(Customer.id == customer_id,
                        Customer.status == 1,
                        Customer.updateTime == datetime.fromtimestamp(old_update_time))\
                .with_lockmode('update')\
                .update({'balance': balance, 'quantity': quantity, 'score': score, 'updateTime': now}):
            db.commit()
        else:
            db.rollback()
        return customer

    @staticmethod
    def send_consume_captcha(db, seller_id, customer_id, cellphone, old_update_time):
        """发送消费验证码
        """
        now = datetime.now()
        captcha = str(random())[2:8]
        if db.query(Customer) \
                .filter(Customer.id == customer_id,
                        Customer.sellerId == seller_id,
                        Customer.cellphone == cellphone,
                        Customer.status == 1,
                        Customer.updateTime == datetime.fromtimestamp(old_update_time)) \
                .with_lockmode('update') \
                .update({'cellphoneConsumeCaptcha': captcha,
                         'cellphoneConsumeCaptchaExpireTime': datetime.fromtimestamp(now.timestamp() + 10 * 60)}):
            db.commit()
            send_sms(cellphone, '消费验证码:{0}'.format(captcha))
        else:
            db.rollback()
        return

    @staticmethod
    def consume(db, seller_id, customer_id, old_update_time,
                balance_change=0, quantity_change=0, score_change=0, comments=None, captcha=None):
        """会员消费
        """
        if balance_change > 0 or quantity_change > 0 or score_change > 0:
            raise Exception
        if balance_change == 0 and quantity_change == 0 and score_change == 0:
            raise Exception
        now = datetime.now()
        customer = db.query(Customer).filter(Customer.id == customer_id,
                                             Customer.sellerId == seller_id,
                                             Customer.status == 1,
                                             Customer.updateTime == datetime.fromtimestamp(old_update_time)).one()
        if captcha and (not customer.cellphoneConsumeCaptcha or
                        not customer.cellphoneConsumeCaptchaExpireTime or
                        captcha != customer.cellphoneConsumeCaptcha or
                        customer.cellphoneConsumeCaptchaExpireTime < now):
            raise Exception
        balance = customer.balance + balance_change
        quantity = customer.quantity + quantity_change
        score_change += -balance_change * customer.seller.scoreRate
        score = customer.score + score_change
        if balance < 0 or quantity < 0 or score < 0:
            raise Exception
        # 写消费记录
        transaction = Transaction(customerId=customer.id, kind=5,
                                  balanceChange=balance_change, balance=balance,
                                  quantityChange=quantity_change, quantity=quantity,
                                  scoreChange=score_change, score=score,
                                  comments=comments, createTime=now)
        db.add(transaction)
        # 消费
        if db.query(Customer) \
                .filter(Customer.id == customer_id,
                        Customer.sellerId == seller_id,
                        Customer.status == 1,
                        Customer.updateTime == datetime.fromtimestamp(old_update_time)) \
                .with_lockmode('update') \
                .update({'balance': balance, 'quantity': quantity, 'score': score,
                         'cellphoneConsumeCaptcha': None, 'cellphoneConsumeCaptchaExpireTime': None,
                         'updateTime': now}):
            db.commit()
        else:
            db.rollback()
        return
