# 标准库
import time
import string
import random
import hashlib
from xml.etree import ElementTree as etree

# 三方库
import requests

# import 限制
__all__ = ("WeixinPayError", "WeixinPay")

# 全局变量
FAIL = "FAIL"
SUCCESS = "SUCCESS"


class WeixinError(Exception):
    def __init__(self, msg):
        super(WeixinError, self).__init__(msg)


class Map(dict):
    """
    提供字典的dot访问模式
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """

    def __init__(self, *args, **kwargs):
        super(Map, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    if isinstance(v, dict):
                        v = Map(v)
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                if isinstance(v, dict):
                    v = Map(v)
                self[k] = v

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __getitem__(self, key):
        if key not in self.__dict__:
            super(Map, self).__setitem__(key, {})
            self.__dict__.update({key: Map()})
        return self.__dict__[key]

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]


class WeixinPayError(WeixinError):
    def __init__(self, msg):
        super(WeixinPayError, self).__init__(msg)


class WeixinPay(object):
    def __init__(self, app_id, mch_id, mch_key, notify_url, key=None, cert=None):
        # id
        self.app_id = app_id
        # mchid
        self.mch_id = mch_id
        # api key
        self.mch_key = mch_key
        # 回调链接
        self.notify_url = notify_url
        # 证书key
        self.key = key
        # 证书
        self.cert = cert
        self.sess = requests.Session()

    @property
    def nonce_str(self):
        char = string.ascii_letters + string.digits
        return "".join(random.choice(char) for _ in range(32))

    def sign(self, raw):
        raw = [(k, str(raw[k]) if isinstance(raw[k], int) else raw[k])
               for k in sorted(raw.keys())]
        s = "&".join("=".join(kv) for kv in raw if kv[1])
        s += "&key={0}".format(self.mch_key)
        return hashlib.md5(s.encode("utf-8")).hexdigest().upper()

    def check(self, data):
        sign = data.pop("sign")
        return sign == self.sign(data)

    def to_xml(self, raw):
        s = ""
        for k, v in raw.items():
            s += "<{0}>{1}</{0}>".format(k, v)
        s = "<xml>{0}</xml>".format(s)
        return s.encode("utf-8")

    def to_dict(self, content):
        raw = {}
        root = etree.fromstring(content)
        for child in root:
            raw[child.tag] = child.text
        return raw

    def _fetch(self, url, data, use_cert=False):
        data.setdefault("appid", self.app_id)
        data.setdefault("mch_id", self.mch_id)
        data.setdefault("nonce_str", self.nonce_str)
        data.setdefault("sign", self.sign(data))

        if use_cert:
            resp = self.sess.post(url, data=self.to_xml(data), cert=(self.cert, self.key))
        else:
            resp = self.sess.post(url, data=self.to_xml(data))
        content = resp.content.decode("utf-8")
        if "return_code" in content:
            data = Map(self.to_dict(content))
            if data.return_code == FAIL:
                raise WeixinPayError(data.return_msg)
            if "result_code" in content and data.result_code == FAIL:
                raise WeixinPayError(data.err_code_des)
            return data
        return content

    def reply(self, msg, ok=True):
        code = SUCCESS if ok else FAIL
        return self.to_xml(dict(return_code=code, return_msg=msg))

    def unified_order(self, data):
        """
        统一下单
        out_trade_no、body、total_fee、trade_type必填
        app_id, mchid, nonce_str自动填写
        """
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        # 关联参数
        if data["trade_type"] == "JSAPI" and "openid" not in data:
            raise WeixinPayError("trade_type为JSAPI时，openid为必填参数")
        raw = self._fetch(url, data)
        return raw

    def order_query(self, data):
        """
        订单查询
        out_trade_no必填
        """
        url = "https://api.mch.weixin.qq.com/pay/orderquery"
        return self._fetch(url, data)

    def close_order(self, data):
        """
        关闭订单
        out_trade_no必填
        """
        url = "https://api.mch.weixin.qq.com/pay/closeorder"

        return self._fetch(url, data)

    def refund(self, data):
        """
        申请退款
        out_trade_no、out_refund_no、total_fee、refund_fee、op_user_id为必填参数
        """
        if not self.key or not self.cert:
            raise WeixinError("退款申请接口需要双向证书")
        url = "https://api.mch.weixin.qq.com/secapi/pay/refund"
        return self._fetch(url, data, True)

    def refund_query(self, data):
        """
        查询退款
        提交退款申请后，通过调用该接口查询退款状态。退款有一定延时，
        用零钱支付的退款20分钟内到账，银行卡支付的退款3个工作日后重新查询退款状态。
       out_trade_no必填
        """
        url = "https://api.mch.weixin.qq.com/pay/refundquery"
        return self._fetch(url, data)

