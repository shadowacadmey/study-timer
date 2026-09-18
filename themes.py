# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════
  themes.py — پالت‌های رنگی لوکسِ اختصاصی هر دوره / هر روز
═══════════════════════════════════════════════════════════════════════
  با تغییر روزِ هفته، کل داشبورد با یکی از این پالت‌ها رنگ‌آمیزی می‌شود:

    • دورهٔ ۱ (شنبه)      : آبی کهکشانی
    • دورهٔ ۲ (یکشنبه)    : سبز مدرن
    • دورهٔ ۳ (دوشنبه)    : کهربایی/طلایی
    • دورهٔ ۴ (سه‌شنبه)   : بنفش نئونی
    • مرور هفتگی (چهارشنبه) : فیروزه‌ای
    • پروژهٔ عملی (پنجشنبه) : سرخ آتشی
    • استراحت مطلق (جمعه)  : بنفش ملایم رویایی
"""

from __future__ import annotations


def _theme(name_fa: str, **colors) -> dict:
    required = {
        "bg": "#000000", "panel": "#111111", "card": "#161616",
        "card_border": "#2a2a2a", "accent": "#ffffff",
        "accent_hover": "#dddddd", "accent_soft": "#222222",
        "progress_bg": "#1c1c1c", "success": "#34d399",
        "text": "#ffffff", "subtext": "#9ca3af", "chip_text": "#ffffff",
        "glow": "#ffffff", "grad_top": "#0b0620", "grad_bottom": "#251345",
        "stars": ["#c4b5fd", "#e9d5ff", "#fde68a", "#93c5fd", "#f0abfc"],
    }
    required.update(colors)
    required["name_fa"] = name_fa
    return required


THEMES = {
    # ─────────────────────────── دورهٔ ۱: آبی حرفه‌ای ───────────────────────────
    "course1": _theme(
        "آبی حرفه‌ای",
        bg="#0F172A", panel="#1E293B", card="#334155", card_border="#475569",
        accent="#3B82F6", accent_hover="#2563EB", accent_soft="#1E3A8A",
        progress_bg="#1E293B", text="#F8FAFC", subtext="#94A3B8",
        chip_text="#FFFFFF", glow="#60A5FA",
        grad_top="#0F172A", grad_bottom="#1E293B",
        stars=["#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE", "#DBEAFE"],
    ),
    # ─────────────────────────── دورهٔ ۲: سبز لوکس ───────────────────────────
    "course2": _theme(
        "سبز لوکس",
        bg="#064E3B", panel="#065F46", card="#047857", card_border="#059669",
        accent="#10B981", accent_hover="#059669", accent_soft="#064E3B",
        progress_bg="#065F46", text="#ECFDF5", subtext="#6EE7B7",
        chip_text="#FFFFFF", glow="#34D399",
        grad_top="#064E3B", grad_bottom="#065F46",
        stars=["#10B981", "#34D399", "#6EE7B7", "#A7F3D0", "#D1FAE5"],
    ),
    # ─────────────────────────── دورهٔ ۳: طلایی ممتاز ───────────────────────────
    "course3": _theme(
        "طلایی ممتاز",
        bg="#451A03", panel="#78350F", card="#92400E", card_border="#B45309",
        accent="#F59E0B", accent_hover="#D97706", accent_soft="#451A03",
        progress_bg="#78350F", text="#FFFBEB", subtext="#FCD34D",
        chip_text="#FFFFFF", glow="#FBBF24",
        grad_top="#451A03", grad_bottom="#78350F",
        stars=["#F59E0B", "#FBBF24", "#FCD34D", "#FDE68A", "#FEF3C7"],
    ),
    # ─────────────────────────── دورهٔ ۴: بنفش سلطنتی ───────────────────────────
    "course4": _theme(
        "بنفش سلطنتی",
        bg="#581C87", panel="#6B21A8", card="#7C3AED", card_border="#8B5CF6",
        accent="#A78BFA", accent_hover="#8B5CF6", accent_soft="#581C87",
        progress_bg="#6B21A8", text="#FAF5FF", subtext="#C4B5FD",
        chip_text="#FFFFFF", glow="#DDD6FE",
        grad_top="#581C87", grad_bottom="#6B21A8",
        stars=["#A78BFA", "#C4B5FD", "#DDD6FE", "#EDE9FE", "#F5F3FF"],
    ),
    # ─────────────────────────── دورهٔ ۵: فیروزه‌ای اقیانوسی ───────────────────────────
    "course5": _theme(
        "فیروزه‌ای اقیانوسی",
        bg="#0E7490", panel="#155E75", card="#0E7490", card_border="#06B6D4",
        accent="#22D3EE", accent_hover="#06B6D4", accent_soft="#0E7490",
        progress_bg="#155E75", text="#CFFAFE", subtext="#67E8F9",
        chip_text="#FFFFFF", glow="#A5F3FC",
        grad_top="#0E7490", grad_bottom="#155E75",
        stars=["#22D3EE", "#67E8F9", "#A5F3FC", "#CFFAFE", "#ECFEFF"],
    ),
    # ─────────────────────────── دورهٔ ۶: قرمز انرژیک ───────────────────────────
    "course6": _theme(
        "قرمز انرژیک",
        bg="#7F1D1D", panel="#991B1B", card="#B91C1C", card_border="#DC2626",
        accent="#EF4444", accent_hover="#DC2626", accent_soft="#7F1D1D",
        progress_bg="#991B1B", text="#FEF2F2", subtext="#FCA5A5",
        chip_text="#FFFFFF", glow="#F87171",
        grad_top="#7F1D1D", grad_bottom="#991B1B",
        stars=["#EF4444", "#F87171", "#FCA5A5", "#FECACA", "#FEE2E2"],
    ),
    # ─────────────────────────── چهارشنبه: مرور (فیروزه‌ای اقیانوسی) ───────────────────────────
    "review": _theme(
        "فیروزه‌ای اقیانوسی",
        bg="#0E7490", panel="#155E75", card="#0E7490", card_border="#06B6D4",
        accent="#22D3EE", accent_hover="#06B6D4", accent_soft="#0E7490",
        progress_bg="#155E75", text="#CFFAFE", subtext="#67E8F9",
        chip_text="#FFFFFF", glow="#A5F3FC",
        grad_top="#0E7490", grad_bottom="#155E75",
        stars=["#22D3EE", "#67E8F9", "#A5F3FC", "#CFFAFE", "#ECFEFF"],
    ),
    # ─────────────────────────── پنجشنبه: پروژه (قرمز انرژیک) ───────────────────────────
    "project": _theme(
        "قرمز انرژیک",
        bg="#7F1D1D", panel="#991B1B", card="#B91C1C", card_border="#DC2626",
        accent="#EF4444", accent_hover="#DC2626", accent_soft="#7F1D1D",
        progress_bg="#991B1B", text="#FEF2F2", subtext="#FCA5A5",
        chip_text="#FFFFFF", glow="#F87171",
        grad_top="#7F1D1D", grad_bottom="#991B1B",
        stars=["#EF4444", "#F87171", "#FCA5A5", "#FECACA", "#FEE2E2"],
    ),
    # ─────────────────────────── جمعه: استراحت (کرمی آرام) ───────────────────────────
    "rest": _theme(
        "کرمی آرام",
        bg="#292524", panel="#44403C", card="#57534E", card_border="#78716C",
        accent="#A8A29E", accent_hover="#78716C", accent_soft="#292524",
        progress_bg="#44403C", text="#FAFAF9", subtext="#D6D3D1",
        chip_text="#FFFFFF", glow="#E7E5E4",
        grad_top="#292524", grad_bottom="#44403C",
        stars=["#A8A29E", "#D6D3D1", "#E7E5E4", "#FAFAF9", "#F5F5F4"],
    ),
    # ─────────────────────────── دوره‌های سفارشی لوکس ───────────────────────────
    "custom1": _theme(
        "صورتی نئون",
        bg="#831843", panel="#9D174D", card="#BE185D", card_border="#DB2777",
        accent="#EC4899", accent_hover="#DB2777", accent_soft="#831843",
        progress_bg="#9D174D", text="#FDF2F8", subtext="#F472B6",
        chip_text="#FFFFFF", glow="#F9A8D4",
        grad_top="#831843", grad_bottom="#9D174D",
        stars=["#EC4899", "#F472B6", "#F9A8D4", "#FBCFE8", "#FCE7F3"],
    ),
    "custom2": _theme(
        "بنفش عمیق",
        bg="#4C1D95", panel="#5B21B6", card="#6D28D9", card_border="#7C3AED",
        accent="#8B5CF6", accent_hover="#7C3AED", accent_soft="#4C1D95",
        progress_bg="#5B21B6", text="#F5F3FF", subtext="#C4B5FD",
        chip_text="#FFFFFF", glow="#DDD6FE",
        grad_top="#4C1D95", grad_bottom="#5B21B6",
        stars=["#8B5CF6", "#A78BFA", "#C4B5FD", "#DDD6FE", "#EDE9FE"],
    ),
    "custom3": _theme(
        "سرمه‌ای مدرن",
        bg="#1E1B4B", panel="#312E81", card="#4338CA", card_border="#4F46E5",
        accent="#6366F1", accent_hover="#4F46E5", accent_soft="#1E1B4B",
        progress_bg="#312E81", text="#EEF2FF", subtext="#A5B4FC",
        chip_text="#FFFFFF", glow="#C7D2FE",
        grad_top="#1E1B4B", grad_bottom="#312E81",
        stars=["#6366F1", "#818CF8", "#A5B4FC", "#C7D2FE", "#E0E7FF"],
    ),
}
