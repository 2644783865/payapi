from django.db import models


class App(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True, verbose_name='App名称')
    identity = models.CharField(max_length=64, blank=True, null=True, verbose_name='身份信息')
    app_secret = models.CharField(max_length=32, blank=True, null=True, verbose_name='AppSecret')
    # 最各种支付好全部设置为一样的
    api_key = models.CharField(max_length=32, blank=True, null=True, verbose_name='api_key')
    # APP支付
    app_id = models.CharField(max_length=32, blank=True, null=True, verbose_name='AppID')
    app_mchid = models.CharField(max_length=32, blank=True, null=True, verbose_name='商户号')
    app_url = models.CharField(max_length=32, blank=True, null=True, verbose_name='App回调链接')
    app_key = models.CharField(max_length=32, blank=True, null=True, verbose_name='App证书key相对路径')
    app_cert = models.CharField(max_length=32, blank=True, null=True, verbose_name='App证书cert相对路径')
    # 小程序
    sp_appid = models.CharField(max_length=32, blank=True, null=True, verbose_name='小程序ID')
    sp_mchid = models.CharField(max_length=32, blank=True, null=True, verbose_name='小程序mchid')
    sp_url = models.CharField(max_length=32, blank=True, null=True, verbose_name='小程序回调链接')
    sp_key = models.CharField(max_length=32, blank=True, null=True, verbose_name='小程序证书key相对路径')
    sp_cert = models.CharField(max_length=32, blank=True, null=True, verbose_name='小程序证书cert相对路径')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "App信息"
        verbose_name_plural = verbose_name


# 订单操作信息备份
class Order(models.Model):
    app = models.ForeignKey(App)
    order_no = models.CharField(max_length=32, blank=False)
    total_fee = models.CharField(max_length=32, blank=True)
    operation = models.CharField(max_length=32, blank=False)
    update_time = models.DateTimeField(auto_now=True)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.order_no

    class Meta:
        verbose_name = "订单操作信息"
        verbose_name_plural = verbose_name
