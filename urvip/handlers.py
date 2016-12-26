from datetime import datetime

import pyqrcode

from core.decorators import require_login
from core.handlers import PageHandler, ApiHandler
from urvip.models import Seller, Admin, ChargeRule, Customer


class LoginHandler(PageHandler):
    """登录
    """
    def get(self, *args, **kwargs):
        return self.render('urvip/login.html')

    def post(self, *args, **kwargs):
        cellphone = self.get_str_argument('cellphone')
        captcha = self.get_str_argument('captcha')
        try:
            admin = Admin.auth_by_captcha(self.db, cellphone, captcha)
        except:
            return self.redirect('login')
        else:
            session_id, expire_time = self.generate_session(admin.id, sellerId=admin.sellerId,
                                                            permissions=[], cellphone=cellphone)
            self.set_secure_cookie('sessionId', session_id, expires=expire_time)
            return self.redirect('/customers', permanent=False)


class SendCaptchaHandler(ApiHandler):
    """发送验证码
    """
    def post(self, *args, **kwargs):
        cellphone = self.get_str_argument('cellphone')
        Admin.send_auth_captcha(self.db, cellphone)
        return self.api_succeed()


class ChargeRulesHandler(PageHandler):
    """充值规则列表
    """
    @require_login
    def get(self, *args, **kwargs):
        charge_rules = ChargeRule.list(self.db, self.current_user.sellerId)
        return self.render('urvip/charge_rules.html', user_name=self.current_user.cellphone, charge_rules=charge_rules)


class AddChargeRuleHandler(ApiHandler):
    """添加充值规则
    """
    @require_login
    def post(self, *args, **kwargs):
        name = self.get_str_argument('name')
        payout = self.get_float_argument('payout')
        balance_change = self.get_float_argument('balanceChange')
        quantity_change = self.get_float_argument('quantityChange')
        score_change = self.get_float_argument('scoreChange')
        ChargeRule.add(self.db, self.current_user.sellerId, name, payout, balance_change, quantity_change, score_change)
        return self.api_succeed()


class DeleteChargeRuleHandler(ApiHandler):
    """删除充值规则
    """
    @require_login
    def post(self, *args, **kwargs):
        id = self.get_int_argument('id')
        ChargeRule.delete(self.db, self.current_user.sellerId, id)
        return self.api_succeed()


class CustomersHandler(PageHandler):
    """会员列表
    """
    @require_login
    def get(self, *args, **kwargs):
        page_num = self.get_int_argument('page')
        card = self.get_str_argument('card')
        cellphone = self.get_str_argument('cellphone')
        if not card and not cellphone:
            customers, page_num, page_count = Customer.list_by_page(self.db, self.current_user.sellerId, page_num)
        else:
            customer = Customer.get(self.db, self.current_user.sellerId, card=card, cellphone=cellphone)
            customers, page_num, page_count = [customer] if customer else [], 0, 1
        charge_rules = ChargeRule.list(self.db, self.current_user.sellerId)
        return self.render('urvip/customers.html',
                           user_name=self.current_user.cellphone,
                           customers=customers, page_num=page_num, page_count=page_count,
                           charge_rules=[r for r in charge_rules])


class AddCustomerHandler(ApiHandler):
    """添加会员
    """
    @require_login
    def post(self, *args, **kwargs):
        identification = self.get_str_argument('identification')
        name = self.get_str_argument('name')
        gender = self.get_int_argument('gender')
        cellphone = self.get_str_argument('cellphone')
        Customer.add(self.db, self.current_user.sellerId, identification, name, gender, cellphone)
        return self.api_succeed()


class DeleteCustomerHandler(ApiHandler):
    """删除会员
    """
    @require_login
    def post(self, *args, **kwargs):
        id = self.get_int_argument('id')
        Customer.delete(self.db, self.current_user.sellerId, id)
        return self.api_succeed()


class ChargeHandler(ApiHandler):
    """会员充值
    """
    @require_login
    def post(self, *args, **kwargs):
        customer_id = self.get_int_argument('customerId')
        old_update_time = self.get_float_argument('updateTime')
        charge_rule_id = self.get_int_argument('chargeRuleId')
        comments = self.get_str_argument('comments')
        Customer.charge(self.db, self.current_user.sellerId, customer_id, old_update_time, charge_rule_id, comments)
        return self.api_succeed()


class SendConsumeCaptchaHandler(ApiHandler):
    """发送消费验证码
    """
    @require_login
    def post(self, *args, **kwargs):
        customer_id = self.get_int_argument('customerId')
        cellphone = self.get_str_argument('cellphone')
        old_update_time = self.get_float_argument('updateTime')
        Customer.send_consume_captcha(self.db, self.current_user.sellerId, customer_id, cellphone, old_update_time)
        return self.api_succeed()


class ConsumeHandler(ApiHandler):
    """会员消费
    """
    @require_login
    def post(self, *args, **kwargs):
        customer_id = self.get_int_argument('customerId')
        old_update_time = self.get_float_argument('updateTime')
        balance_change = self.get_float_argument('balanceChange')
        quantity_change = self.get_int_argument('quantityChange')
        score_change = self.get_int_argument('scoreChange')
        comments = self.get_str_argument('comments')
        captcha = self.get_str_argument('captcha')
        Customer.consume(self.db, self.current_user.sellerId, customer_id, old_update_time,
                         balance_change, quantity_change, score_change, comments, captcha)
        return self.api_succeed()


class CustomerDetailHandler(PageHandler):
    """会员充值和消费的历史记录
    """
    @require_login
    def get(self, *args, **kwargs):
        id = self.get_int_argument('id')
        card = self.get_str_argument('card')
        cellphone = self.get_str_argument('cellphone')
        customer = Customer.get(self.db, self.current_user.sellerId, id=id, card=card, cellphone=cellphone)
        return self.render('urvip/customer_detail.html',
                           customer=customer, qr_code=pyqrcode.create(customer.card).text(),
                           transactions=[t for t in customer.transactions.limit(100)])


class DownloadCustomerDetailHandler(PageHandler):
    """下载会员充值和消费的历史记录
    """
    @require_login
    def get(self, *args, **kwargs):
        id = self.get_int_argument('id')
        customer = Customer.get(self.db, self.current_user.sellerId, id=id)
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition:', 'attachment;filename={0}-{1}.csv'
                        .format(customer.name, customer.cellphone[3:]))
        self.write('"姓名","{0}",\n'.format(customer.name))
        self.write('"性别","{0}",\n'.format({1: '男', 2: '女'}[customer.gender]))
        self.write('"身份证","{0}",\n'.format(customer.identification))
        self.write('"手机","{0}",\n'.format(customer.cellphone))
        self.write('"时间","类别","余额变动","次数变动","积分变动","剩余金额","剩余次数","剩余积分","备注"\n')
        for t in customer.transactions.limit(100):
            self.write('"{0}","{1}","{2}","{3}","{4}","{5}","{6}","{7}","{8}"\n'.
                       format(datetime.strftime(t.createTime, '%Y-%m-%d %H:%M'), {1: '充值', 5: '消费'}[t.kind],
                              t.balanceChange, t.quantityChange, t.scoreChange, t.balance, t.quantity, t.score,
                              t.comments))
        return self.finish()


class SellerTransactionsHandler(PageHandler):
    """商户所有会员的充值和消费记录
    """
    @require_login
    def get(self, *args, **kwargs):
        page_num = self.get_int_argument('page')
        transactions, page_num, page_count = Seller.list_transactions_by_page(self.db, self.current_user.sellerId,
                                                                              page_num)
        return self.render('urvip/seller_transactions.html',
                           user_name=self.current_user.cellphone,
                           transactions=transactions, page_num=page_num, page_count=page_count)


__handlers__ = [
    (r'^/login$', LoginHandler),
    (r'^/sendCaptcha$', SendCaptchaHandler),
    (r'^/chargeRules$', ChargeRulesHandler),
    (r'^/addChargeRule$', AddChargeRuleHandler),
    (r'^/deleteChargeRule$', DeleteChargeRuleHandler),
    (r'^/customers$', CustomersHandler),
    (r'^/addCustomer$', AddCustomerHandler),
    (r'^/deleteCustomer$', DeleteCustomerHandler),
    (r'^/charge$', ChargeHandler),
    (r'^/sendConsumeCaptcha', SendConsumeCaptchaHandler),
    (r'^/consume$', ConsumeHandler),
    (r'^/customerDetail$', CustomerDetailHandler),
    (r'^/downloadCustomerDetail$', DownloadCustomerDetailHandler),
    (r'^/sellerTransactions$', SellerTransactionsHandler)
]
