# -*- coding: utf-8 -*-
"""
Check supported languages in gtts
"""
from gtts import gTTS
import gtts.lang

try:
    print("Checking supported languages in gtts...")
    langs = gtts.lang.tts_langs()
    
    print("Total languages:", len(langs))
    print("\nSearching for Persian/Farsi...")
    
    persian_found = False
    for code, name in langs.items():
        if 'persian' in name.lower() or 'farsi' in name.lower() or 'iran' in name.lower():
            print(f"Found: {code} - {name}")
            persian_found = True
    
    if not persian_found:
        print("No Persian/Farsi language found.")
        print("\nSearching for similar languages...")
        for code, name in langs.items():
            if 'arabic' in name.lower() or 'urdu' in name.lower():
                print(f"Found: {code} - {name}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
