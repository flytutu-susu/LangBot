from __future__ import annotations

import logging

import openai
from openai.types import images_response

from ..openai import keymgr
from ..utils import context
from ..audit import gatherer
from ..openai import modelmgr
from ..openai.api import model as api_model
from ..core import app


class OpenAIInteract:
    """OpenAI 接口封装

    将文字接口和图片接口封装供调用方使用
    """

    key_mgr: keymgr.KeysManager = None

    audit_mgr: gatherer.DataGatherer = None

    default_image_api_params = {
        "size": "256x256",
    }

    client: openai.Client = None

    def __init__(self, ap: app.Application):

        cfg= ap.cfg_mgr.data
        api_key = cfg['openai_config']['api_key']

        self.key_mgr = keymgr.KeysManager(api_key)
        self.audit_mgr = gatherer.DataGatherer()

        # 配置OpenAI proxy
        openai.proxies = None  # 先重置，因为重载后可能需要清除proxy
        if "http_proxy" in cfg['openai_config'] and cfg['openai_config']["http_proxy"] is not None:
            openai.proxies = {
                "http": cfg['openai_config']["http_proxy"],
                "https": cfg['openai_config']["http_proxy"]
            }

        # 配置openai api_base
        if "reverse_proxy" in cfg['openai_config'] and cfg['openai_config']["reverse_proxy"] is not None:
            logging.debug("设置反向代理: "+cfg['openai_config']['reverse_proxy'])
            openai.base_url = cfg['openai_config']["reverse_proxy"]


        self.client = openai.Client(
            api_key=self.key_mgr.get_using_key(),
            base_url=openai.base_url
        )

        context.set_openai_manager(self)

    def request_completion(self, messages: list):
        """请求补全接口回复=
        """
        # 选择接口请求类
        config = context.get_config_manager().data

        request: api_model.RequestBase

        model: str = config['completion_api_params']['model']

        cp_parmas = config['completion_api_params'].copy()
        del cp_parmas['model']

        request = modelmgr.select_request_cls(self.client, model, messages, cp_parmas)

        # 请求接口
        for resp in request:

            if resp['usage']['total_tokens'] > 0:
                self.audit_mgr.report_text_model_usage(
                    model,
                    resp['usage']['total_tokens']
                )

            yield resp

    def request_image(self, prompt) -> images_response.ImagesResponse:
        """请求图片接口回复

        Parameters:
            prompt (str): 提示语

        Returns:
            dict: 响应
        """
        config = context.get_config_manager().data
        params = config['image_api_params']

        response = self.client.images.generate(
            prompt=prompt,
            n=1,
            **params
        )

        self.audit_mgr.report_image_model_usage(params['size'])

        return response

