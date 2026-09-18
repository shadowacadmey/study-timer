# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  history.py — ذخیرهٔ خودکار تاریخچهٔ مطالعه در فایل JSON
═══════════════════════════════════════════════════════════════════════
  ساختار فایل history.json:

  {
    "days": {
      "2026-08-19": {
        "date": "2026-08-19",
        "day_index": 3,
        "day_name": "سه‌شنبه",
        "title": "دورهٔ ۴ — هوش مصنوعی و پروژهٔ نهایی",
        "blocks_completed": 3,
        "block_labels": ["تماشای ویدیو آموزشی 🎥", "..."],
        "study_seconds": 7200,
        "events": [ {"ts": "...", "type": "block_completed", "label": "...", "seconds": 2400} ]
      }
    },
    "total_seconds": 14400
  }
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import config

logger = logging.getLogger("study-timer")


class History:
    """مدیریت خواندن/نوشتن تاریخچهٔ مطالعه."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict = {"days": {}, "total_seconds": 0}
        self.load()

    # ─────────────────────────────── خواندن ───────────────────────────────
    def load(self) -> "History":
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data = loaded
                    self.data.setdefault("days", {})
                    self.data.setdefault("total_seconds", 0)
        except Exception as exc:  # فایل خراب → شروع مجدد با تاریخچهٔ خالی
            logger.warning("خطا در خواندن تاریخچه (%s): %s", self.path, exc)
            self.data = {"days": {}, "total_seconds": 0}
        self.data["total_seconds"] = self.total_seconds()
        return self

    # ─────────────────────────────── ثبت رویداد ───────────────────────────────
    def _ensure_day(self, date_str: str, day_index: int, day_name: str, title: str) -> dict:
        days = self.data.setdefault("days", {})
        if date_str not in days:
            days[date_str] = {
                "date": date_str,
                "day_index": day_index,
                "day_name": day_name,
                "title": title,
                "blocks_completed": 0,
                "block_labels": [],
                "study_seconds": 0,
                "events": [],
            }
        return days[date_str]

    def add_block(self, date_str: str, day_index: int, day_name: str,
                  title: str, block_label: str, seconds: int) -> None:
        """ثبت اتمام یک بخش مطالعاتی (به صورت خودکار ذخیرهٔ جداگانه نیاز نیست)."""
        day = self._ensure_day(date_str, day_index, day_name, title)
        day["blocks_completed"] += 1
        if block_label not in day["block_labels"]:
            day["block_labels"].append(block_label)
        day["study_seconds"] += max(0, int(seconds))
        day["events"].append({
            "ts": datetime.now().isoformat(timespec="seconds"),
            "type": "block_completed",
            "label": block_label,
            "seconds": max(0, int(seconds)),
        })
        # محدود نگه‌داشتن حجم فایل (فقط ۲۰۰ رویداد آخر هر روز)
        if len(day["events"]) > 200:
            day["events"] = day["events"][-200:]
        self.data["total_seconds"] = self.total_seconds()

    # ─────────────────────────────── ذخیره ───────────────────────────────
    def save(self) -> None:
        """ذخیرهٔ اتمی (نوشتن در فایل موقت + جایگزینی) تا فایل خراب نشود."""
        try:
            self.data["total_seconds"] = self.total_seconds()
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except Exception as exc:
            logger.warning("خطا در ذخیرهٔ تاریخچه: %s", exc)

    # ─────────────────────────────── آمار ───────────────────────────────
    def total_seconds(self) -> int:
        return sum(
            d.get("study_seconds", 0)
            for d in self.data.get("days", {}).values()
        )

    def today_study_seconds(self, date_str: str) -> int:
        day = self.data.get("days", {}).get(date_str)
        return day.get("study_seconds", 0) if day else 0

    def week_study_seconds(self, today: date) -> int:
        """مجموع مطالعه از شنبهٔ همین هفته تا امروز."""
        day_index = config.persian_day_index(today)
        week_start = today - timedelta(days=day_index)
        week_end = week_start + timedelta(days=7)
        total = 0
        for ds, day in self.data.get("days", {}).items():
            try:
                d = date.fromisoformat(ds)
            except ValueError:
                continue
            if week_start <= d < week_end:
                total += day.get("study_seconds", 0)
        return total
