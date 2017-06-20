# 标准库应用
import json
# 三方库引用
from django.http import JsonResponse, QueryDict

# 内部引用
from wx import models
from . import wx_tool


def login_request(func):
    """验证identity和token，并把对应app装入req.app"""

    def wrapper(req, *args, **kwargs):
        # 验证请求头中的identity
        identity = req.META.get('HTTP_IDENTITY', None)
        # 判定identity
        if identity:
            try:
                app = models.App.objects.get(identity=identity)
            except models.App.DoesNotExist:
                return JsonResponse({'return_code': 'FAIL', 'error': '身份认证已过期'})
            else:
                data = json.loads(req.body)
                # 判定token
                if wx_tool.check_token(data):
                    # app装在req里面
                    req.app = app
                else:
                    return JsonResponse({'return_code': 'FAIL', 'error': 'token错误'})
        else:
            return JsonResponse({'return_code': 'FAIL', 'error': '无身份认证'})
        return func(req, *args, **kwargs)

    return wrapper


def check_method(method_list):
    """请求方法检测装饰器"""

    def _decorator(inner):
        def wrapper(req, *args, **kwargs):
            if req.method in method_list:
                # 这里直接return，否则包装之后的函数没有返回httpResponse
                return inner(req)
            else:
                return JsonResponse(
                    {'statu': '400', 'error': '请求方式错误'}
                )

        return wrapper

    return _decorator
