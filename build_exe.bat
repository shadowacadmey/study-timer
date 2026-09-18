@echo off
rem ──────────────────────────────────────────────────────────────
rem  ساخت فایل اجرایی مستقل ویندوز (بدون پنجرهٔ CMD)
rem  خروجی: dist\StudyTimerPro.exe
rem ──────────────────────────────────────────────────────────────
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "StudyTimerPro" ^
    --add-data "sounds;sounds" main.py
echo.
echo  فایل نهایی: dist\StudyTimerPro.exe
pause
