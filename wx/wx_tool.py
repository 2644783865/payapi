# 标准库应用
import random, string
from hashlib import md5


def nonce_str():
    """产生随机字符串，不长于32位"""
    char = string.ascii_letters + string.digits
    return "".join(random.choice(char) for _ in range(32))


def get_md5(string):
    """get MD5"""
    return md5(string.encode()).hexdigest()


def _calculate(data):
    """token算法:
    1，传入参数字典排序
    2，整理成字符串 加上 '自定义字符串'
    3，md5加密，得到token"""
    sorted_key = sorted(data.keys())
    key_value = (key + data[key] for key in sorted_key)
    string = ''.join(key_value) + '自定义字符串'
    return md5(string.encode()).hexdigest()


def check_token(data):
    """
    检查签名：
    1，取出toke
    2，删除token，验证算法
    """
    token = data.pop('token')
    return token == _calculate(data)
