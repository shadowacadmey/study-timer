# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  tests.py — تست‌های خودکار منطق برنامه (بدون نیاز به نمایشگر)
═══════════════════════════════════════════════════════════════════════
  اجرا:  python tests.py
═══════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

import config
import themes
from history import History

PASSED = 0
FAILED = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✓ {name}")
    else:
        FAILED += 1
        print(f"  ✗ {name}  ← {detail}")


# ─────────────────────────────── ۱) تبدیل تاریخ شمسی ───────────────────────────────

def test_jalali() -> None:
    print("\n[۱] تبدیل تاریخ میلادی → شمسی")
    check("۱ فروردین ۱۴۰۳ = 2024-03-20",
          config.gregorian_to_jalali(2024, 3, 20) == (1403, 1, 1),
          config.gregorian_to_jalali(2024, 3, 20))
    check("۱ فروردین ۱۴۰۰ = 2021-03-21",
          config.gregorian_to_jalali(2021, 3, 21) == (1400, 1, 1),
          config.gregorian_to_jalali(2021, 3, 21))
    check("۲۲ بهمن ۱۳۵۷ = 1979-02-11",
          config.gregorian_to_jalali(1979, 2, 11) == (1357, 11, 22),
          config.gregorian_to_jalali(1979, 2, 11))
    jy, jm, jd = config.gregorian_to_jalali(2026, 8, 19)
    check("2026-08-19 در ماه مرداد است", jm == 5, (jy, jm, jd))


# ─────────────────────────────── ۲) چرخش روزهای هفته ───────────────────────────────

def test_weekday_mapping() -> None:
    print("\n[۲] چرخش هوشمند روزهای هفته")
    cases = {
        date(2026, 8, 22): (0, "course", 1),   # شنبه → دورهٔ ۱
        date(2026, 8, 23): (1, "course", 2),   # یکشنبه → دورهٔ ۲
        date(2026, 8, 24): (2, "course", 3),   # دوشنبه → دورهٔ ۳
        date(2026, 8, 25): (3, "course", 4),   # سه‌شنبه → دورهٔ ۴
        date(2026, 8, 26): (4, "review", None),    # چهارشنبه → مرور
        date(2026, 8, 27): (5, "project", None),   # پنجشنبه → پروژه
        date(2026, 8, 28): (6, "rest", None),      # جمعه → استراحت
    }
    for d, (idx, typ, course) in cases.items():
        got_idx = config.persian_day_index(d)
        sched = config.get_schedule()[got_idx]
        check(f"{d} → شاخص {idx} ({typ})",
              got_idx == idx and sched["type"] == typ and sched.get("course") == course,
              f"got idx={got_idx}, type={sched['type']}, course={sched.get('course')}")


# ─────────────────────────────── ۳) مدت‌زمان جلسات ───────────────────────────────

def test_durations() -> None:
    print("\n[۳] مدت‌زمان دقیق بخش‌ها")
    schedule = config.get_schedule()
    std_secs = sum(s for _, s in schedule[0]["blocks"])
    check("جلسهٔ استاندارد = ۳ بخش × ۴۰ دقیقه = ۷۲۰۰ ثانیه", std_secs == 7200, std_secs)
    check("دورهٔ ۱ سه بخش دارد", len(schedule[0]["blocks"]) == 3)
    check("مرور هفتگی سه بخش دارد", len(schedule[4]["blocks"]) == 3)
    check("پروژهٔ عملی سه بخش دارد", len(schedule[5]["blocks"]) == 3)
    check("جمعه هیچ بخشی ندارد", len(schedule[6]["blocks"]) == 0)


# ─────────────────────────────── ۴) پالت‌های رنگی ───────────────────────────────

def test_themes() -> None:
    print("\n[۴] پالت‌های رنگی دوره‌ها")
    required = ("bg", "panel", "card", "card_border", "accent", "accent_hover",
                "accent_soft", "progress_bg", "success", "text", "subtext",
                "chip_text", "glow", "grad_top", "grad_bottom", "stars", "name_fa")
    hex_re = re.compile(r"^#[0-9a-fA-F]{6}$")
    for key in ("course1", "course2", "course3", "course4", "review", "project", "rest"):
        th = themes.THEMES.get(key)
        check(f"تم {key} موجود است", th is not None)
        if not th:
            continue
        missing = [f for f in required if f not in th]
        check(f"تم {key} همهٔ کلیدها را دارد", not missing, str(missing))
        bad = [f for f in required if f in th and isinstance(th[f], str)
               and f != "name_fa" and not hex_re.match(th[f])]
        check(f"تم {key} رنگ‌ها معتبرند", not bad, str(bad))
    check("چهار دورهٔ اصلی تم مجزا دارند",
          len({themes.THEMES[k]["accent"] for k in ("course1", "course2", "course3", "course4")}) == 4)


# ─────────────────────────────── ۵) تاریخچهٔ JSON ───────────────────────────────

def test_history() -> None:
    print("\n[۵] ذخیرهٔ خودکار تاریخچه در JSON")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "history.json"
        h = History(path)
        h.add_block("2026-08-22", 0, "شنبه", "دورهٔ ۱ — مبانی برنامه‌نویسی پایتون",
                    "تماشای ویدیو آموزشی 🎥", 2400)
        h.add_block("2026-08-22", 0, "شنبه", "دورهٔ ۱ — مبانی برنامه‌نویسی پایتون",
                    "تمرین عملی و کدنویسی 💻", 2400)
        h.add_block("2026-08-23", 1, "یکشنبه", "دورهٔ ۲ — پایتون پیشرفته و شیءگرایی",
                    "تماشای ویدیو آموزشی 🎥", 2400)
        h.save()

        # خواندن مجدد از روی دیسک
        h2 = History(path)
        check("سه بخش ثبت شده", h2.data["days"]["2026-08-22"]["blocks_completed"] == 2
              and h2.data["days"]["2026-08-23"]["blocks_completed"] == 1)
        check("مجموع ثانیه‌ها درست است", h2.total_seconds() == 7200, h2.total_seconds())
        check("مطالعهٔ امروز (شنبه) درست است",
              h2.today_study_seconds("2026-08-22") == 4800)
        check("مطالعهٔ هفته (شنبه‌محور) درست است",
              h2.week_study_seconds(date(2026, 8, 23)) == 7200)
        # فایل واقعاً JSON است
        raw = json.loads(path.read_text(encoding="utf-8"))
        check("فایل JSON معتبر است", raw["total_seconds"] == 7200)


# ─────────────────────────────── ۶) ابزارهای صوتی و متنی ───────────────────────────────

def test_voice_and_text() -> None:
    print("\n[۶] عبارات صوتی و ابزارهای متن")
    check("تشخیص متن فارسی", config.has_persian("سلام") is True
          and config.has_persian("hello") is False)
    check("حذف ایموجی", config.strip_emoji("وقت ویدیو تمام شد 🎥!") == "وقت ویدیو تمام شد !")
    msg_fa = config.voice_message("block_end", "fa",
                                  done="تماشای ویدیو آموزشی 🎥",
                                  nxt="تمرین عملی و کدنویسی 💻")
    check("پیام فارسیِ پایان بخش ساخته می‌شود",
          "برید سراغ" in msg_fa and "تمرین" in msg_fa, msg_fa)
    msg_en = config.voice_message("block_end", "en",
                                  done=config.en_label("تماشای ویدیو آموزشی 🎥"),
                                  nxt=config.en_label("تمرین عملی و کدنویسی 💻"))
    check("پیام انگلیسیِ پایان بخش ساخته می‌شود",
          "educational video" in msg_en and "practice" in msg_en, msg_en)
    check("معادل انگلیسی برچسب‌ها", config.en_label("تماشای ویدیو آموزشی 🎥")
          == "educational video")


# ─────────────────────────────── اجرا ───────────────────────────────

if __name__ == "__main__":
    print("═" * 60)
    print("  تست‌های Study Timer Pro")
    print("═" * 60)
    test_jalali()
    test_weekday_mapping()
    test_durations()
    test_themes()
    test_history()
    test_voice_and_text()
    print("\n" + "═" * 60)
    print(f"  نتیجه: {PASSED} موفق / {FAILED} ناموفق")
    print("═" * 60)
    raise SystemExit(1 if FAILED else 0)
