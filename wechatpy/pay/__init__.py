# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import copy

import requests
import xmltodict
from optionaldict import optionaldict

from wechatpy.utils import random_string
from wechatpy.exceptions import WeChatPayException
from wechatpy.pay.utils import calculate_signature
from wechatpy.pay.utils import dict_to_xml
from wechatpy.pay.base import BaseWeChatPayAPI
from wechatpy.pay import api


class WeChatPay(object):
    redpack = api.WeChatRedpack()
    """红包接口"""
    transfer = api.WeChatTransfer()
    """企业付款接口"""
    coupon = api.WeChatCoupon()
    """代金券接口"""
    order = api.WeChatOrder()
    """订单接口"""
    refund = api.WeChatRefund()
    """退款接口"""
    tools = api.WeChatTools()

    API_BASE_URL = 'https://api.mch.weixin.qq.com/'

    def __new__(cls, *args, **kwargs):
        self = super(WeChatPay, cls).__new__(cls)
        for name, _api in self.__class__.__dict__.items():
            if isinstance(_api, BaseWeChatPayAPI):
                _api = copy.deepcopy(_api)
                _api._client = self
                setattr(self, name, _api)
        return self

    def __init__(self, appid, api_key, mch_id, sub_mch_id=None,
                 mch_cert=None, mch_key=None):
        """
        :param appid: 微信公众号 appid
        :param api_key: 商户 key
        :param mch_id: 商户号
        :param sub_mch_id: 可选，子商户号，受理模式下必填
        :param mch_cert: 商户证书路径
        :param mch_key: 商户证书私钥路径
        """
        self.appid = appid
        self.api_key = api_key
        self.mch_id = mch_id
        self.sub_mch_id = sub_mch_id
        self.mch_cert = mch_cert
        self.mch_key = mch_key

    def _request(self, method, url_or_endpoint, **kwargs):
        if not url_or_endpoint.startswith(('http://', 'https://')):
            api_base_url = kwargs.pop('api_base_url', self.API_BASE_URL)
            url = '{base}{endpoint}'.format(
                base=api_base_url,
                endpoint=url_or_endpoint
            )
        else:
            url = url_or_endpoint

        if isinstance(kwargs.get('data', ''), dict):
            data = optionaldict(kwargs['data'])
            if 'mchid' not in data:
                # Fuck Tencent
                data.setdefault('mch_id', self.mch_id)
            data.setdefault('sub_mch_id', self.sub_mch_id)
            data.setdefault('nonce_str', random_string(32))
            sign = calculate_signature(data, self.api_key)
            body = dict_to_xml(data, sign)
            body = body.encode('utf-8')
            kwargs['data'] = body

        # 商户证书
        if self.mch_cert and self.mch_key:
            kwargs['cert'] = (self.mch_cert, self.mch_key)

        res = requests.request(
            method=method,
            url=url,
            **kwargs
        )
        res.raise_for_status()
        return self._handle_result(res)

    def _handle_result(self, res):
        xml = res.text
        try:
            data = xmltodict.parse(xml)['xml']
        except xmltodict.ParsingInterrupted:
            # 解析 XML 失败
            return xml

        return_code = data['return_code']
        return_msg = data.get('return_msg')
        result_code = data.get('result_code')
        errcode = data.get('err_code')
        errmsg = data.get('err_code_des')
        if return_code != 'SUCCESS' or result_code != 'SUCCESS':
            # 返回状态码不为成功
            raise WeChatPayException(
                return_code,
                result_code,
                return_msg,
                errcode,
                errmsg
            )
        return data

    def get(self, url, **kwargs):
        return self._request(
            method='get',
            url_or_endpoint=url,
            **kwargs
        )

    def post(self, url, **kwargs):
        return self._request(
            method='post',
            url_or_endpoint=url,
            **kwargs
        )
