"""
兼容小程序支付和app支付的微服务，支付参数放本地数据库
资金回滚需要双向证书
证书cert放在(/wx/cert/app名字/..cert.pem)括号内路径存在数据库中
证书key放在/wx/cert/app名字/..key.pem
"""
# 标准库应用
import time, json, logging

# 三方库引用
from django.http import JsonResponse

# 内部引用
from . import wx_tool
from . import models
from wx.decorator import login_request, check_method
from payapi import settings
from .pay import WeixinPay

# 全局变量
log = logging.getLogger('weixin')


def index(req):
    return JsonResponse(settings.BASE_DIR)


# 反回code,供计算identity
@check_method(['GET'])
def get_code(req):
    """获取计算identity的code"""
    name = req.GET['name']
    app = models.App.objects.get(name=name)
    try:
        code = wx_tool.nonce_str()
        identity = wx_tool.get_md5('自定义字符串' + wx_tool.get_md5(code))
        app.identity = identity
        app.save()
        log.info('{},{}'.format('获取code', {'code': code, 'identity': identity}))
        return JsonResponse({'status': 'success', 'code': code, })
    except models.App.DoesNotExist:
        return JsonResponse({'return_code': 'FAIL', 'error': 'App不存在'})


@login_request
@check_method(['POST'])
def unified_order(req):
    """商户系统先调用该接口在微信支付服务后台生成预支付交易单，
    返回正确的预支付交易回话标识后再在APP里面调起支付。"""
    data = json.loads(req.body)
    # 参数说明
    # out_trade_no      商户订单号 	     ex:20150806125346
    # body              商品描述 	         ex:腾讯充值中心-QQ会员充值
    # total_fee         总金额 	         ex:80
    # spbill_create_ip  Ip               APP和网页支付提交用户端ip，Native支付填调用微信支付API的机器IP。
    # trade_type        交易类型         	 默认为：APP（app支付）/JSAPI（小程序支付）
    # detail            商品细节[可选]     默认为：null
    # attach            附加数据[可选]     默认为：null
    # device_info       终端设备号(门店号或收银设备ID)[可选]  默认为：WEB
    if any(data.get(key, None) is None for key in
           ("out_trade_no", "body", "total_fee", "spbill_create_ip", 'trade_type')):
        return JsonResponse({'return_code': 'FAIL', 'error': '缺少必要参数'})
    # 剔除加密数据,并整理相关信息，设置订单15分钟失效
    arr = {
        "device_info": data.get('device_info', 'WEB'),
        "body": data['body'],
        "detail": data.get('detail', 'null'),
        "attach": data.get('attach', 'null'),
        "out_trade_no": data['out_trade_no'],
        "fee_type": "CNY",
        "total_fee": str(int(float(data['total_fee']) * 100)),
        "spbill_create_ip": data['spbill_create_ip'],
        "time_start": str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))),
        "time_expire": str(time.strftime('%Y%m%d%H%M%S', time.localtime(time.time() + 15 * 60))),
        "trade_type": data['trade_type'],
    }
    # 初始化支付对象，APP支付
    if data['trade_type'] == "APP":
        wx = WeixinPay(app_id=req.app.app_id,
                       mch_id=req.app.app_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.app_url)
    # 小程序支付
    elif data['trade_type'] == "JSAPI":
        wx = WeixinPay(app_id=req.app.sp_appid,
                       mch_id=req.app.sp_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.sp_url)
        # 小程序支付需要openid
        arr['openid'] = data['openid']

    try:
        rsp_json = wx.unified_order(data=arr)
    except Exception as e:
        models.Order.objects.create(
            app=req.app,
            order_no=arr['out_trade_no'],
            total_fee=arr['total_fee'],
            operation='统一下单失败'
        )
        log.info('{},{},{},{}'.format(req.app.name, '统一下单', data['out_trade_no'], str(e)))
        return JsonResponse({'return_code': 'FAIL', 'error': str(e)})

    # 整理信息返回让服务器反给前端直接调起App支付
    if arr['trade_type'] == 'APP':
        info = {}
        info['appid'] = rsp_json['appid']
        info['partnerid'] = rsp_json['mch_id']
        info['prepayid'] = rsp_json['prepay_id']
        info['package'] = 'Sign=WXPay'
        info['noncestr'] = wx_tool.nonce_str()
        info['timestamp'] = str(time.time()).split('.')[0]
        # 生成签名
        sign = wx.sign(raw=info)
        # 计算出sign并加进去
        info['sign'] = sign
        models.Order.objects.create(
            app=req.app,
            order_no=arr['out_trade_no'],
            total_fee=arr['total_fee'],
            operation='统一下单成功'
        )
        log.info('{},{},{},{}'.format(req.app.name, '统一下单', data['out_trade_no'], rsp_json))
        return JsonResponse(info)
    else:
        return JsonResponse(rsp_json)


@login_request
@check_method(['POST'])
def order_query(req):
    """该接口提供所有微信支付订单的查询，
    商户可以通过该接口主动查询订单状态，完成下一步的业务逻辑。"""
    data = json.loads(req.body)
    if any(data.get(key, None) is None for key in
           ("out_trade_no", "trade_type")):
        return JsonResponse({'return_code': 'FAIL', 'error': '缺少必要参数'})
    # 剔除加密数据
    arr = {'out_trade_no': data['out_trade_no']}
    if data['trade_type'] == "APP":
        wx = WeixinPay(app_id=req.app.app_id,
                       mch_id=req.app.app_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.app_url)
    # 小程序支付
    elif data['trade_type'] == "JSAPI":
        wx = WeixinPay(app_id=req.app.sp_appid,
                       mch_id=req.app.sp_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.sp_url)
    try:
        rsp_json = wx.order_query(data=arr)
    except Exception as e:
        models.Order.objects.create(
            app=req.app,
            order_no=data['out_trade_no'],
            operation='查询订单失败'
        )
        log.info('{},{},{},{}'.format(req.app.name, '查询订单失败', data['out_trade_no'], str(e)))
        return JsonResponse({'return_code': 'FAIL', 'error': str(e)})
    models.Order.objects.create(
        app=req.app,
        order_no=data['out_trade_no'],
        operation='订单查询成功'
    )
    log.info('{},{},{},{}'.format(req.app.name, '订单查询成功', data['out_trade_no'], rsp_json))
    return JsonResponse(rsp_json)


@login_request
@check_method(['POST'])
def close_order(req):
    """以下情况需要调用关单接口：
    商户订单支付失败需要生成新单号重新发起支付，要对原订单号调用关单，避免重复支付；
    系统下单后，用户支付超时，系统退出不再受理，避免用户继续，请调用关单接口。"""
    data = json.loads(req.body)
    if any(data.get(key, None) is None for key in
           ("out_trade_no", "trade_type")):
        return JsonResponse({'return_code': 'FAIL', 'error': '缺少必要参数'})
    arr = {
        "out_trade_no": data['out_trade_no'],
    }
    if data['trade_type'] == "APP":
        wx = WeixinPay(app_id=req.app.app_id,
                       mch_id=req.app.app_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.app_url)
    # 小程序支付
    elif data['trade_type'] == "JSAPI":
        wx = WeixinPay(app_id=req.app.sp_appid,
                       mch_id=req.app.sp_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.sp_url)
    try:
        rsp_json = wx.close_order(data=arr)
    except Exception as e:
        models.Order.objects.create(
            app=req.app,
            order_no=data['out_trade_no'],
            operation='订单关闭失败'
        )
        log.info('{},{},{},{}'.format(req.app.name, '订单关闭失败', data['out_trade_no'], str(e)))
        return JsonResponse({'return_code': 'FAIL', 'error': str(e)})
    models.Order.objects.create(
        app=req.app,
        order_no=data['out_trade_no'],
        operation='订单关闭成功'
    )
    log.info('{},{},{},{}'.format(req.app.name, '订单关闭成功', data['out_trade_no'], rsp_json))
    return JsonResponse(rsp_json)


@login_request
@check_method(['POST'])
def refund(req):
    """退款"""
    data = json.loads(req.body)
    if any(data.get(key, None) is None for key in
           ("out_trade_no", "out_refund_no", "total_fee", "refund_fee", "trade_type")):
        return JsonResponse({'return_code': 'FAIL', 'error': '缺少必要参数'})
    arr = {
        "out_trade_no": data['out_trade_no'],
        "out_refund_no": data['out_refund_no'],
        "total_fee": str(int(float(data['total_fee']) * 100)),
        "refund_fee": str(int(float(data['refund_fee']) * 100)),
    }
    if data['trade_type'] == 'APP':
        wx = WeixinPay(app_id=req.app.app_id,
                       mch_id=req.app.app_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.app_url,
                       # 取项目路径 + 数据库存的相对路径
                       key=settings.BASE_DIR + req.app.app_key,
                       cert=settings.BASE_DIR + req.app.app_cert)
    elif data['trade_type'] == 'JSAPI':
        wx = WeixinPay(app_id=req.app.sp_appid,
                       mch_id=req.app.sp_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.sp_url,
                       # 取项目路径 + 数据库存的相对路径
                       key=settings.BASE_DIR + req.app.sp_key,
                       cert=settings.BASE_DIR + req.app.sp_cert)
        arr = {'op_user_id': req.app.sp_mchid}  # 小程序退款需要op_user_id 默认为商户id
    try:
        rsp_json = wx.refund(data=arr)
    except Exception as e:
        models.Order.objects.create(
            app=req.app,
            order_no=data['out_trade_no'],
            operation='订单退款失败'
        )
        log.info('{},{},{},{}'.format(req.app.name, '订单退款失败', data['out_trade_no'], str(e)))
        return JsonResponse({'return_code': 'FAIL', 'error': str(e)})
    models.Order.objects.create(
        app=req.app,
        order_no=data['out_trade_no'],
        operation='订单退款成功'
    )
    log.info('{},{},{},{}'.format(req.app.name, '订单退款成功', data['out_trade_no'], rsp_json))
    return JsonResponse(rsp_json)


@login_request
@check_method(['POST'])
def refund_query(req):
    data = json.loads(req.body)
    if any(data.get(key, None) is None for key in
           ("out_trade_no", "trade_type")):
        return JsonResponse({'return_code': 'FAIL', 'error': '缺少必要参数'})
    arr = {
        "out_trade_no": data['out_trade_no'],
    }
    # App支付
    if data['trade_type'] == "APP":
        wx = WeixinPay(app_id=req.app.app_id,
                       mch_id=req.app.app_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.app_url)
    # 小程序支付
    elif data['trade_type'] == "JSAPI":
        wx = WeixinPay(app_id=req.app.sp_appid,
                       mch_id=req.app.sp_mchid,
                       mch_key=req.app.api_key,
                       notify_url=req.app.sp_url)
    try:
        rsp_json = wx.refund_query(data=arr)
    except Exception as e:
        models.Order.objects.create(
            app=req.app,
            order_no=data['out_trade_no'],
            operation='退款查询失败'
        )
        log.info('{},{},{},{}'.format(req.app.name, '退款查询失败', data['out_trade_no'], str(e)))
        return JsonResponse({'return_code': 'FAIL', 'error': str(e)})
    models.Order.objects.create(
        app=req.app,
        order_no=data['out_trade_no'],
        operation='退款查询成功'
    )
    log.info('{},{},{},{}'.format(req.app.name, '退款查询成功', data['out_trade_no'], rsp_json))
    return JsonResponse(rsp_json)
