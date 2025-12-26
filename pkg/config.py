from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SplitConfig:
    """Configuration for split typing behavior."""

    split_mode: str = "default"  # 'default' or 'simple'
    segment_delay_max: float = 10  # max delay per segment (seconds)
    segment_pause: float = 0.5  # pause between segments (seconds)
    char_delay: float = 0.1  # delay per character (seconds)
    max_segment_length: int = 50  # max length before skipping split


# Global config instance, initialized in main.py
config: SplitConfig | None = None


def get_config() -> SplitConfig:
    """Get the global config instance."""
    if config is None:
        raise RuntimeError("Config not initialized. Call init_config() first.")
    return config


def init_config(
    split_mode: str = "default",
    segment_delay_max: float = 10,
    segment_pause: float = 0.5,
    char_delay: float = 0.1,
    max_segment_length: int = 50,
) -> SplitConfig:
    """Initialize the global config instance."""
    global config
    config = SplitConfig(
        split_mode=split_mode,
        segment_delay_max=segment_delay_max,
        segment_pause=segment_pause,
        char_delay=char_delay,
        max_segment_length=max_segment_length,
    )
    return config
