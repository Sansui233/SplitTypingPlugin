import asyncio
import os
from collections import defaultdict

import yaml

from pkg.platform.types import Plain  # 导入消息类型
from pkg.platform.types.message import MessageChain
from pkg.plugin.context import (
    APIHost,
    BasePlugin,
    EventContext,
    handler,
    register,
)
from pkg.plugin.events import (  # 导入事件类
    GroupNormalMessageReceived,
    NormalMessageResponded,
    PersonNormalMessageReceived,
)
from plugins.SplitTypingPlugin.split import SplitText


# 注册插件
@register(
    name="SplitTypingPlugin",  # 英文名
    description="模拟人类打字习惯的消息分段发送插件",  # 中文描述
    version="0.1.1",
    author="小馄饨,",
)
class MyPlugin(BasePlugin):
    # 插件加载时触发
    def __init__(self, host: APIHost):
        self.split_enabled = {}  # 用字典存储每个用户的分段状态
        self.typing_locks = defaultdict(asyncio.Lock)  # 每个对话的打字锁
        self.split_engine = SplitText()

        # 加载配置文件

        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                settings = config.get("typing_settings", {})
                self.char_delay = settings.get("char_delay", 0.1)  # 每个字符的延迟
                self.segment_delay_max = settings.get(
                    "segment_delay_max", 10
                )  # 段落最大延迟
                self.segment_pause = settings.get("segment_pause", 0.5)  # 段落间停顿
                self.max_split_length = settings.get(
                    "max_split_length", 50
                )  # 最大分段长度
                self.split_mode: str = settings.get("split_mode", "default")
        except Exception as e:
            # 使用默认值
            self.char_delay = 0.1
            self.segment_pause = 0.5
            self.max_split_length = 50
            raise e

    # 异步初始化
    async def initialize(self):
        self.ap.logger.info("🧩 [SplitTyping] 插件初始化")
        pass

    def split_text(self, text: str) -> list:
        if self.split_mode == "simple":
            return self.split_engine.simple_split(text)
        # default
        return self.split_engine.split(text)

    # 当收到个人消息时触发
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        sender_id = ctx.event.sender_id  # type: ignore
        msg = ctx.event.text_message  # type: ignore

        # 设置默认值
        if sender_id not in self.split_enabled:
            self.split_enabled[sender_id] = True

        # 处理开关命令
        if msg == "开启分段":
            self.split_enabled[sender_id] = True
            self.ap.logger.info(f"[分段发送] 用户 {sender_id} 开启了分段发送功能\n")
            await ctx.send_message(
                "person", sender_id, MessageChain([Plain("已开启分段发送模式")])
            )
            ctx.prevent_default()
            return
        elif msg == "关闭分段":
            self.split_enabled[sender_id] = False
            self.ap.logger.info(f"[分段发送] 用户 {sender_id} 关闭了分段发送功能\n")
            await ctx.send_message(
                "person", sender_id, MessageChain([Plain("已关闭分段发送模式")])
            )
            ctx.prevent_default()
            return

    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        group_id = ctx.event.launcher_id  # type: ignore
        msg = ctx.event.text_message  # type: ignore

        # 设置默认值
        if group_id not in self.split_enabled:
            self.split_enabled[group_id] = True

        # 处理开关命令
        if msg == "开启分段":
            self.split_enabled[group_id] = True
            self.ap.logger.info(f"[分段发送] 群 {group_id} 开启了分段发送功能\n")
            await ctx.send_message(
                "group", group_id, MessageChain([Plain("已开启分段发送模式")])
            )
            ctx.prevent_default()
            return
        elif msg == "关闭分段":
            self.split_enabled[group_id] = False
            self.ap.logger.info(f"[分段发送] 群 {group_id} 关闭了分段发送功能\n")
            await ctx.send_message(
                "group", group_id, MessageChain([Plain("已关闭分段发送模式")])
            )
            ctx.prevent_default()
            return

    async def get_chat_lock(self, chat_type: str, chat_id: str) -> asyncio.Lock:
        """获取对话的锁"""
        lock_key = f"{chat_type}_{chat_id}"
        return self.typing_locks[lock_key]

    async def simulate_typing(
        self, ctx: EventContext, chat_type: str, chat_id: str, text: str
    ):
        """模拟打字效果的延时"""
        # 获取此对话的锁
        lock = await self.get_chat_lock(chat_type, chat_id)

        # 等待获取锁
        async with lock:
            # 根据文本长度计算延时
            typing_delay = len(text) * self.char_delay
            # 发送完整消息
            await ctx.send_message(chat_type, chat_id, MessageChain([Plain(text)]))
            # 等待打字延时
            await asyncio.sleep(typing_delay)

    # 处理大模型的回复
    @handler(NormalMessageResponded)
    async def normal_message_responded(self, ctx: EventContext):
        chat_type = ctx.event.launcher_type  # type: ignore
        chat_id = ctx.event.launcher_id if chat_type == "group" else ctx.event.sender_id  # type: ignore

        # 检查是否启用分段
        if not self.split_enabled.get(chat_id, False):
            self.ap.logger.info("[%%] 不分段\n")
            return

        # 获取大模型的回复文本
        response_text = ctx.event.response_text  # type: ignore
        self.ap.logger.info(f"[%%] content: {response_text}\n")

        # 获取此对话的锁
        lock = await self.get_chat_lock(chat_type, chat_id)

        # 等待获取锁
        async with lock:
            # 如果文本长度超过最大分段长度，直接发送不分段
            # simple 模式忽略此规则
            if len(response_text) > self.max_split_length:
                self.ap.logger.info(
                    f"[分段发送] 文本长度({len(response_text)})超过最大限制({self.max_split_length})，将不进行分段\n"
                )
                return

            # 分割文本
            parts = self.split_text(response_text)

            if parts:
                self.ap.logger.info(
                    f"[分段发送] {chat_type} {chat_id} 的消息将被分为 {len(parts)} 段发送\n"
                )

                # 阻止默认的回复行为
                ctx.prevent_default()

                # 逐段发送消息
                for i, part in enumerate(parts, 1):
                    self.ap.logger.info(
                        f"[分段发送] 正在发送第 {i}/{len(parts)} 段: {part}\n"
                    )
                    # 模拟打字延时并发送
                    typing_delay = len(part) * self.char_delay
                    typing_delay = (
                        self.segment_delay_max
                        if typing_delay > self.segment_delay_max
                        else typing_delay
                    )
                    await ctx.send_message(
                        chat_type, chat_id, MessageChain([Plain(part)])
                    )
                    await asyncio.sleep(typing_delay)

                    # 如果不是最后一段，添加段落间停顿
                    if i < len(parts):
                        await asyncio.sleep(self.segment_pause)

    # 插件卸载时触发
    def __del__(self):
        pass
