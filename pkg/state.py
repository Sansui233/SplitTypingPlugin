from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class SplitState:
    """State management for split typing."""

    # 群聊id 或 私聊id 的开启分段设置
    split_enabled: dict[str, bool] = field(default_factory=dict)
    # 分段发送锁，为 type + chat_id 组合，防止 id 重名
    typing_locks: defaultdict[str, asyncio.Lock] = field(
        default_factory=lambda: defaultdict(asyncio.Lock)
    )

    def is_enabled(self, uid: str) -> bool:
        """Check if split is enabled for a chat."""
        return self.split_enabled.get(uid, False)

    def enable(self, uid: str) -> None:
        """Enable split for a chat."""
        if uid not in self.split_enabled:
            self.split_enabled[uid] = True

    def disable(self, chat_id: str) -> None:
        """Disable split for a chat."""
        self.split_enabled[chat_id] = False

    def get_lock(self, uid: str) -> asyncio.Lock:
        """Get the typing lock for a chat."""
        return self.typing_locks[uid]


def uid(chat_type: str, chat_id: str | int) -> str:
    return f"{chat_type}_{chat_id}"


# Global state instance, initialized in main.py
state: SplitState | None = None


def get_state() -> SplitState:
    """Get the global state instance."""
    if state is None:
        raise RuntimeError("State not initialized. Call init_state() first.")
    return state


def init_state() -> SplitState:
    """Initialize the global state instance."""
    global state
    state = SplitState()
    return state
