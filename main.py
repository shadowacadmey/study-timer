# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  main.py — نقطهٔ ورود برنامهٔ Study Timer Pro
═══════════════════════════════════════════════════════════════════════
  اجرا:
      python main.py
  یا بدون پنجرهٔ CMD در ویندوز:
      pythonw main.py

  گزینه‌های تست:
      python main.py --simulate-date 2026-08-22   (شبیه‌سازی روزِ شنبه)
      python main.py --win-pos 0,0                (موقعیت پنجره)
"""

from __future__ import annotations

import argparse
import logging
import sys

# ثبت وقایع کلی (برای عیب‌یابی)
from app import LOG_PATH

logging.basicConfig(
    level=logging.INFO,
    filename=str(LOG_PATH),
    encoding="utf-8",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Study Timer Pro — تایمر هوشمند مطالعه")
    parser.add_argument("--simulate-date", default=None,
                        help="شبیه‌سازی تاریخ امروز (مثلاً 2026-08-22 برای شنبه)")
    parser.add_argument("--win-pos", default=None,
                        help="موقعیت پنجره به شکل X,Y (مثلاً 0,0)")
    args = parser.parse_args()

    from app import StudyTimerApp

    app = StudyTimerApp(simulate_date=args.simulate_date, win_pos=args.win_pos)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # نمایش خطا در فایل log و خروج امن
        logging.getLogger("study-timer").exception("خطای بحرانی: %s", exc)
        sys.exit(1)
