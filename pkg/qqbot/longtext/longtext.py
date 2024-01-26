from __future__ import annotations
import os
import traceback

from PIL import Image, ImageDraw, ImageFont
from mirai.models.message import MessageComponent, Plain

from ...core import app
from . import strategy
from .strategies import image, forward


class LongTextProcessor:
    
    ap: app.Application

    strategy_impl: strategy.LongTextStrategy

    def __init__(self, ap: app.Application):
        self.ap = ap

    async def initialize(self):
        config = self.ap.cfg_mgr.data
        if self.ap.cfg_mgr.data['blob_message_strategy'] == 'image':
            use_font = config['font_path']
            try:
                # 检查是否存在
                if not os.path.exists(use_font):
                    # 若是windows系统，使用微软雅黑
                    if os.name == "nt":
                        use_font = "C:/Windows/Fonts/msyh.ttc"
                        if not os.path.exists(use_font):
                            self.ap.logger.warn("未找到字体文件，且无法使用Windows自带字体，更换为转发消息组件以发送长消息，您可以在config.py中调整相关设置。")
                            config['blob_message_strategy'] = "forward"
                        else:
                            self.ap.logger.info("使用Windows自带字体：" + use_font)
                            self.ap.cfg_mgr.data['font_path'] = use_font
                    else:
                        self.ap.logger.warn("未找到字体文件，且无法使用系统自带字体，更换为转发消息组件以发送长消息，您可以在config.py中调整相关设置。")
                        self.ap.cfg_mgr.data['blob_message_strategy'] = "forward"
            except:
                traceback.print_exc()
                self.ap.logger.error("加载字体文件失败({})，更换为转发消息组件以发送长消息，您可以在config.py中调整相关设置。".format(use_font))
                self.ap.cfg_mgr.data['blob_message_strategy'] = "forward"
        
        if self.ap.cfg_mgr.data['blob_message_strategy'] == 'image':
            self.strategy_impl = image.Text2ImageStrategy(self.ap)
        elif self.ap.cfg_mgr.data['blob_message_strategy'] == 'forward':
            self.strategy_impl = forward.ForwardComponentStrategy(self.ap)
        await self.strategy_impl.initialize()

    async def check_and_process(self, message: str) -> list[MessageComponent]:
        if len(message) > self.ap.cfg_mgr.data['blob_message_threshold']:
            return await self.strategy_impl.process(message)
        else:
            return [Plain(message)]