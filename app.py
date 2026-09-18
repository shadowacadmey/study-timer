# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  app.py — رابط کاربری گرافیکی Study Timer Pro (CustomTkinter)
═══════════════════════════════════════════════════════════════════════
  ویژگی‌ها:
    • تایمر ۳ بخشی خودکار و پیاپی (ویدیو → تمرین → رفع اشکال)
    • اعلان صوتی مردانه در پایان هر بخش (pyttsx3 + fallback)
    • تم رنگی داینامیکِ اختصاصی برای هر دوره / هر روز
    • چرخش هوشمند روزهای هفته (شنبه تا سه‌شنبه = دورهٔ ۱ تا ۴،
      چهارشنبه = مرور، پنجشنبه = پروژه، جمعه = استراحتِ انیمیشنی)
    • دکمه‌های کنترل بزرگ و هاوردار، سینی سیستم، ذخیرهٔ خودکار JSON

  نکتهٔ معماری: حلقهٔ تایمر با after() در نخ اصلی اجرا می‌شود (thread-safe)
  و کارهای سنگین (صدا، سینی) در نخ‌های جداگانه (daemon) انجام می‌شوند.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import threading
import time
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import font as tkfont

import customtkinter as ctk

import config
import themes
import tray as tray_mod
from history import History
from voice import VoiceNotifier

APP_TITLE = "Study Timer Pro"
WIDTH, HEIGHT = 1000, 720
BASE_DIR = Path(__file__).resolve().parent
HISTORY_PATH = BASE_DIR / "history.json"
SETTINGS_PATH = BASE_DIR / "settings.json"
LOG_PATH = BASE_DIR / "app.log"

DEFAULT_SETTINGS = {
    "voice_mode": "beep",
    "volume": 1.0,
    "custom_sound_file": "",
    "auto_next_block": True,
    "show_stats": True,
    "show_motivation": True,
    "font_size": "medium"
}

# ─────────────────────────────── ابزارهای نمایشی ───────────────────────────────

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(value) -> str:
    """تبدیل ارقام انگلیسی به فارسی (۰-۹ → ۰-۹ فارسی)."""
    return str(value).translate(FA_DIGITS)


def format_mmss(seconds: float) -> str:
    secs = max(0, int(round(seconds)))
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    if h:
        return fa_num(f"{h}:{m:02d}:{s:02d}")
    return fa_num(f"{m:02d}:{s:02d}")


def human_duration(seconds) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return fa_num(f"{h} ساعت و {m} دقیقه")
    if m:
        return fa_num(f"{m} دقیقه")
    return fa_num(f"{s} ثانیه")


def hex_blend(c1: str, c2: str, t: float) -> str:
    """درون‌یابی رنگ‌ها (برای گرادیان)."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    return "#%02x%02x%02x" % (
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def pick_font_family(root: tk.Misc) -> str:
    """انتخاب خودکار فونت مناسب (فارسی‌پشتیبان) بین پلتفرم‌ها."""
    try:
        available = set(tkfont.families(root))
    except Exception:
        return "TkDefaultFont"
    for fam in ("Segoe UI", "Tahoma", "Vazirmatn", "Noto Sans Arabic", "DejaVu Sans"):
        if fam in available:
            return fam
    return "TkDefaultFont"


def get_font_size(base_size: int) -> int:
    """دریافت اندازه فونت بر اساس تنظیمات."""
    multipliers = {"small": 0.85, "medium": 1.0, "large": 1.15}
    return int(base_size * multipliers.get(config.FONT_SIZE, 1.0))


# ─────────────────────────────── مدیریت تنظیمات ───────────────────────────────

class Settings:
    """خواندن/نوشتن تنظیمات کاربر در فایل settings.json."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> "Settings":
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                for key in DEFAULT_SETTINGS:
                    if key in loaded:
                        self.data[key] = loaded[key]
        except Exception as exc:
            logging.getLogger("study-timer").warning("خطا در خواندن تنظیمات: %s", exc)
        return self

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logging.getLogger("study-timer").warning("خطا در ذخیرهٔ تنظیمات: %s", exc)


# ─────────────────────────────── صفحهٔ استراحت جمعه ───────────────────────────────

class RestView(ctk.CTkFrame):
    """
    نمای انیمیشنیِ آرامش‌بخش برای جمعه:
    گرادیان رویایی + ماهِ هلالی + ستاره‌های چشمک‌زن + پیام‌های انگیزشی چرخشی.
    """

    def __init__(self, master, theme: dict, font_family: str, stats_text: str, **kw):
        super().__init__(master, fg_color=theme["bg"], corner_radius=0, **kw)
        self.theme = theme
        self.font_family = font_family
        self.stats_text = stats_text

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=theme["bg"])
        self.canvas.pack(fill="both", expand=True)

        self._gradient = None
        self._stars: list = []
        self._moon_ids: list = []
        self._moon_coords: list = []
        self._title_id = None
        self._msg_id = None
        self._stats_id = None
        self._footer_id = None
        self._msg_idx = 0
        self._msg_elapsed = 0.0
        self._t = 0.0

        self.canvas.bind("<Configure>", lambda e: self._rebuild())
        self._rebuild()

    # ─────────────────────────── رسم ───────────────────────────
    def _rebuild(self) -> None:
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 20 or h < 20:
            return
        c = self.canvas
        c.delete("all")
        self._stars = []

        # ۱) پس‌زمینهٔ گرادیانی (۶۰ نوار رنگی)
        bands = 60
        for i in range(bands):
            color = hex_blend(self.theme["grad_top"], self.theme["grad_bottom"],
                              i / (bands - 1))
            c.create_rectangle(0, int(h * i / bands), w, int(h * (i + 1) / bands) + 1,
                               fill=color, outline="")

        # ۲) ماهِ هلالی
        mx, my, mr = int(w * 0.5), int(h * 0.30), 46
        moon = c.create_oval(mx - mr, my - mr, mx + mr, my + mr,
                             fill="#FDE68A", outline="")
        cut = c.create_oval(mx + mr - 22, my - mr - 10, mx + mr + 30, my + mr + 10,
                            fill=self.theme["grad_top"], outline="")
        self._moon_ids = [moon, cut]
        self._moon_coords = [
            (mx - mr, my - mr, mx + mr, my + mr),
            (mx + mr - 22, my - mr - 10, mx + mr + 30, my + mr + 10),
        ]

        # ۳) ستاره‌های چشمک‌زن
        rnd = random.Random(1405)
        for _ in range(80):
            x = rnd.uniform(0, w)
            y = rnd.uniform(0, h * 0.82)
            base_r = rnd.uniform(1.0, 2.8)
            phase = rnd.uniform(0, 2 * math.pi)
            speed = rnd.uniform(0.6, 1.8)
            color = rnd.choice(self.theme["stars"])
            oid = c.create_oval(x, y, x + base_r, y + base_r, fill=color, outline="")
            self._stars.append([oid, x, y, base_r, phase, speed])

        # ۴) ابرهای آرام پایین صفحه
        cloud_color = hex_blend(self.theme["grad_bottom"], "#3B2E6B", 0.35)
        for cx0, cy0, cw, ch in ((0.12, 0.88, 0.30, 0.05), (0.55, 0.92, 0.34, 0.06),
                                 (0.75, 0.85, 0.26, 0.05)):
            c.create_oval(int(w * cx0), int(h * cy0), int(w * (cx0 + cw)), int(h * (cy0 + ch)),
                          fill=cloud_color, outline="")

        # ۵) متن‌ها
        self._title_id = c.create_text(
            w // 2, int(h * 0.52),
            text="استراحت مطلق 💤",
            fill=self.theme["text"],
            font=(self.font_family, 30, "bold"),
        )
        msg_text = config.REST_MESSAGES[self._msg_idx] if config.SHOW_MOTIVATION else ""
        self._msg_id = c.create_text(
            w // 2, int(h * 0.62),
            text=msg_text,
            fill=self.theme["subtext"],
            font=(self.font_family, 15),
            width=w - 240,
        )
        self._stats_id = c.create_text(
            w // 2, int(h * 0.72),
            text=self.stats_text,
            fill=self.theme["accent"],
            font=(self.font_family, 15, "bold"),
        )
        self._footer_id = c.create_text(
            w // 2, int(h * 0.80),
            text="هیچ تایمری امروز فعال نیست؛ فقط نفس بکش. ☁️",
            fill=self.theme["subtext"],
            font=(self.font_family, 12),
        )

    # ─────────────────────────── انیمیشن ───────────────────────────
    def on_tick(self, dt: float) -> None:
        self._t += dt

        # چشمک زدن ستاره‌ها (فاز هر ستاره در خودِ لیست به‌روز می‌شود)
        for st in self._stars:
            st[4] += dt * st[5]
            r = st[3] * (0.55 + 0.45 * math.sin(st[4]))
            self.canvas.coords(st[0], st[1] - r, st[2] - r, st[1] + r, st[2] + r)

        # چرخش پیام انگیزشی هر ۷ ثانیه
        self._msg_elapsed += dt
        if config.SHOW_MOTIVATION and self._msg_elapsed >= 7.0:
            self._msg_elapsed = 0.0
            self._msg_idx = (self._msg_idx + 1) % len(config.REST_MESSAGES)
            self.canvas.itemconfigure(
                self._msg_id, text=config.REST_MESSAGES[self._msg_idx]
            )

        # نوسانِ نرمِ ماه به بالا/پایین (بدون دریفت — مکان مطلق از _t محاسبه می‌شود)
        if self._moon_ids:
            dy = math.sin(self._t * 0.5) * 6
            for oid, (x0, y0, x1, y1) in zip(self._moon_ids, self._moon_coords):
                self.canvas.coords(oid, x0, y0 + dy, x1, y1 + dy)


# ─────────────────────────────── برنامهٔ اصلی ───────────────────────────────

class StudyTimerApp(ctk.CTk):
    def __init__(self, simulate_date: str | None = None, win_pos: str | None = None):
        super().__init__()
        self._setup_logger()
        self.logger.info("برنامه در حال اجرا...")

        if simulate_date:
            try:
                y, m, d = map(int, simulate_date.split("-"))
                config.set_today_override(date(y, m, d))
                self.logger.info("شبیه‌سازی تاریخ: %s", simulate_date)
            except Exception:
                self.logger.warning("تاریخ شبیه‌سازی نامعتبر است: %s", simulate_date)

        # ── داده‌ها ──
        self.settings = Settings(SETTINGS_PATH)
        self.history = History(HISTORY_PATH)
        self.voice = VoiceNotifier(
            mode=self.settings.data.get("voice_mode", "beep"),
            volume=self.settings.data.get("volume", 1.0),
            custom_sound_file=self.settings.data.get("custom_sound_file", ""),
        )
        
        # اعمال تنظیمات رفتاری به config
        config.set_auto_next_block(self.settings.data.get("auto_next_block", True))
        config.set_show_stats(self.settings.data.get("show_stats", True))
        config.set_show_motivation(self.settings.data.get("show_motivation", True))
        config.set_font_size(self.settings.data.get("font_size", "medium"))
        
        self.today = config.get_today()
        self.day_index = config.persian_day_index(self.today)
        self.schedule = config.get_schedule()[self.day_index]
        self.theme = themes.THEMES[self.schedule["theme_key"]]
        self.sched_title = config.schedule_title(self.schedule)

        # ── پنجره ──
        ctk.set_appearance_mode("dark")  # حالت تاریک برای طراحی حرفه‌ای
        self.title(APP_TITLE)
        self.configure(fg_color=self.theme["bg"])
        geometry = f"{WIDTH}x{HEIGHT}"
        if win_pos:
            x, y = win_pos.split(",")
            geometry += f"+{x}+{y}"
        else:
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            geometry += f"+{(sw - WIDTH) // 2}+{(sh - HEIGHT) // 2 - 20}"
        self.geometry(geometry)
        self.resizable(False, False)
        self.font = pick_font_family(self)

        # ── وضعیت تایمر ──
        self.blocks = [
            {"label": lab, "seconds": sec, "status": "pending"}
            for lab, sec in self.schedule["blocks"]
        ]
        self.block_index = 0
        self.remaining = float(self.blocks[0]["seconds"]) if self.blocks else 0.0
        self.running = False
        self.paused = False
        self.session_complete = False
        self._started = False
        self._last_tick = None
        self._tray_icon = None
        self.rest_view = None
        self.block_widgets = []

        # ── ساخت رابط ──
        self._build_ui()
        self.apply_theme(self.theme)
        self._setup_tray()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<space>", lambda e: self._toggle_start_pause())
        self.bind("<r>", lambda e: self.reset_timer())
        self.after(200, self._tick)

    # ═══════════════════════════════ ثبت وقایع ═══════════════════════════════

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("study-timer")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            try:
                handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                self.logger.addHandler(handler)
            except Exception:
                pass

    # ═══════════════════════════════ ساخت رابط ═══════════════════════════════

    def _build_ui(self) -> None:
        # نوار رنگی بالای پنجره (رنگ دورهٔ فعال) با گرادیان
        self.accent_bar = ctk.CTkFrame(self, height=8, corner_radius=0,
                                       fg_color=self.theme["accent"])
        self.accent_bar.pack(fill="x")

        # ── سربرگ لوکس ──
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=32, pady=(20, 8))
        self.header.grid_columnconfigure(0, weight=1)

        # لوگو و عنوان با طراحی حرفه‌ای
        title_frame = ctk.CTkFrame(self.header, fg_color=self.theme["panel"], 
                                   corner_radius=16, border_width=2, 
                                   border_color=self.theme["card_border"])
        title_frame.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 16))
        
        self.title_lbl = ctk.CTkLabel(title_frame, text="⏱️ Study Timer Pro",
                                      font=(self.font, 22, "bold"), text_color=self.theme["accent"])
        self.title_lbl.pack(padx=20, pady=(12, 4))
        
        self.subtitle_lbl = ctk.CTkLabel(title_frame, text="جلسات هوشمند ۳ بخشی • تحلیل پیشرفته",
                                         font=(self.font, 11), text_color=self.theme["subtext"])
        self.subtitle_lbl.pack(padx=20, pady=(0, 12))

        chips = ctk.CTkFrame(self.header, fg_color="transparent")
        chips.grid(row=0, column=1, rowspan=2, sticky="e")

        # چیپ تاریخ شمسی با طراحی مدرن
        date_text = config.format_jalali_date(self.today)
        self.day_chip = ctk.CTkFrame(chips, corner_radius=24, 
                                     fg_color=self.theme["accent_soft"], 
                                     border_width=1, border_color=self.theme["accent"])
        self.day_chip.pack(side="left", padx=(0, 12))
        self.day_chip_lbl = ctk.CTkLabel(self.day_chip, text=date_text,
                                         font=(self.font, 13, "bold"), text_color=self.theme["text"])
        self.day_chip_lbl.pack(padx=16, pady=8)

        # چیپ دوره / حالت روز با طراحی شیک
        self.course_chip = ctk.CTkFrame(chips, corner_radius=24,
                                       fg_color=self.theme["accent"],
                                       border_width=2, border_color=self.theme["accent_hover"])
        self.course_chip.pack(side="left", padx=(0, 12))
        
        # پیام واضح برای نوبت دوره
        day_name = config.PERSIAN_DAY_NAMES[self.day_index]
        if self.schedule["type"] == "course":
            course_msg = f"امروز {day_name} • {self.sched_title}"
        elif self.schedule["type"] == "custom":
            course_msg = f"امروز {day_name} • {self.sched_title}"
        elif self.schedule["type"] == "review":
            course_msg = f"امروز {day_name} • مرور هفتگی"
        elif self.schedule["type"] == "project":
            course_msg = f"امروز {day_name} • پروژه عملی"
        else:  # rest
            course_msg = f"امروز {day_name} • استراحت"
        
        self.course_chip_lbl = ctk.CTkLabel(self.course_chip, text=course_msg,
                                            font=(self.font, 13, "bold"), text_color=self.theme["chip_text"])
        self.course_chip_lbl.pack(padx=18, pady=8)

        # دکمهٔ تنظیمات با طراحی آیکون‌محور
        self.settings_btn = ctk.CTkButton(chips, text="⚙️", width=48, height=40,
                                          corner_radius=14, font=(self.font, 18),
                                          fg_color=self.theme["panel"],
                                          hover_color=self.theme["accent_soft"],
                                          border_width=2, border_color=self.theme["card_border"],
                                          text_color=self.theme["text"],
                                          command=self._open_settings)
        self.settings_btn.pack(side="left")

        # ── بدنه ──
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=26, pady=(6, 10))

        if self.schedule["type"] == "rest":
            week_s = self.history.week_study_seconds(self.today)
            stats_text = f"این هفته {human_duration(week_s)} مطالعه کردی — آفرین! 🎉"
            self.rest_view = RestView(self.content, self.theme, self.font, stats_text)
            self.rest_view.pack(fill="both", expand=True)
        else:
            self._build_study_view()

    def _build_study_view(self) -> None:
        # نوار پیشرفت کل جلسه با طراحی حرفه‌ای
        self.session_frame = ctk.CTkFrame(self.content, fg_color=self.theme["panel"], 
                                          corner_radius=16, border_width=1, 
                                          border_color=self.theme["card_border"])
        self.session_frame.pack(fill="x", pady=(8, 16), padx=8)
        
        progress_header = ctk.CTkFrame(self.session_frame, fg_color="transparent")
        progress_header.pack(fill="x", padx=20, pady=(12, 8))
        
        self.session_lbl = ctk.CTkLabel(progress_header, text="پیشرفت کل جلسه",
                                        font=(self.font, 14, "bold"), text_color=self.theme["text"])
        self.session_lbl.pack(side="left")
        
        self.session_pct = ctk.CTkLabel(progress_header, text=fa_num("۰٪"),
                                        font=(self.font, 16, "bold"), text_color=self.theme["accent"])
        self.session_pct.pack(side="right")
        
        progress_bar_frame = ctk.CTkFrame(self.session_frame, fg_color="transparent")
        progress_bar_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        self.session_bar = ctk.CTkProgressBar(progress_bar_frame, height=12,
                                              corner_radius=6, fg_color=self.theme["progress_bg"],
                                              progress_color=self.theme["accent"])
        self.session_bar.pack(fill="x")
        self.session_bar.set(0)

        # سه کارت بخش با طراحی مدرن
        self.blocks_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.blocks_frame.pack(fill="x", padx=8)
        for i in range(len(self.blocks)):
            self.blocks_frame.grid_columnconfigure(i, weight=1, uniform="blk")
            self.block_widgets.append(self._build_block_card(i))

        # تایمر بزرگ با افکت‌های بصری
        self.clock_frame = ctk.CTkFrame(self.content, fg_color=self.theme["panel"], 
                                       corner_radius=20, border_width=2, 
                                       border_color=self.theme["accent"])
        self.clock_frame.pack(fill="x", pady=(20, 16), padx=8)
        
        self.active_lbl = ctk.CTkLabel(self.clock_frame,
                                       text=self.blocks[0]["label"] if self.blocks else "",
                                       font=(self.font, 18, "bold"), text_color=self.theme["text"])
        self.active_lbl.pack(pady=(20, 8))
        
        self.clock_lbl = ctk.CTkLabel(self.clock_frame, text=format_mmss(self.remaining),
                                      font=(self.font, get_font_size(64), "bold"), text_color=self.theme["accent"])
        self.clock_lbl.pack(pady=(8, 8))
        
        self.status_lbl = ctk.CTkLabel(self.clock_frame,
                                       text="برای شروع، دکمهٔ «شروع» را بزن ✨",
                                       font=(self.font, 14), text_color=self.theme["subtext"])
        self.status_lbl.pack(pady=(8, 20))

        # دکمه‌های کنترل با طراحی آیکون‌محور
        self.controls = ctk.CTkFrame(self.content, fg_color="transparent")
        self.controls.pack(pady=(8, 16))
        
        self.start_btn = ctk.CTkButton(self.controls, text="▶ شروع", width=160, height=56,
                                       corner_radius=18, font=(self.font, get_font_size(16), "bold"),
                                       fg_color=self.theme["accent"], hover_color=self.theme["accent_hover"],
                                       text_color=self.theme["chip_text"], command=self.start_timer)
        self.start_btn.pack(side="left", padx=8)
        
        self.pause_btn = ctk.CTkButton(self.controls, text="⏸ توقف", width=160, height=56,
                                       corner_radius=18, font=(self.font, get_font_size(16), "bold"),
                                       fg_color=self.theme["panel"], hover_color=self.theme["accent_soft"],
                                       border_width=2, border_color=self.theme["card_border"],
                                       text_color=self.theme["text"], command=self._toggle_pause)
        self.pause_btn.pack(side="left", padx=8)
        
        self.reset_btn = ctk.CTkButton(self.controls, text="↺ ریست", width=140, height=56,
                                       corner_radius=18, font=(self.font, get_font_size(16), "bold"),
                                       fg_color=self.theme["panel"], hover_color=self.theme["accent_soft"],
                                       border_width=2, border_color=self.theme["card_border"],
                                       text_color=self.theme["text"], command=self.reset_timer)
        self.reset_btn.pack(side="left", padx=8)

        # دکمه‌های کمکی
        helper_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        helper_frame.pack(pady=(8, 8))
        
        self.skip_btn = ctk.CTkButton(helper_frame, text="⏭ رد شدن از بخش",
                                      width=200, height=36, corner_radius=14,
                                      font=(self.font, 13), fg_color="transparent",
                                      hover_color=self.theme["accent_soft"],
                                      text_color=self.theme["subtext"], command=self.skip_block)
        self.skip_btn.pack(side="left", padx=8)

        # آمار روزانه/کلی با طراحی زیبا
        if config.SHOW_STATS:
            stats_frame = ctk.CTkFrame(self.content, fg_color=self.theme["panel"], 
                                       corner_radius=16, border_width=1, 
                                       border_color=self.theme["card_border"])
            stats_frame.pack(fill="x", pady=(8, 8), padx=8)
            
            self.stats_lbl = ctk.CTkLabel(stats_frame, text=self._stats_text(),
                                          font=(self.font, 13), text_color=self.theme["text"])
            self.stats_lbl.pack(pady=12)
        
        self.tray_hint = ctk.CTkLabel(self.content,
                                      text="🖥️ با بستن پنجره، برنامه در سینی سیستم می‌ماند",
                                      font=(self.font, 11), text_color=self.theme["subtext"])
        self.tray_hint.pack(pady=(0, 8))

    def _build_block_card(self, i: int) -> dict:
        b = self.blocks[i]
        card = ctk.CTkFrame(self.blocks_frame, corner_radius=16, border_width=1)
        card.grid(row=0, column=i, padx=8, sticky="nsew")

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 2))
        badge = ctk.CTkFrame(top, corner_radius=12)
        badge.pack(side="left")
        ctk.CTkLabel(badge, text=fa_num(f"بخش {i + 1}"),
                     font=(self.font, 11, "bold")).pack(padx=10, pady=3)
        status = ctk.CTkLabel(top, text="در انتظار", font=(self.font, 11, "bold"))
        status.pack(side="right")

        lbl = ctk.CTkLabel(card, text=b["label"], font=(self.font, 15, "bold"),
                           wraplength=250)
        lbl.pack(fill="x", padx=14, pady=(0, 8))

        bar = ctk.CTkProgressBar(card, height=12, corner_radius=6)
        bar.pack(fill="x", padx=14, pady=(0, 6))
        bar.set(0)

        time_lbl = ctk.CTkLabel(card, text=format_mmss(b["seconds"]),
                                font=(self.font, 21, "bold"))
        time_lbl.pack(padx=14, pady=(0, 12))

        return {"card": card, "badge": badge, "status": status, "label": lbl,
                "bar": bar, "time": time_lbl}

    # ═══════════════════════════════ تم داینامیک ═══════════════════════════════

    def apply_theme(self, theme: dict) -> None:
        """اعمال پالت رنگیِ دورهٔ فعلی روی کل داشبورد."""
        self.theme = theme
        self.configure(fg_color=theme["bg"])
        self.accent_bar.configure(fg_color=theme["accent"])
        self.title_lbl.configure(text_color=theme["text"])
        self.subtitle_lbl.configure(text_color=theme["subtext"])
        self.day_chip.configure(fg_color=theme["accent_soft"])
        self.day_chip_lbl.configure(text_color=theme["text"])
        self.course_chip.configure(fg_color=theme["accent"])
        self.course_chip_lbl.configure(text_color=theme["chip_text"])
        self.settings_btn.configure(fg_color=theme["accent_soft"],
                                    hover_color=theme["accent"],
                                    text_color=theme["text"])

        if self.schedule["type"] == "rest":
            return  # صفحهٔ استراحت رنگ خود را در ساخت‌اش گرفته است

        self.session_lbl.configure(text_color=theme["text"])
        self.session_bar.configure(progress_color=theme["accent"],
                                   fg_color=theme["progress_bg"])
        self.session_pct.configure(text_color=theme["accent"])
        self.active_lbl.configure(text_color=theme["text"])
        self.clock_lbl.configure(text_color=theme["accent"])
        self.status_lbl.configure(text_color=theme["subtext"])

        self.start_btn.configure(fg_color=theme["accent"],
                                 hover_color=theme["accent_hover"],
                                 text_color=theme["chip_text"])
        for btn in (self.pause_btn, self.reset_btn):
            btn.configure(fg_color=theme["panel"], border_color=theme["card_border"],
                          hover_color=theme["accent_soft"],
                          text_color=theme["text"])
        self.skip_btn.configure(hover_color=theme["accent_soft"],
                                text_color=theme["subtext"])
        if config.SHOW_STATS and hasattr(self, 'stats_lbl'):
            self.stats_lbl.configure(text_color=theme["subtext"])
        self.tray_hint.configure(text_color=theme["subtext"])

        for w in self.block_widgets:
            w["card"].configure(fg_color=theme["panel"],
                                border_color=theme["card_border"])
            w["badge"].configure(fg_color=theme["accent_soft"])
            w["label"].configure(text_color=theme["text"])
            w["bar"].configure(progress_color=theme["accent"],
                               fg_color=theme["progress_bg"])
            w["time"].configure(text_color=theme["text"])
        self._refresh_block_ui()

    # ═══════════════════════════════ حلقهٔ تایمر ═══════════════════════════════

    def _tick(self) -> None:
        try:
            now = time.monotonic()
            if self.running and not self.paused and self.blocks:
                dt = now - self._last_tick
                self._last_tick = now
                self.remaining -= dt
                if self.remaining <= 0:
                    self.remaining = 0.0
                    self._complete_block()
            self._refresh_block_ui()
            if self.rest_view is not None:
                self.rest_view.on_tick(0.2)
        except Exception as exc:
            self.logger.exception("خطا در حلقهٔ تایمر: %s", exc)
        self.after(200, self._tick)

    # ═══════════════════════════════ کنترل‌ها ═══════════════════════════════

    def start_timer(self) -> None:
        if not self.blocks or self.running:
            return
        if self.session_complete:
            self._reset_state()
        self.running = True
        self.paused = False
        self._last_tick = time.monotonic()
        if not self._started:
            self._started = True
            self._set_status("در حال اجرا — موفق باشی 💪")
            self.voice.notify("session_start")
        else:
            self._set_status("ادامه… 💪")
        self._refresh_block_ui()

    def _toggle_pause(self) -> None:
        if not self.blocks or self.session_complete:
            return
        if not self.running:
            self.start_timer()
            return
        if self.paused:
            self.paused = False
            self._last_tick = time.monotonic()
            self._set_status("ادامه… 💪")
            self.pause_btn.configure(text="توقف موقت ⏸")
        else:
            self.paused = True
            self._set_status("مکث شده — هر وقت خواستی ادامه بده ⏸")
            self.pause_btn.configure(text="ادامه ▶")
        self._refresh_block_ui()

    def _toggle_start_pause(self) -> None:
        if self.running:
            self._toggle_pause()
        else:
            self.start_timer()

    def _reset_state(self) -> None:
        self.running = False
        self.paused = False
        self.session_complete = False
        self._started = False
        self.block_index = 0
        for b in self.blocks:
            b["status"] = "pending"
        self.remaining = float(self.blocks[0]["seconds"]) if self.blocks else 0.0
        self.pause_btn.configure(text="توقف موقت ⏸")

    def reset_timer(self) -> None:
        self._reset_state()
        self._set_status("برای شروع، دکمهٔ «شروع» را بزن ✨")
        self._refresh_block_ui()

    def skip_block(self) -> None:
        if not self.blocks or self.session_complete or self.block_index >= len(self.blocks):
            return
        self._complete_block()

    # ═══════════════════════════════ پایان بخش/جلسه ═══════════════════════════════

    def _complete_block(self) -> None:
        b = self.blocks[self.block_index]
        b["status"] = "done"
        label = b["label"]

        # ذخیرهٔ خودکار در تاریخچه
        self.history.add_block(
            self.today.isoformat(), self.day_index,
            config.PERSIAN_DAY_NAMES[self.day_index], self.sched_title,
            label, int(b["seconds"]),
        )
        self.history.save()
        self.logger.info("بخش تمام شد: %s", label)

        nxt = self.block_index + 1
        if nxt < len(self.blocks):
            if config.AUTO_NEXT_BLOCK:
                self.block_index = nxt
                self.blocks[nxt]["status"] = "active"
                self.remaining = float(self.blocks[nxt]["seconds"])
                self._last_tick = time.monotonic()
                self.voice.notify("block_end", done=label, nxt=self.blocks[nxt]["label"])
                self._set_status(f"«{label}» تمام شد — شروع «{self.blocks[nxt]['label']}» 🚀")
            else:
                self.running = False
                self.paused = False
                self.voice.notify("block_end", done=label, nxt=self.blocks[nxt]["label"])
                self._set_status(f"«{label}» تمام شد — برای شروع بخش بعدی دکمه شروع را بزنید")
        else:
            self.running = False
            self.paused = False
            self.session_complete = True
            self.pause_btn.configure(text="توقف موقت ⏸")
            self.voice.notify("session_complete")
            self._set_status("جلسه با موفقیت کامل شد! 🎉 آفرین! 👏")
            if config.SHOW_STATS and hasattr(self, 'stats_lbl'):
                self.stats_lbl.configure(text=self._stats_text())
        self._refresh_block_ui()

    # ═══════════════════════════════ نمایش‌ها ═══════════════════════════════

    def _set_status(self, text: str) -> None:
        self.status_lbl.configure(text=text)

    def _stats_text(self) -> str:
        today_s = self.history.today_study_seconds(self.today.isoformat())
        week_s = self.history.week_study_seconds(self.today)
        total_s = self.history.total_seconds()
        return (
            f"مطالعهٔ امروز: {human_duration(today_s)}    •    "
            f"این هفته: {human_duration(week_s)}    •    "
            f"مجموع کل: {human_duration(total_s)}"
        )

    def _refresh_block_ui(self) -> None:
        t = self.theme
        total_session = sum(b["seconds"] for b in self.blocks)

        # نوار پیشرفت کل جلسه
        if total_session:
            done_secs = 0.0
            for i, b in enumerate(self.blocks):
                if i < self.block_index:
                    done_secs += b["seconds"]
                elif i == self.block_index:
                    done_secs += b["seconds"] - max(0.0, self.remaining)
            pct = max(0.0, min(1.0, done_secs / total_session))
            self.session_bar.set(pct)
            self.session_pct.configure(text=fa_num(f"{int(round(pct * 100))}٪"))

        # کارت‌های بخش
        for i, w in enumerate(self.block_widgets):
            b = self.blocks[i]
            if b["status"] == "done":
                w["bar"].set(1.0)
                w["time"].configure(text="✓ تکمیل")
                w["status"].configure(text="تکمیل شد", text_color=t["success"])
            elif i == self.block_index:
                frac = 1.0 - (self.remaining / b["seconds"]) if b["seconds"] else 1.0
                w["bar"].set(max(0.0, min(1.0, frac)))
                if self.paused:
                    w["status"].configure(text="مکث", text_color=t["glow"])
                elif self.running:
                    w["status"].configure(text="در حال اجرا", text_color=t["accent"])
                else:
                    w["status"].configure(text="آماده", text_color=t["accent"])
                w["time"].configure(text=format_mmss(self.remaining))
            else:
                w["bar"].set(0.0)
                w["time"].configure(text=format_mmss(b["seconds"]))
                w["status"].configure(text="در انتظار", text_color=t["subtext"])

        # تایمر بزرگ و بخش فعال
        if self.blocks:
            if self.block_index < len(self.blocks):
                self.active_lbl.configure(text=self.blocks[self.block_index]["label"])
                self.clock_lbl.configure(text=format_mmss(self.remaining))
            else:
                self.active_lbl.configure(text="جلسهٔ امروز تکمیل شد 🎉")
                self.clock_lbl.configure(text=fa_num("۰۰:۰۰"))

    # ═══════════════════════════════ سینی سیستم ═══════════════════════════════

    def _setup_tray(self) -> None:
        try:
            icon = tray_mod.create_tray({
                "show": lambda: self.after(0, self._show_window),
                "start": lambda: self.after(0, self.start_timer),
                "toggle": lambda: self.after(0, self._toggle_pause),
                "quit": lambda: self.after(0, self._quit),
            })
            if icon is None:
                return
            self._tray_icon = icon
            threading.Thread(target=icon.run, daemon=True).start()
            self.logger.info("سینی سیستم فعال شد.")
        except Exception as exc:
            self.logger.warning("سینی سیستم فعال نشد: %s", exc)
            self._tray_icon = None

    def _on_close(self) -> None:
        """بستن پنجره: اگر سینی داریم → مخفی به سینی، وگرنه خروج کامل."""
        if self._tray_icon is not None:
            self.withdraw()
            try:
                self._tray_icon.notify("برنامه در سینی سیستم فعال است.", APP_TITLE)
            except Exception:
                pass
        else:
            self._quit()

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def _quit(self) -> None:
        try:
            self.history.save()
            self.settings.save()
        except Exception:
            pass
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    # ═══════════════════════════════ پنجرهٔ تنظیمات ═══════════════════════════════

    def _open_settings(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title("تنظیمات")
        win.geometry("700x500")
        win.resizable(False, False)
        win.configure(fg_color=self.theme["bg"])
        win.transient(self)
        win.grab_set()

        t = self.theme
        mode_var = tk.StringVar(value=self.settings.data.get("voice_mode", "beep"))
        vol_var = tk.DoubleVar(value=self.settings.data.get("volume", 1.0) * 100)
        
        # متغیرهای زمان
        video_var = tk.IntVar(value=config.VIDEO_MIN)
        practice_var = tk.IntVar(value=config.PRACTICE_MIN)
        debug_var = tk.IntVar(value=config.DEBUG_MIN)
        
        # متغیرهای تنظیمات جدید
        auto_next_var = tk.BooleanVar(value=self.settings.data.get("auto_next_block", True))
        show_stats_var = tk.BooleanVar(value=self.settings.data.get("show_stats", True))
        show_motivation_var = tk.BooleanVar(value=self.settings.data.get("show_motivation", True))
        font_size_var = tk.StringVar(value=self.settings.data.get("font_size", "medium"))

        # اسکرول باکس برای محتویات اصلی
        scroll_frame = ctk.CTkScrollableFrame(win, fg_color="transparent", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(scroll_frame, text="زمان بخش‌ها (دقیقه)", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 6), anchor="w")
        
        # بخش اول: ویدیو
        video_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        video_frame.pack(fill="x", padx=20, pady=1)
        ctk.CTkLabel(video_frame, text="ویدیو آموزشی:", font=(self.font, 11),
                     text_color=t["text"]).pack(side="left")
        video_entry = ctk.CTkEntry(video_frame, width=70, textvariable=video_var,
                                   font=(self.font, 11))
        video_entry.pack(side="right")
        
        # بخش دوم: تمرین
        practice_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        practice_frame.pack(fill="x", padx=20, pady=1)
        ctk.CTkLabel(practice_frame, text="تمرین عملی:", font=(self.font, 11),
                     text_color=t["text"]).pack(side="left")
        practice_entry = ctk.CTkEntry(practice_frame, width=70, textvariable=practice_var,
                                      font=(self.font, 11))
        practice_entry.pack(side="right")
        
        # بخش سوم: رفع اشکال
        debug_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        debug_frame.pack(fill="x", padx=20, pady=1)
        ctk.CTkLabel(debug_frame, text="رفع اشکال:", font=(self.font, 11),
                     text_color=t["text"]).pack(side="left")
        debug_entry = ctk.CTkEntry(debug_frame, width=70, textvariable=debug_var,
                                    font=(self.font, 11))
        debug_entry.pack(side="right")

        ctk.CTkLabel(scroll_frame, text="نام دوره‌های استاندارد", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 6), anchor="w")
        
        # متغیرهای نام دوره‌ها
        course_name_vars = {}
        for i in range(1, 7):
            # دریافت نام فعلی (سفارشی یا پیش‌فرض)
            current_name = config.get_course_name(str(i))
            course_name_vars[i] = tk.StringVar(value=current_name)
            
            course_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            course_frame.pack(fill="x", padx=20, pady=1)
            ctk.CTkLabel(course_frame, text=f"دوره {i}:", font=(self.font, 11),
                         text_color=t["text"]).pack(side="left")
            course_entry = ctk.CTkEntry(course_frame, width=220, textvariable=course_name_vars[i],
                                        font=(self.font, 11))
            course_entry.pack(side="right")

        ctk.CTkLabel(scroll_frame, text="نحوهٔ اعلان صوتی", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 6), anchor="w")
        options = [
            ("beep", "زنگ پیش‌فرض ویندوز 🔔"),
        ]
        for value, label in options:
            ctk.CTkRadioButton(scroll_frame, text=label, variable=mode_var, value=value,
                               font=(self.font, 12), text_color=t["text"],
                               fg_color=t["accent"], hover_color=t["accent_hover"],
                               border_color=t["card_border"]).pack(
                padx=30, pady=2, anchor="w")

        ctk.CTkLabel(scroll_frame, text="حجم صدا", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 4), anchor="w")
        vol_lbl = ctk.CTkLabel(scroll_frame, text=fa_num(f"{int(vol_var.get())}٪"),
                               font=(self.font, 12, "bold"), text_color=t["accent"])
        vol_lbl.pack(pady=(0, 2))
        slider = ctk.CTkSlider(scroll_frame, from_=0, to=100, variable=vol_var, width=350,
                               fg_color=t["progress_bg"], progress_color=t["accent"],
                               button_color=t["accent"], button_hover_color=t["accent_hover"])
        slider.pack(padx=20)
        slider.configure(command=lambda v: vol_lbl.configure(text=fa_num(f"{int(v)}٪")))

        # تنظیمات رفتاری
        ctk.CTkLabel(scroll_frame, text="تنظیمات رفتاری", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 6), anchor="w")
        
        ctk.CTkCheckBox(scroll_frame, text="شروع خودکار بخش بعدی", variable=auto_next_var,
                       font=(self.font, 12), text_color=t["text"],
                       fg_color=t["accent"], hover_color=t["accent_hover"],
                       border_color=t["card_border"]).pack(padx=30, pady=2, anchor="w")
        
        ctk.CTkCheckBox(scroll_frame, text="نمایش آمار", variable=show_stats_var,
                       font=(self.font, 12), text_color=t["text"],
                       fg_color=t["accent"], hover_color=t["accent_hover"],
                       border_color=t["card_border"]).pack(padx=30, pady=2, anchor="w")
        
        ctk.CTkCheckBox(scroll_frame, text="نمایش پیام‌های انگیزشی", variable=show_motivation_var,
                       font=(self.font, 12), text_color=t["text"],
                       fg_color=t["accent"], hover_color=t["accent_hover"],
                       border_color=t["card_border"]).pack(padx=30, pady=2, anchor="w")
        
        ctk.CTkLabel(scroll_frame, text="اندازه فونت", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(padx=20, pady=(12, 6), anchor="w")
        
        font_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        font_frame.pack(fill="x", padx=20, pady=2)
        
        for size in ["small", "medium", "large"]:
            size_label = {"small": "کوچک", "medium": "متوسط", "large": "بزرگ"}[size]
            ctk.CTkRadioButton(font_frame, text=size_label, variable=font_size_var, value=size,
                               font=(self.font, 13), text_color=t["text"],
                               fg_color=t["accent"], hover_color=t["accent_hover"],
                               border_color=t["card_border"]).pack(side="left", padx=8)

        # پنل پایین برای دکمه‌ها
        bottom_panel = ctk.CTkFrame(win, fg_color=t["panel"], corner_radius=0, height=50)
        bottom_panel.pack(fill="x", side="bottom")
        bottom_panel.pack_propagate(False)

        def save_settings() -> None:
            try:
                # ذخیره زمان‌ها
                video = max(1, min(180, video_var.get()))
                practice = max(1, min(180, practice_var.get()))
                debug = max(1, min(180, debug_var.get()))
                config.set_custom_times(video, practice, debug)
                
                # ذخیره نام‌های دوره‌های استاندارد
                for i in range(1, 7):
                    new_name = course_name_vars[i].get().strip()
                    if new_name and new_name != config.COURSE_NAMES[i]:
                        config.set_custom_course_name(i, new_name)
                
                # ذخیره فایل صوتی سفارشی (فعلاً غیرفعال)
                self.settings.data["custom_sound_file"] = ""
                
                # ذخیره تنظیمات صدا
                self.settings.data["voice_mode"] = mode_var.get()
                self.settings.data["volume"] = max(0.0, min(1.0, vol_var.get() / 100))
                
                # ذخیره تنظیمات رفتاری
                self.settings.data["auto_next_block"] = auto_next_var.get()
                self.settings.data["show_stats"] = show_stats_var.get()
                self.settings.data["show_motivation"] = show_motivation_var.get()
                self.settings.data["font_size"] = font_size_var.get()
                
                self.settings.save()
                self.voice.set_mode(self.settings.data["voice_mode"])
                self.voice.set_volume(self.settings.data["volume"])
                
                # اعمال تنظیمات به config
                config.set_auto_next_block(auto_next_var.get())
                config.set_show_stats(show_stats_var.get())
                config.set_show_motivation(show_motivation_var.get())
                config.set_font_size(font_size_var.get())
                
                # بازسازی برنامه با زمان‌های جدید
                self._reset_state()
                self.blocks = [
                    {"label": lab, "seconds": sec, "status": "pending"}
                    for lab, sec in config._std_blocks()
                ]
                self.remaining = float(self.blocks[0]["seconds"]) if self.blocks else 0.0
                self._refresh_block_ui()
                
                # به‌روزرسانی نام دوره در رابط کاربری
                self.sched_title = config.schedule_title(self.schedule)
                self.course_chip_lbl.configure(text=self.sched_title)
                
                # به‌روزرسانی صدای TTS اگر فعال است
                if self.settings.data.get("voice_mode") == "tts":
                    self.voice.set_mode("tts")
                
                self.logger.info("تنظیمات ذخیره شد: %s", self.settings.data)
                win.destroy()
            except Exception as exc:
                self.logger.warning("خطا در ذخیره تنظیمات: %s", exc)

        def reset_times() -> None:
            config.reset_default_times()
            video_var.set(config.VIDEO_MIN)
            practice_var.set(config.PRACTICE_MIN)
            debug_var.set(config.DEBUG_MIN)

        # دکمه‌ها در پنل پایین
        btns = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        btns.pack(expand=True, fill="both", padx=20, pady=8)
        
        ctk.CTkButton(btns, text="ذخیره ✓", width=90, height=30, corner_radius=8,
                      font=(self.font, 12, "bold"), fg_color=t["accent"],
                      hover_color=t["accent_hover"], text_color=t["chip_text"],
                      command=save_settings).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="مدیریت دوره‌ها 📚", width=110, height=30, corner_radius=8,
                      font=(self.font, 10), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=lambda: self._open_course_manager(win)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="ویرایش هفته 📅", width=90, height=30, corner_radius=8,
                      font=(self.font, 10), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=lambda: self._open_week_editor(win)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="بازنشانی زمان", width=90, height=30, corner_radius=8,
                      font=(self.font, 10), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=reset_times).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="انصراف", width=80, height=30, corner_radius=8,
                      font=(self.font, 12), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=win.destroy).pack(side="left", padx=2)

    def _open_week_editor(self, parent_window) -> None:
        """باز کردن پنجره ویرایش برنامه هفته با امکان تعریف برای هفته‌های مختلف."""
        week_win = ctk.CTkToplevel(self)
        week_win.title("ویرایش برنامه هفته")
        week_win.geometry("700x750")
        week_win.resizable(False, False)
        week_win.configure(fg_color=self.theme["bg"])
        week_win.transient(self)
        week_win.grab_set()

        t = self.theme
        
        # عنوان
        ctk.CTkLabel(week_win, text="مدیریت برنامه هفته", font=(self.font, 18, "bold"),
                     text_color=t["text"]).pack(padx=24, pady=(18, 12))
        
        # اطلاعات هفته جاری
        current_week_key = config.get_week_key(self.today)
        current_week_info = f"هفته جاری: {current_week_key}"
        ctk.CTkLabel(week_win, text=current_week_info, font=(self.font, 14),
                     text_color=t["subtext"]).pack(padx=24, pady=(0, 12))
        
        # انتخاب هفته
        week_frame = ctk.CTkFrame(week_win, fg_color=t["panel"], corner_radius=8)
        week_frame.pack(fill="x", padx=24, pady=8)
        
        ctk.CTkLabel(week_frame, text="انتخاب هفته:", font=(self.font, 13, "bold"),
                     text_color=t["text"]).pack(side="left", padx=12, pady=8)
        
        week_var = tk.StringVar(value=current_week_key)
        # تولید لیست هفته‌های نزدیک (قبل و بعد از هفته جاری)
        current_year, current_week, _ = self.today.isocalendar()
        week_options = []
        for offset in range(-4, 5):  # 4 هفته قبل تا 4 هفته بعد
            if offset == 0:
                week_num = current_week
                year = current_year
            else:
                # محاسبه هفته با آفست
                from datetime import timedelta
                target_date = self.today + timedelta(weeks=offset)
                year, week_num, _ = target_date.isocalendar()
            
            week_key = f"{year}-{week_num:02d}"
            label = f"هفته {week_num} سال {year}"
            if offset == 0:
                label += " (جاری)"
            week_options.append((week_key, label))
        
        week_menu = ctk.CTkOptionMenu(week_frame, values=[label for _, label in week_options],
                                     variable=week_var,
                                     font=(self.font, 12),
                                     fg_color=t["accent_soft"],
                                     button_color=t["accent"],
                                     button_hover_color=t["accent_hover"],
                                     dropdown_fg_color=t["panel"],
                                     dropdown_text_color=t["text"],
                                     text_color=t["text"])
        week_menu.pack(side="right", padx=12, pady=8)
        
        # دریافت برنامه فعلی برای هفته انتخاب شده
        def get_schedule_for_week():
            selected_label = week_var.get()
            selected_key = None
            for key, label in week_options:
                if label == selected_label:
                    selected_key = key
                    break
            schedule = config.get_week_schedule(selected_key) if selected_key else None
            return schedule
        
        # متغیرهای انتخاب دوره برای هر روز
        day_vars = {}
        
        # تابع برای به‌روزرسانی لیست دوره‌ها
        def get_course_options():
            """دریافت لیست گزینه‌های دوره شامل دوره‌های سفارشی."""
            options = ["course1", "course2", "course3", "course4", "course5", "course6", "review", "project", "rest"]
            names = {
                "course1": config.get_course_name("1"),
                "course2": config.get_course_name("2"),
                "course3": config.get_course_name("3"),
                "course4": config.get_course_name("4"),
                "course5": config.get_course_name("5"),
                "course6": config.get_course_name("6"),
                "review": "مرور هفتگی",
                "project": "پروژهٔ عملی",
                "rest": "استراحت",
            }
            
            # اضافه کردن دوره‌های سفارشی به لیست
            custom_courses = config.get_all_custom_courses()
            for course_id, course_info in custom_courses.items():
                options.append(course_id)
                names[course_id] = course_info["name"]
            
            return options, names
        
        course_options, course_names = get_course_options()
        
        # انتخاب برای هر روز
        days_frame = ctk.CTkFrame(week_win, fg_color="transparent")
        days_frame.pack(fill="both", expand=True, padx=24, pady=8)
        
        day_menus = {}  # ذخیره رفرنس به منوها برای به‌روزرسانی
        
        for day_idx, day_name in enumerate(config.PERSIAN_DAY_NAMES):
            frame = ctk.CTkFrame(days_frame, fg_color=t["panel"], corner_radius=8)
            frame.pack(fill="x", pady=4)
            
            ctk.CTkLabel(frame, text=day_name, font=(self.font, 13, "bold"),
                         text_color=t["text"], width=80).pack(side="left", padx=12, pady=8)
            
            day_vars[day_idx] = tk.StringVar()
            
            # منوی کشویی
            day_menu = ctk.CTkOptionMenu(frame, values=list(course_names.values()),
                                        variable=day_vars[day_idx],
                                        font=(self.font, 12),
                                        fg_color=t["accent_soft"],
                                        button_color=t["accent"],
                                        button_hover_color=t["accent_hover"],
                                        dropdown_fg_color=t["panel"],
                                        dropdown_text_color=t["text"],
                                        text_color=t["text"])
            day_menu.pack(side="right", padx=12, pady=8)
            day_menus[day_idx] = day_menu
        
        # تعریف تابع load_week_schedule بعد از ایجاد day_menus
        def load_week_schedule():
            """بارگذاری برنامه برای هفته انتخاب شده."""
            # به‌روزرسانی لیست دوره‌ها شامل دوره‌های سفارشی
            nonlocal course_options, course_names
            course_options, course_names = get_course_options()
            
            schedule = get_schedule_for_week()
            if schedule is None:
                # استفاده از برنامه پیش‌فرض
                schedule = {
                    0: {"type": "course", "course": 1, "theme_key": "course1"},
                    1: {"type": "course", "course": 2, "theme_key": "course2"},
                    2: {"type": "course", "course": 3, "theme_key": "course3"},
                    3: {"type": "course", "course": 4, "theme_key": "course4"},
                    4: {"type": "course", "course": 5, "theme_key": "course1"},
                    5: {"type": "course", "course": 6, "theme_key": "course2"},
                    6: {"type": "rest", "course": None, "theme_key": "rest"}
                }
            
            for day_idx, day_name in enumerate(config.PERSIAN_DAY_NAMES):
                # بررسی وجود روز در برنامه
                if day_idx not in schedule:
                    continue
                    
                day_schedule = schedule[day_idx]
                
                # استخراج کلید دوره بر اساس نوع
                if day_schedule["type"] == "course":
                    if day_schedule["course"]:
                        current_key = f"course{day_schedule['course']}"
                    else:
                        current_key = day_schedule["theme_key"]
                elif day_schedule["type"] == "custom":
                    current_key = day_schedule["course"]
                else:
                    current_key = day_schedule["type"]  # review, project, rest
                
                current_value = course_names.get(current_key, current_key)
                day_vars[day_idx].set(current_value)
                
                # به‌روزرسانی منوی کشویی برای هر روز
                if day_idx in day_menus:
                    day_menus[day_idx].configure(values=list(course_names.values()))
        
        # بارگذاری اولیه
        load_week_schedule()
        
        # بروزرسانی هنگام تغییر هفته
        def on_week_change(*args):
            load_week_schedule()
        
        week_var.trace_add("write", on_week_change)
        
        # دکمه‌ها
        btn_frame = ctk.CTkFrame(week_win, fg_color="transparent")
        btn_frame.pack(pady=18)
        
        def save_week_schedule() -> None:
            try:
                selected_label = week_var.get()
                selected_key = None
                for key, label in week_options:
                    if label == selected_label:
                        selected_key = key
                        break
                
                if not selected_key:
                    return
                
                new_schedule = {}
                for day_idx, day_name in enumerate(config.PERSIAN_DAY_NAMES):
                    selected_name = day_vars[day_idx].get()
                    # پیدا کردن کلید بر اساس نام
                    selected_key_day = None
                    for key, name in course_names.items():
                        if name == selected_name:
                            selected_key_day = key
                            break
                    
                    if selected_key_day:
                        # ساخت برنامه برای این روز
                        if selected_key_day == "rest":
                            new_schedule[day_idx] = {
                                "type": "rest",
                                "course": None,
                                "theme_key": "rest",
                                "blocks": []
                            }
                        elif selected_key_day == "review":
                            new_schedule[day_idx] = {
                                "type": "review",
                                "course": None,
                                "theme_key": "review",
                                "blocks": config._to_seconds(config.REVIEW_BLOCKS_MIN)
                            }
                        elif selected_key_day == "project":
                            new_schedule[day_idx] = {
                                "type": "project",
                                "course": None,
                                "theme_key": "project",
                                "blocks": config._to_seconds(config.PROJECT_BLOCKS_MIN)
                            }
                        elif selected_key_day.startswith("course"):  # course1-6
                            course_num = int(selected_key_day.replace("course", ""))
                            new_schedule[day_idx] = {
                                "type": "course",
                                "course": course_num,
                                "theme_key": selected_key_day,
                                "blocks": config._std_blocks()
                            }
                        else:  # دوره سفارشی
                            custom_course = config.get_custom_course(selected_key_day)
                            if custom_course:
                                # ساخت بخش‌های سفارشی برای این دوره
                                new_schedule[day_idx] = {
                                    "type": "custom",
                                    "course": selected_key_day,
                                    "theme_key": custom_course["theme_key"],
                                    "blocks": config._custom_blocks_to_seconds(selected_key_day)
                                }
                
                # ذخیره برنامه برای هفته انتخاب شده
                config.set_week_schedule(selected_key, new_schedule)
                
                # اگر هفته جاری بود، رابط را بروزرسانی کن
                if selected_key == current_week_key:
                    # دریافت برنامه ذخیره شده
                    saved_schedule = config.get_week_schedule(selected_key)
                    if saved_schedule and self.day_index in saved_schedule:
                        self.schedule = saved_schedule[self.day_index]
                    else:
                        self.schedule = config.get_schedule()[self.day_index]
                    
                    self.theme = themes.THEMES[self.schedule["theme_key"]]
                    self.sched_title = config.schedule_title(self.schedule)
                    
                    # بروزرسانی UI
                    self.apply_theme(self.theme)
                    self.course_chip_lbl.configure(text=self.sched_title)
                    
                    # اگر در حالت استراحت هستیم، رابط را بازسازی کن
                    if self.schedule["type"] == "rest":
                        for widget in self.content.winfo_children():
                            widget.destroy()
                        week_s = self.history.week_study_seconds(self.today)
                        stats_text = f"این هفته {human_duration(week_s)} مطالعه کردی — آفرین! 🎉"
                        self.rest_view = RestView(self.content, self.theme, self.font, stats_text)
                        self.rest_view.pack(fill="both", expand=True)
                    else:
                        if self.rest_view is not None:
                            self.rest_view.destroy()
                            self.rest_view = None
                            self._build_study_view()
                        else:
                            if hasattr(self, 'blocks_frame') and self.blocks_frame is not None:
                                for widget in self.blocks_frame.winfo_children():
                                    widget.destroy()
                                self.block_widgets = []
                                self.blocks = [
                                    {"label": lab, "seconds": sec, "status": "pending"}
                                    for lab, sec in self.schedule["blocks"]
                                ]
                                self.block_index = 0
                                self.remaining = float(self.blocks[0]["seconds"]) if self.blocks else 0.0
                                for i in range(len(self.blocks)):
                                    self.blocks_frame.grid_columnconfigure(i, weight=1, uniform="blk")
                                    self.block_widgets.append(self._build_block_card(i))
                                self._refresh_block_ui()
                        
                        # بروزرسانی برچسب‌های بخش‌ها و تایمر
                        if self.blocks:
                            self.active_lbl.configure(text=self.blocks[0]["label"])
                            self.clock_lbl.configure(text=format_mmss(self.remaining))
                
                self.logger.info(f"برنامه هفته {selected_key} ذخیره شد")
                week_win.destroy()
                parent_window.destroy()
                
            except Exception as exc:
                self.logger.warning("خطا در ذخیره برنامه هفته: %s", exc)
        
        def delete_week_schedule() -> None:
            """حذف برنامه برای هفته انتخاب شده."""
            selected_label = week_var.get()
            selected_key = None
            for key, label in week_options:
                if label == selected_label:
                    selected_key = key
                    break
            
            if selected_key:
                config.reset_week_schedule(selected_key)
                load_week_schedule()
                
                # اگر هفته جاری حذف شد، UI را به برنامه پیش‌فرض برگردان
                if selected_key == current_week_key:
                    self.schedule = config.get_schedule()[self.day_index]
                    self.theme = themes.THEMES[self.schedule["theme_key"]]
                    self.sched_title = config.schedule_title(self.schedule)
                    
                    # بروزرسانی UI
                    self.apply_theme(self.theme)
                    self.course_chip_lbl.configure(text=self.sched_title)
                    
                    # بازسازی رابط
                    if self.schedule["type"] == "rest":
                        for widget in self.content.winfo_children():
                            widget.destroy()
                        week_s = self.history.week_study_seconds(self.today)
                        stats_text = f"این هفته {human_duration(week_s)} مطالعه کردی — آفرین! 🎉"
                        self.rest_view = RestView(self.content, self.theme, self.font, stats_text)
                        self.rest_view.pack(fill="both", expand=True)
                    else:
                        if self.rest_view is not None:
                            self.rest_view.destroy()
                            self.rest_view = None
                            self._build_study_view()
                        else:
                            if hasattr(self, 'blocks_frame') and self.blocks_frame is not None:
                                for widget in self.blocks_frame.winfo_children():
                                    widget.destroy()
                                self.block_widgets = []
                                self.blocks = [
                                    {"label": lab, "seconds": sec, "status": "pending"}
                                    for lab, sec in self.schedule["blocks"]
                                ]
                                self.block_index = 0
                                self.remaining = float(self.blocks[0]["seconds"]) if self.blocks else 0.0
                                for i in range(len(self.blocks)):
                                    self.blocks_frame.grid_columnconfigure(i, weight=1, uniform="blk")
                                    self.block_widgets.append(self._build_block_card(i))
                                self._refresh_block_ui()
                        
                        # بروزرسانی برچسب‌های بخش‌ها و تایمر
                        if self.blocks:
                            self.active_lbl.configure(text=self.blocks[0]["label"])
                            self.clock_lbl.configure(text=format_mmss(self.remaining))
                
                self.logger.info(f"برنامه هفته {selected_key} حذف شد")
        
        ctk.CTkButton(btn_frame, text="ذخیره ✓", width=120, height=42, corner_radius=12,
                      font=(self.font, 15, "bold"), fg_color=t["accent"],
                      hover_color=t["accent_hover"], text_color=t["chip_text"],
                      command=save_week_schedule).pack(side="left", padx=4)
        
        ctk.CTkButton(btn_frame, text="حذف این هفته", width=120, height=42, corner_radius=12,
                      font=(self.font, 13), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=delete_week_schedule).pack(side="left", padx=4)
        
        ctk.CTkButton(btn_frame, text="بستن", width=120, height=42, corner_radius=12,
                      font=(self.font, 15), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=week_win.destroy).pack(side="left", padx=4)

    def _open_course_manager(self, parent_window) -> None:
        """باز کردن پنجره مدیریت دوره‌های سفارشی."""
        course_win = ctk.CTkToplevel(self)
        course_win.title("مدیریت دوره‌ها")
        course_win.geometry("650x600")
        course_win.resizable(False, False)
        course_win.configure(fg_color=self.theme["bg"])
        course_win.transient(self)
        course_win.grab_set()

        t = self.theme
        
        # عنوان
        ctk.CTkLabel(course_win, text="مدیریت دوره‌های سفارشی", font=(self.font, 18, "bold"),
                     text_color=t["text"]).pack(padx=24, pady=(18, 12))
        
        # لیست دوره‌های موجود
        courses_frame = ctk.CTkFrame(course_win, fg_color=t["panel"], corner_radius=8)
        courses_frame.pack(fill="both", expand=True, padx=24, pady=8)
        
        # اسکرول برای لیست دوره‌ها
        courses_canvas = tk.Canvas(courses_frame, bg=t["panel"], highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(courses_frame, orientation="vertical", command=courses_canvas.yview)
        scrollable_frame = ctk.CTkFrame(courses_canvas, fg_color="transparent")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: courses_canvas.configure(scrollregion=courses_canvas.bbox("all"))
        )
        
        courses_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        courses_canvas.configure(yscrollcommand=scrollbar.set)
        
        courses_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def refresh_courses_list():
            """بازسازی لیست دوره‌ها."""
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            # دوره‌های استاندارد
            ctk.CTkLabel(scrollable_frame, text="دوره‌های استاندارد", font=(self.font, 14, "bold"),
                         text_color=t["accent"]).pack(anchor="w", padx=12, pady=(8, 4))
            
            for course_id, default_name in config.COURSE_NAMES.items():
                # استفاده از نام سفارشی اگر وجود دارد
                display_name = config.get_course_name(str(course_id))
                course_item = ctk.CTkFrame(scrollable_frame, fg_color=t["card"], corner_radius=6)
                course_item.pack(fill="x", padx=8, pady=2)
                ctk.CTkLabel(course_item, text=f"دوره {course_id}: {display_name}", font=(self.font, 12),
                           text_color=t["text"]).pack(side="left", padx=8, pady=6)
            
            # دوره‌های سفارشی
            custom_courses = config.get_all_custom_courses()
            if custom_courses:
                ctk.CTkLabel(scrollable_frame, text="دوره‌های سفارشی", font=(self.font, 14, "bold"),
                           text_color=t["accent"]).pack(anchor="w", padx=12, pady=(12, 4))
                
                for course_id, course_info in custom_courses.items():
                    course_item = ctk.CTkFrame(scrollable_frame, fg_color=t["card"], corner_radius=6)
                    course_item.pack(fill="x", padx=8, pady=2)
                    ctk.CTkLabel(course_item, text=f"{course_id}: {course_info['name']}", 
                               font=(self.font, 12), text_color=t["text"]).pack(side="left", padx=8, pady=6)
                    
                    # دکمه حذف
                    delete_btn = ctk.CTkButton(course_item, text="حذف", width=50, height=24,
                                             corner_radius=6, font=(self.font, 10),
                                             fg_color=t["accent"], hover_color=t["accent_hover"],
                                             text_color=t["chip_text"],
                                             command=lambda cid=course_id: delete_course(cid))
                    delete_btn.pack(side="right", padx=4, pady=6)
            else:
                ctk.CTkLabel(scrollable_frame, text="دوره سفارشی وجود ندارد", font=(self.font, 12),
                           text_color=t["subtext"]).pack(anchor="w", padx=12, pady=(12, 4))
        
        def delete_course(course_id: str) -> None:
            """حذف دوره سفارشی."""
            if config.delete_custom_course(course_id):
                refresh_courses_list()
                self.logger.info(f"دوره {course_id} حذف شد")
        
        # فرم افزودن دوره جدید
        add_frame = ctk.CTkFrame(course_win, fg_color=t["panel"], corner_radius=8)
        add_frame.pack(fill="x", padx=24, pady=8)
        
        ctk.CTkLabel(add_frame, text="افزودن دوره جدید", font=(self.font, 14, "bold"),
                     text_color=t["text"]).pack(anchor="w", padx=12, pady=(8, 4))
        
        # ID دوره
        id_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        id_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(id_frame, text="شناسه دوره:", font=(self.font, 12),
                     text_color=t["text"]).pack(side="left")
        id_entry = ctk.CTkEntry(id_frame, width=150, placeholder_text="مثلاً: python_web",
                                font=(self.font, 12))
        id_entry.pack(side="right")
        
        # نام دوره
        name_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        name_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(name_frame, text="نام دوره:", font=(self.font, 12),
                     text_color=t["text"]).pack(side="left")
        name_entry = ctk.CTkEntry(name_frame, width=250, placeholder_text="مثلاً: توسعه وب با پایتون",
                                 font=(self.font, 12))
        name_entry.pack(side="right")
        
        # زمان بخش‌ها
        times_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        times_frame.pack(fill="x", padx=12, pady=2)
        
        ctk.CTkLabel(times_frame, text="زمان‌ها (دقیقه):", font=(self.font, 12),
                     text_color=t["text"]).pack(side="left")
        
        video_entry = ctk.CTkEntry(times_frame, width=60, placeholder_text="ویدیو",
                                  font=(self.font, 12))
        video_entry.insert(0, "40")
        video_entry.pack(side="right", padx=2)
        
        practice_entry = ctk.CTkEntry(times_frame, width=60, placeholder_text="تمرین",
                                     font=(self.font, 12))
        practice_entry.insert(0, "40")
        practice_entry.pack(side="right", padx=2)
        
        debug_entry = ctk.CTkEntry(times_frame, width=60, placeholder_text="رفع اشکال",
                                   font=(self.font, 12))
        debug_entry.insert(0, "40")
        debug_entry.pack(side="right", padx=2)
        
        # انتخاب تم
        theme_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(theme_frame, text="تم رنگی:", font=(self.font, 12),
                     text_color=t["text"]).pack(side="left")
        
        theme_options = ["course1", "course2", "course3", "course4", "custom1", "custom2", "custom3"]
        theme_names = {
            "course1": "آبی", "course2": "سبز", "course3": "نارنجی", "course4": "بنفش",
            "custom1": "صورتی", "custom2": "صورتی دودی", "custom3": "قهوه‌ای"
        }
        theme_var = tk.StringVar(value="custom1")
        theme_menu = ctk.CTkOptionMenu(theme_frame, values=list(theme_names.values()),
                                      variable=theme_var, font=(self.font, 12),
                                      fg_color=t["accent_soft"], button_color=t["accent"],
                                      button_hover_color=t["accent_hover"],
                                      dropdown_fg_color=t["panel"],
                                      dropdown_text_color=t["text"],
                                      text_color=t["text"])
        theme_menu.pack(side="right")
        
        def add_course() -> None:
            """افزودن دوره جدید."""
            try:
                course_id = id_entry.get().strip()
                name = name_entry.get().strip()
                video_min = int(video_entry.get())
                practice_min = int(practice_entry.get())
                debug_min = int(debug_entry.get())
                
                theme_name = theme_var.get()
                theme_key = None
                for key, name in theme_names.items():
                    if name == theme_name:
                        theme_key = key
                        break
                
                if not course_id or not name:
                    return
                
                # اعتبارسنجی زمان‌ها
                video_min = max(1, min(180, video_min))
                practice_min = max(1, min(180, practice_min))
                debug_min = max(1, min(180, debug_min))
                
                config.add_custom_course(course_id, name, video_min, practice_min, debug_min, theme_key)
                refresh_courses_list()
                
                # پاک کردن فرم
                id_entry.delete(0, tk.END)
                name_entry.delete(0, tk.END)
                
                self.logger.info(f"دوره جدید اضافه شد: {course_id}")
                
            except ValueError:
                pass
        
        ctk.CTkButton(add_frame, text="افزودن دوره", width=120, height=32, corner_radius=8,
                      font=(self.font, 12, "bold"), fg_color=t["accent"],
                      hover_color=t["accent_hover"], text_color=t["chip_text"],
                      command=add_course).pack(pady=8)
        
        # دکمه‌های پایین
        btn_frame = ctk.CTkFrame(course_win, fg_color="transparent")
        btn_frame.pack(pady=12)
        
        ctk.CTkButton(btn_frame, text="بستن", width=120, height=42, corner_radius=12,
                      font=(self.font, 15), fg_color=t["panel"],
                      border_width=2, border_color=t["card_border"],
                      hover_color=t["accent_soft"], text_color=t["text"],
                      command=course_win.destroy).pack(side="left", padx=4)
        
        # بارگذاری اولیه لیست
        refresh_courses_list()
