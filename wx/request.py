"""请求测试"""
import requests
import json
from hashlib import md5


# ------------------------调用示例-----------------------------
def calculate(data):
    """
    微服务加密
    token算法:
    1，传入参数字典排序
    3，md5加密，得到token
    2，整理成字符串 加上 '自定义字符串'
    """
    sorted_key = sorted(data.keys())
    key_value = (key + data[key] for key in sorted_key)
    string = ''.join(key_value) + '自定义字符串'
    data['token'] = md5(string.encode()).hexdigest()
    return data

url = 'http://0.0.0.0:8888/wx/refund/'
# 过微服务验证
headers = {'identity': '7dbcc9e0926eae2b57d6043e4c4698a1'}

data = {
    "out_trade_no": '11111111111111113',  # 单号
    'out_refund_no':"11111111111111113",  # 退款单号
    "body": 'ceshibody',  # 内容
    "total_fee": '0.01',  # 价格元
    'refund_fee': '0.01',
    "spbill_create_ip": '151.221.150.128',  # 用户IP
    "trade_type": 'APP'  # 支付方式
}

# 微服务验证算法
data = calculate(data)
print(data)
# 传json格式数据
r = requests.post(url=url, headers=headers, data=json.dumps(data))
print(r.json())

# ------------------------------------------------------------------
# APP支付rsp示例
# 下单，成功后微信会往回调连接发消息验证，包含订单
unified_order = {'return_code': 'SUCCESS', 'return_msg': 'OK',
                 'appid': 'wx4d89fdb3c4a613b8', 'mch_id': '1442791802',
                 'device_info': 'WEB', 'nonce_str': 'NXxKmyOp46sThqdl',
                 'sign': 'BC150421AF70033ECDE48D65A3AF1FCB', 'result_code': 'SUCCESS',
                 'prepay_id': 'wx201706151354008bb58d41d10347109982', 'trade_type': 'APP'}
# 微服务整理后，直接给前端调起支付的数据
info = {'appid': 'wx4d89fdb3c4a613b8',
        'partnerid': '1442791802',
        'prepayid': 'wx201706151533142b8d7c639b0133738675',
        'package': 'Sign=WXPay',
        'noncestr': 'amlg8z8mdy05xchafo529z4gngkyr4hn',
        'timestamp': '1497511994',
        'sign': 'A2C1142DEECD87264491D2733BAC7237'}

# 查询订单
order_query = {'return_code': 'SUCCESS', 'return_msg': 'OK',
               'appid': 'wx4d89fdb3c4a613b8', 'mch_id': '1442791802',
               'nonce_str': 'XOcS0Gs56lHSBCNy', 'sign': 'DDCDAF6F66F41D63141CEA3471DB7B03',
               'result_code': 'SUCCESS', 'out_trade_no': '1111111111111111',
               'trade_state': 'NOTPAY', 'trade_state_desc': '订单未支付'
               }
# 关闭订单
close_order = {'return_code': 'SUCCESS', 'return_msg': 'OK',
               'appid': 'wx4d89fdb3c4a613b8', 'mch_id': '1442791802',
               'sub_mch_id': None, 'nonce_str': 'J59TSM3tom3xrxjj',
               'sign': '7D21B66178F5CBE7BBD5EAE1A6F1D6EB', 'result_code': 'SUCCESS'}


from xml.etree import ElementTree as etree

def to_dict(content):
    raw = {}
    root = etree.fromstring(content)
    for child in root:
        raw[child.tag] = child.text
    return raw

# 返回示例
def payr_eturn(request):
    informXml = request.body.decode()
    # Xml转字典
    informJson = to_dict(informXml)
    return_code = informJson["return_code"]
    result_code = informJson["result_code"]
    xmlre = '<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>'
    if return_code == "SUCCESS" and result_code == 'SUCCESS':
        print("-----支付成功--------")
        transaction_id = informJson["transaction_id"]
        openid = informJson["openid"]
        out_trade_no = informJson["out_trade_no"]  # 订单号
        order = models.Order.objects.get(order_no=out_trade_no)
        if order.state == 1:
            return HttpResponse(xmlre, content_type="application/xml")
        else:
            # 修改订单状态
            order.state = 1
            # 写入相关支付信息
            payment = models.Payment()
            payment.order = order
            payment.pay_type = order.pay_type
            payment.wx_price = order.real_cost
            payment.coupon_price = order.total_cost - order.real_cost
            payment.out_trade_no = out_trade_no
            payment.transaction_id = transaction_id
            payment.open_id = openid
            payment.save()
        order.save()
        return HttpResponse(xmlre, content_type="application/xml")
