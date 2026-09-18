# -*- coding: utf-8 -*-
"""
Check available voices and look for Persian
"""
import pyttsx3

try:
    print("Initializing voice engine...")
    engine = pyttsx3.init()
    
    print("Available voices:")
    voices = engine.getProperty("voices")
    for i, voice in enumerate(voices):
        print(f"  {i}: {voice.name}")
        print(f"      ID: {voice.id}")
        print(f"      Languages: {getattr(voice, 'languages', 'N/A')}")
        print()
    
    # Check for Persian voices
    print("Searching for Persian voices...")
    persian_found = False
    for i, voice in enumerate(voices):
        voice_id = (voice.id or "").lower()
        voice_name = (voice.name or "").lower()
        if "fa" in voice_id or "persian" in voice_id or "persian" in voice_name or "farsi" in voice_name:
            print(f"Found Persian voice: {voice.name} ({voice.id})")
            persian_found = True
    
    if not persian_found:
        print("No Persian voice found.")
        print("You need to install a Persian TTS voice for Windows.")
        print("You can download one from:")
        print("  - Microsoft Store: Search for 'Persian voice'")
        print("  - Or try: https://www.microsoft.com/en-us/download/details.aspx?id=39711")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
