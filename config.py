# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  config.py — پیکربندی مرکزی برنامهٔ Study Timer Pro
═══════════════════════════════════════════════════════════════════════
  تمام ثابت‌ها، برنامهٔ چرخش هفتگی، برچسب بخش‌ها، عبارات صوتی و
  تبدیل تاریخ میلادی→شمسی در همین فایل تعریف شده‌اند.
  اگر می‌خواهید مدت‌زمان بخش‌ها یا پیام‌ها را تغییر دهید، همین‌جا را ویرایش کنید.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, timedelta
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# ۱) مدت‌زمان بخش‌های استاندارد (به دقیقه)
#    هر جلسهٔ استاندارد = ۳ بخش × ۴۰ دقیقه = ۱۲۰ دقیقه = ۷۲۰۰ ثانیه
#    (توجه: ۱۲۰ دقیقه دقیقاً برابر ۷۲۰۰ ثانیه است، نه ۱۲۰۰۰ ثانیه.)
# ═══════════════════════════════════════════════════════════════════
DEFAULT_VIDEO_MIN = 40        # بخش اول: تماشای ویدیو آموزشی
DEFAULT_PRACTICE_MIN = 40     # بخش دوم: تمرین عملی و کدنویسی
DEFAULT_DEBUG_MIN = 40        # بخش سوم: رفع اشکال و جمع‌بندی

# متغیرهای قابل تغییر توسط کاربر
VIDEO_MIN = DEFAULT_VIDEO_MIN
PRACTICE_MIN = DEFAULT_PRACTICE_MIN
DEBUG_MIN = DEFAULT_DEBUG_MIN

# تنظیمات ظاهری و رفتاری
AUTO_NEXT_BLOCK = True  # شروع خودکار بخش بعدی
SHOW_STATS = True  # نمایش آمار
SHOW_MOTIVATION = True  # نمایش پیام‌های انگیزشی
FONT_SIZE = "medium"  # small, medium, large

# ─── حالت تست سریع (فقط برای توسعه): با STUDY_TIMER_FAST=1 اجرا کنید ───
FAST_BLOCK_SECONDS = 2


def set_custom_times(video_min: int, practice_min: int, debug_min: int) -> None:
    """تنظیم زمان‌های سفارشی برای بخش‌ها."""
    global VIDEO_MIN, PRACTICE_MIN, DEBUG_MIN
    VIDEO_MIN = max(1, min(180, video_min))  # بین ۱ تا ۱۸۰ دقیقه
    PRACTICE_MIN = max(1, min(180, practice_min))
    DEBUG_MIN = max(1, min(180, debug_min))


def reset_default_times() -> None:
    """بازنشانی زمان‌ها به مقادیر پیش‌فرض."""
    global VIDEO_MIN, PRACTICE_MIN, DEBUG_MIN
    VIDEO_MIN = DEFAULT_VIDEO_MIN
    PRACTICE_MIN = DEFAULT_PRACTICE_MIN
    DEBUG_MIN = DEFAULT_DEBUG_MIN


def set_auto_next_block(value: bool) -> None:
    """تنظیم شروع خودکار بخش بعدی."""
    global AUTO_NEXT_BLOCK
    AUTO_NEXT_BLOCK = value


def set_show_stats(value: bool) -> None:
    """تنظیم نمایش آمار."""
    global SHOW_STATS
    SHOW_STATS = value


def set_show_motivation(value: bool) -> None:
    """تنظیم نمایش پیام‌های انگیزشی."""
    global SHOW_MOTIVATION
    SHOW_MOTIVATION = value


def set_font_size(value: str) -> None:
    """تنظیم اندازه فونت."""
    global FONT_SIZE
    if value in ("small", "medium", "large"):
        FONT_SIZE = value


# ═══════════════════════════════════════════════════════════════════
# ۲) برچسب‌های گرافیکی بخش‌های استاندارد (فارسی + معادل انگلیسی برای TTS)
# ═══════════════════════════════════════════════════════════════════
BLOCK_LABELS_FA = [
    "تماشای ویدیو آموزشی 🎥",
    "تمرین عملی و کدنویسی 💻",
    "رفع اشکال و جمع‌بندی 📝",
]

BLOCK_LABELS_EN = {
    "تماشای ویدیو آموزشی 🎥": "educational video",
    "تمرین عملی و کدنویسی 💻": "hands-on practice",
    "رفع اشکال و جمع‌بندی 📝": "debugging and wrap-up",
    "مرور خلاصه‌ها و فلش‌کارت‌ها 🗂️": "reviewing notes and flashcards",
    "حل نمونه‌سؤال و آزمونک ❓": "practice questions",
    "بازبینی نقاط ضعف و تثبیت 🎯": "reviewing weak points",
    "پروژه عملی و پیاده‌سازی 🛠️": "hands-on project implementation",
    "رفع اشکال تجمعی و تست 🔧": "cumulative debugging and testing",
    "مستندسازی و جمع‌بندی 📄": "documentation and wrap-up",
}


def en_label(fa_label: str) -> str:
    """معادل انگلیسیِ یک برچسب فارسی (برای موتور TTS انگلیسی)."""
    return BLOCK_LABELS_EN.get(fa_label, fa_label)


# ═══════════════════════════════════════════════════════════════════
# ۳) برنامهٔ چرخش هوشمند هفته (شنبه = ۰  تا  جمعه = ۶)
#    شنبه ← دورهٔ ۱ | یکشنبه ← دورهٔ ۲ | دوشنبه ← دورهٔ ۳ | سه‌شنبه ← دورهٔ ۴
#    چهارشنبه ← مرور هفتگی | پنجشنبه ← پروژهٔ عملی | جمعه ← استراحت مطلق
# ═══════════════════════════════════════════════════════════════════
PERSIAN_DAY_NAMES = [
    "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه",
    "چهارشنبه", "پنجشنبه", "جمعه",
]

COURSE_NAMES = {
    1: "دورهٔ ۱ — مبانی برنامه‌نویسی پایتون",
    2: "دورهٔ ۲ — پایتون پیشرفته و شیءگرایی",
    3: "دورهٔ ۳ — دیتابیس و بک‌اند",
    4: "دورهٔ ۴ — هوش مصنوعی و پروژهٔ نهایی",
    5: "دورهٔ ۵ — تمرین و پروژه عملی",
    6: "دورهٔ ۶ — تمرین و رفع اشکال",
}

# نام‌های سفارشی برای دوره‌های استاندارد
_custom_course_names: dict[int, str] = {}
CUSTOM_COURSE_NAMES_PATH = Path(__file__).resolve().parent / "custom_course_names.json"


def _save_custom_course_names() -> None:
    """ذخیره نام‌های سفارشی دوره‌های استاندارد در فایل JSON."""
    try:
        CUSTOM_COURSE_NAMES_PATH.write_text(
            json.dumps(_custom_course_names, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در ذخیره نام‌های دوره‌های استاندارد: %s", exc)


def _load_custom_course_names() -> None:
    """بارگذاری نام‌های سفارشی دوره‌های استاندارد از فایل JSON."""
    global _custom_course_names
    try:
        if CUSTOM_COURSE_NAMES_PATH.exists():
            loaded = json.loads(CUSTOM_COURSE_NAMES_PATH.read_text(encoding="utf-8"))
            # تبدیل کلیدهای رشته‌ای به عدد صحیح
            _custom_course_names = {int(k): v for k, v in loaded.items()}
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در بارگذاری نام‌های دوره‌های استاندارد: %s", exc)


def set_custom_course_name(course_num: int, name: str) -> None:
    """تنظیم نام سفارشی برای یک دوره استاندارد."""
    _custom_course_names[course_num] = name
    _save_custom_course_names()


def get_course_name(course_id: str) -> str:
    """دریافت نام دوره (چه استاندارد چه سفارشی)."""
    if course_id.isdigit():
        course_num = int(course_id)
        # بررسی نام سفارشی اول
        if course_num in _custom_course_names:
            return _custom_course_names[course_num]
        # استفاده از نام پیش‌فرض
        if course_num in COURSE_NAMES:
            return COURSE_NAMES[course_num]
    
    # بررسی دوره‌های سفارشی
    custom_course = get_custom_course(course_id)
    if custom_course:
        return custom_course["name"]
    
    return course_id

# ═══════════════════════════════════════════════════════════════════
# ۸) مدیریت دوره‌های سفارشی
# ═══════════════════════════════════════════════════════════════════
_custom_courses: dict[str, dict] = {}  # کلید: ID دوره، مقدار: اطلاعات دوره
CUSTOM_COURSES_PATH = Path(__file__).resolve().parent / "custom_courses.json"


def _save_custom_courses() -> None:
    """ذخیره دوره‌های سفارشی در فایل JSON."""
    try:
        CUSTOM_COURSES_PATH.write_text(
            json.dumps(_custom_courses, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در ذخیره دوره‌های سفارشی: %s", exc)


def _load_custom_courses() -> None:
    """بارگذاری دوره‌های سفارشی از فایل JSON."""
    global _custom_courses
    try:
        if CUSTOM_COURSES_PATH.exists():
            loaded = json.loads(CUSTOM_COURSES_PATH.read_text(encoding="utf-8"))
            _custom_courses = loaded
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در بارگذاری دوره‌های سفارشی: %s", exc)


def add_custom_course(course_id: str, name: str, video_min: int = 40, 
                     practice_min: int = 40, debug_min: int = 40, theme_key: str = "course1") -> None:
    """اضافه کردن دوره سفارشی."""
    _custom_courses[course_id] = {
        "name": name,
        "video_min": video_min,
        "practice_min": practice_min,
        "debug_min": debug_min,
        "theme_key": theme_key,
    }
    _save_custom_courses()


def get_custom_course(course_id: str) -> dict | None:
    """دریافت اطلاعات دوره سفارشی."""
    return _custom_courses.get(course_id)


def get_all_custom_courses() -> dict[str, dict]:
    """دریافت تمام دوره‌های سفارشی."""
    return _custom_courses.copy()


def delete_custom_course(course_id: str) -> bool:
    """حذف دوره سفارشی."""
    if course_id in _custom_courses:
        del _custom_courses[course_id]
        _save_custom_courses()
        return True
    return False

PRACTICE_DEBUG_BLOCKS_MIN = [
    ("تمرین عملی و کدنویسی �", 60),
    ("رفع اشکال و تست 🔧", 60),
]


def _std_blocks() -> list[tuple[str, int]]:
    """بخش‌های استاندارد (برحسب ثانیه) - از متغیرهای جهانی استفاده می‌کند."""
    if os.environ.get("STUDY_TIMER_FAST") == "1":
        return [(lab, FAST_BLOCK_SECONDS) for lab in BLOCK_LABELS_FA]
    # استفاده از متغیرهای جهانی که توسط کاربر قابل تغییر هستند
    minutes = [VIDEO_MIN, PRACTICE_MIN, DEBUG_MIN]
    return [(lab, m * 60) for lab, m in zip(BLOCK_LABELS_FA, minutes)]


def _to_seconds(blocks_min: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """تبدیل فهرست (برچسب، دقیقه) به (برچسب، ثانیه) + حالت تست سریع."""
    if os.environ.get("STUDY_TIMER_FAST") == "1":
        return [(lab, FAST_BLOCK_SECONDS) for lab, _ in blocks_min]
    return [(lab, m * 60) for lab, m in blocks_min]


def _custom_blocks_to_seconds(course_id: str) -> list[tuple[str, int]]:
    """تبدیل بخش‌های دوره سفارشی به ثانیه."""
    custom_course = get_custom_course(course_id)
    if not custom_course:
        return []
    
    blocks = [
        ("تماشای ویدیو آموزشی 🎥", custom_course["video_min"] * 60),
        ("تمرین عملی و کدنویسی 💻", custom_course["practice_min"] * 60),
        ("رفع اشکال و جمع‌بندی 📝", custom_course["debug_min"] * 60),
    ]
    
    if os.environ.get("STUDY_TIMER_FAST") == "1":
        return [(lab, FAST_BLOCK_SECONDS) for lab, _ in blocks]
    
    return blocks


# ═══════════════════════════════════════════════════════════════════
# ۷) تنظیمات دوره دلخواه برای هفته‌های مختلف
# ═══════════════════════════════════════════════════════════════════
_weekly_schedules: dict[str, dict[int, dict]] = {}  # کلید: هفته (فرمت YYYY-WW)
WEEKLY_SCHEDULES_PATH = Path(__file__).resolve().parent / "weekly_schedules.json"


def get_week_key(date_obj: date) -> str:
    """دریافت کلید هفته به فرمت YYYY-WW"""
    year, week, _ = date_obj.isocalendar()
    return f"{year}-{week:02d}"


def set_week_schedule(week_key: str, schedule: dict[int, dict]) -> None:
    """تنظیم برنامه برای یک هفته خاص."""
    _weekly_schedules[week_key] = schedule
    _save_weekly_schedules()


def get_week_schedule(week_key: str) -> dict[int, dict] | None:
    """دریافت برنامه برای یک هفته خاص."""
    return _weekly_schedules.get(week_key)


def reset_week_schedule(week_key: str) -> None:
    """حذف برنامه برای یک هفته خاص."""
    if week_key in _weekly_schedules:
        del _weekly_schedules[week_key]
        _save_weekly_schedules()


def reset_all_custom_schedules() -> None:
    """حذف تمام برنامه‌های سفارشی."""
    _weekly_schedules.clear()
    _save_weekly_schedules()


def _save_weekly_schedules() -> None:
    """ذخیره برنامه‌های هفته‌ای در فایل JSON."""
    try:
        WEEKLY_SCHEDULES_PATH.write_text(
            json.dumps(_weekly_schedules, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در ذخیره برنامه‌های هفته‌ای: %s", exc)


def _load_weekly_schedules() -> None:
    """بارگذاری برنامه‌های هفته‌ای از فایل JSON."""
    global _weekly_schedules
    try:
        if WEEKLY_SCHEDULES_PATH.exists():
            loaded = json.loads(WEEKLY_SCHEDULES_PATH.read_text(encoding="utf-8"))
            # تبدیل کلیدهای رشته‌ای به عدد صحیح
            converted = {}
            for week_key, week_schedule in loaded.items():
                converted_schedule = {}
                for day_key, day_schedule in week_schedule.items():
                    # تبدیل کلید روز از رشته به عدد
                    day_idx = int(day_key)
                    converted_schedule[day_idx] = day_schedule
                converted[week_key] = converted_schedule
            _weekly_schedules = converted
    except Exception as exc:
        logging.getLogger("study-timer").warning("خطا در بارگذاری برنامه‌های هفته‌ای: %s", exc)


# بارگذاری خودکار هنگام ایمپورت
_load_weekly_schedules()
_load_custom_courses()
_load_custom_course_names()


def get_current_week_schedule() -> dict[int, dict] | None:
    """دریافت برنامه برای هفته جاری."""
    return get_week_schedule(get_week_key(get_today()))


def get_schedule() -> dict:
    """دریافت برنامه هفتگی با زمان‌های به‌روز (برای پشتیبانی از تغییر زمان توسط کاربر)."""
    # اگر برنامه برای هفته جاری تنظیم شده، از آن استفاده کن
    try:
        current_week_schedule = get_current_week_schedule()
        if current_week_schedule is not None:
            return current_week_schedule
    except:
        # اگر هنوز get_today تعریف نشده، از برنامه پیش‌فرض استفاده کن
        pass
    
    return {
        # ── شنبه تا پنجشنبه: دوره‌های ۱ تا ۵ (هر کدام ۳ بخش با زمان قابل تنظیم) ──
        0: {"type": "course", "course": 1, "theme_key": "course1", "blocks": _std_blocks()},
        1: {"type": "course", "course": 2, "theme_key": "course2", "blocks": _std_blocks()},
        2: {"type": "course", "course": 3, "theme_key": "course3", "blocks": _std_blocks()},
        3: {"type": "course", "course": 4, "theme_key": "course4", "blocks": _std_blocks()},
        4: {"type": "course", "course": 5, "theme_key": "course1", "blocks": _std_blocks()},
        5: {"type": "course", "course": 6, "theme_key": "course2", "blocks": _std_blocks()},
        # ── جمعه: استراحت مطلق ──
        6: {"type": "rest", "course": None, "theme_key": "rest", "blocks": []},
    }

# نسخهٔ قدیمی برای سازگاری (اما برنامه باید از get_schedule() استفاده کند)
# SCHEDULE = get_schedule()  # غیرفعال شد چون در زمان ایمپورت مشکل دارد

_SPECIAL_TITLES = {
    "review": "مرور و بازنگری هفتگی 📚",
    "project": "پروژهٔ عملی و رفع اشکال تجمعی 🛠️",
    "practice_debug": "تمرین و رفع اشکال 🔧",
    "rest": "استراحت مطلق 💤",
}


def schedule_title(sched: dict) -> str:
    """عنوان خوانای برنامهٔ امروز."""
    if sched["type"] == "course":
        return get_course_name(str(sched["course"]))
    elif sched["type"] == "custom":
        return get_course_name(sched["course"])
    return _SPECIAL_TITLES[sched["type"]]


# ═══════════════════════════════════════════════════════════════════
# ۴) ابزارهای تاریخ (روز شمسی + تبدیل میلادی → شمسی)
# ═══════════════════════════════════════════════════════════════════
_today_override: date | None = None


def set_today_override(d: date) -> None:
    """برای تست/شبیه‌سازی: تاریخ امروز را ثابت می‌کند."""
    global _today_override
    _today_override = d


def get_today() -> date:
    return _today_override if _today_override is not None else date.today()


def persian_day_index(d: date | None = None) -> int:
    """
    اندیس روز شمسی: شنبه=۰، یکشنبه=۱، ...، جمعه=۶
    (ورودی: آبجکت date میلادی)
    """
    d = d or get_today()
    # در پایتون: دوشنبه=۰ ... یکشنبه=۶
    py_map = {5: 0, 6: 1, 0: 2, 1: 3, 2: 4, 3: 5, 4: 6}  # میلادی → شمسی
    return py_map[d.weekday()]


JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """
    تبدیل تاریخ میلادی به شمسی (الگوریتم استاندارد jdf).
    خروجی: (سال، ماه، روز) شمسی
    """
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = (365 * gy2) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400)
    # g_d_m[gm2] = تعداد روزهای سپری‌شده تا ابتدای ماه جاری
    g_day_no += g_d_m[gm2]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day_no += 1  # روز ۲۹ بهمن در سال کبیسه
    g_day_no += gd2

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + (33 * j_np) + (4 * (j_day_no // 1461))
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + (j_day_no // 31)
        jd = 1 + (j_day_no % 31)
    else:
        jm = 7 + ((j_day_no - 186) // 30)
        jd = 1 + ((j_day_no - 186) % 30)
    return jy, jm, jd


def format_jalali_date(d: date | None = None) -> str:
    """مثال: «شنبه • ۲۹ مرداد ۱۴۰۵»"""
    d = d or get_today()
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{PERSIAN_DAY_NAMES[persian_day_index(d)]} • {jd} {JALALI_MONTHS[jm - 1]} {jy}"


# ═══════════════════════════════════════════════════════════════════
# ۵) عبارات صوتی (فارسی + انگلیسی برای TTS)
# ═══════════════════════════════════════════════════════════════════
VOICE_PHRASES = {
    "fa": {
        "session_start": "جلسه شروع شد؛ موفق باشی!",
        "block_end": "وقت «{done}» تمام شد! برید سراغ «{nxt}»!",
        "session_complete": "آفرین! جلسهٔ امروز با موفقیت کامل شد؛ به خودت افتخار کن!",
        "session_rest": "امروز روز استراحت مطلق است؛ فقط آرام باش!",
    },
    "en": {
        "session_start": "Session started. Good luck and stay focused!",
        "block_end": "Time for {done} is over! Now go to {nxt}!",
        "session_complete": "Well done! Today's session is complete. Be proud of yourself!",
        "session_rest": "Today is a total rest day. Just relax!",
    },
}

REST_MESSAGES = [
    "استراحت، بخشی از موفقیت است؛ نه فرار از آن. 🌙",
    "مغزت امروز خیلی کار کرده؛ بگذار جادوی استراحت کارش را بکند. ✨",
    "امروز فقط برای توست؛ هیچ تایمری فعال نیست. 💜",
    "هر قهرمانی به روزهای استراحت نیاز دارد؛ تو هم قهرمانی! 🏆",
    "دور از کتاب‌ها، اما نزدیک به آرامش. ☁️",
]


def voice_message(key: str, lang: str, **params) -> str:
    """ساخت متنِ گفتنی برای یک رویداد صوتی."""
    phrase = VOICE_PHRASES[lang][key]
    if params:
        return phrase.format(**params)
    return phrase


# ═══════════════════════════════════════════════════════════════════
# ۶) ابزارهای متن (تشخیص فارسی، حذف ایموجی، اعداد فارسی)
# ═══════════════════════════════════════════════════════════════════
_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_EMOJI_RE = re.compile(
    r"[\U0001F000-\U0001FAFF"      # ایموجی‌های اصلی
    r"\u2190-\u21FF"               # فلش‌ها (↺)
    r"\u2300-\u27BF"               # نمادها (⏸ ▶ ✓)
    r"\u2B00-\u2BFF"               # اشکال (⭐)
    r"\uFE0F"                      # واریاسیون رنگی
    r"\u00A9\u00AE]"
)


def has_persian(text: str) -> bool:
    return bool(_PERSIAN_RE.search(text))


def strip_emoji(text: str) -> str:
    """حذف ایموجی‌ها از متن پیش از ارسال به موتور گفتار."""
    return _EMOJI_RE.sub("", text)
