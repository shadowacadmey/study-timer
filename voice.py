# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  voice.py — سیستم اعلان صوتی ساده (فقط زنگ ویندوز)
═══════════════════════════════════════════════════════════════════════
  فقط از زنگ پیش‌فرض ویندوز استفاده می‌کند
"""

from __future__ import annotations

import logging
import os
import threading

import config

logger = logging.getLogger("study-timer")


class VoiceNotifier:
    def __init__(self, mode: str = "beep", volume: float = 1.0, custom_sound_file: str = ""):
        self.mode = "beep"  # فقط زنگ ویندوز
        self.volume = max(0.0, min(1.0, float(volume)))
        self.custom_sound_file = custom_sound_file
        self._speaking_lock = threading.Lock()

    # ═══════════════════════════════ API عمومی ═══════════════════════════════

    def set_mode(self, mode: str) -> None:
        """فقط حالت beep پشتیبانی می‌شود"""
        self.mode = "beep"

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
    
    def set_custom_sound_file(self, file_path: str) -> None:
        """این تابع فعلاً کار نمی‌کند"""
        pass

    def notify(self, key: str, **params) -> None:
        """
        پخشِ ناهمگامِ زنگ ویندوز برای یک رویداد.
        key: session_start | block_end | session_complete | session_rest
        """
        thread = threading.Thread(target=self._beep, daemon=True)
        thread.start()

    # ─────────────────────────── زنگ ساده ───────────────────────────

    @staticmethod
    def _beep() -> None:
        try:
            if os.name == "nt":
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception as exc:
            logger.warning("پخش زنگ ناموفق بود: %s", exc)
