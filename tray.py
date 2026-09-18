# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  tray.py — آیکون سینی سیستم ویندوز (System Tray)
═══════════════════════════════════════════════════════════════════════
  با بستن پنجره، برنامه به سینی سیستم منتقل می‌شود (تسک‌بار را اشغال
  نمی‌کند). منوی راست‌کلیک: نمایش پنجره / شروع / توقف-ادامه / خروج.

  اگر pystray در دسترس نباشد یا محیط گرافیکی آن را پشتیبانی نکند،
  برنامه بدون سینی هم به‌درستی کار می‌کند (بستن پنجره = خروج کامل).
"""

from __future__ import annotations

import logging

logger = logging.getLogger("study-timer")

_TRAY_AVAILABLE = False
try:
    import pystray  # noqa: F401
    from PIL import Image, ImageDraw  # noqa: F401
    _TRAY_AVAILABLE = True
except Exception as exc:  # محیط بدون سینی (مثلاً لینوکسِ بدون X یا نبودِ pystray)
    logger.info("سینی سیستم در دسترس نیست: %s", exc)


def is_available() -> bool:
    return _TRAY_AVAILABLE


def _make_icon_image():
    """طراحی آیکون ۶۴×۶۴: پس‌زمینهٔ تیره + ساعت سفید (با Pillow)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (2, 2, 62, 62), radius=14, fill=(16, 22, 51, 255),
        outline=(76, 141, 255, 255), width=3,
    )
    cx, cy, r = 32, 32, 20
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(234, 242, 255, 255), width=4)
    draw.line((cx, cy, cx, cy - 13), fill=(234, 242, 255, 255), width=4)          # عقربهٔ دقیقه
    draw.line((cx, cy, cx + 10, cy + 4), fill=(234, 242, 255, 255), width=4)      # عقربهٔ ساعت
    draw.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(76, 141, 255, 255))
    return img


def _build_menu(callbacks: dict, persian: bool):
    """ساخت منوی راست‌کلیک سینی (فارسی یا انگلیسی به‌عنوان fallback)."""
    import pystray
    if persian:
        items = [
            ("نمایش پنجره", "show"),
            ("شروع تایمر", "start"),
            ("توقف / ادامه", "toggle"),
            ("خروج", "quit"),
        ]
    else:
        items = [
            ("Show window", "show"),
            ("Start timer", "start"),
            ("Pause / Resume", "toggle"),
            ("Quit", "quit"),
        ]
    menu_items = [
        pystray.MenuItem(label, (lambda cb: lambda: callbacks.get(cb)())(key))
        for label, key in items[:3]
    ]
    menu_items.append(pystray.Menu.SEPARATOR)
    menu_items.append(pystray.MenuItem(
        items[3][0], (lambda cb: lambda: callbacks.get(cb)())(items[3][1])))
    return pystray.Menu(*menu_items)


def create_tray(callbacks: dict) -> object | None:
    """
    ساخت آیکون سینی.
    callbacks: {"show": fn, "start": fn, "toggle": fn, "quit": fn}
    خروجی: آبجکت pystray.Icon یا None (وقتی سینی در دسترس نیست)

    اول با منوی فارسی ساخته می‌شود؛ اگر backend نتواند یونیکد را کدگذاری کند
    (مثل بعضی محیط‌های لینوکسی)، خودکار با منوی انگلیسی دوباره تلاش می‌کند.
    """
    if not _TRAY_AVAILABLE:
        return None
    try:
        import pystray
        icon = pystray.Icon("study_timer_pro", _make_icon_image(),
                            "Study Timer Pro — تایمر هوشمند مطالعه",
                            _build_menu(callbacks, persian=True))
        return icon
    except Exception as exc:
        logger.warning("ساخت سینی با منوی فارسی ناموفق بود (%s)؛ تلاش با انگلیسی...", exc)
    try:
        import pystray
        icon = pystray.Icon("study_timer_pro", _make_icon_image(),
                            "Study Timer Pro",
                            _build_menu(callbacks, persian=False))
        return icon
    except Exception as exc:
        logger.warning("ساخت آیکون سینی ناموفق بود: %s", exc)
        return None
