from django.conf.urls import url, include
from wx import views

urlpatterns = [
    # 测试路径
    url(r'^index/$', views.index),
    # 获取code,计算identity用
    url(r'^get_code/$', views.get_code),
    # 统一下单
    url(r'^unified_order/$', views.unified_order),
    # 订单查询
    url(r'^order_query/$', views.order_query),
    # 关闭订单
    url(r'^close_order/$', views.close_order),
    # 退款
    url(r'^refund/$', views.refund),
    # 退款查询
    url(r'^refund_query/$', views.refund_query),
]
