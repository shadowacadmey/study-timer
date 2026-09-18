# -*- coding: utf-8 -*-
"""
Simple voice test for debugging
"""
import pyttsx3
import sys

try:
    print("Initializing voice engine...")
    engine = pyttsx3.init()
    
    print("Available voices:")
    voices = engine.getProperty("voices")
    for i, voice in enumerate(voices):
        print(f"  {i}: {voice.name} ({voice.id})")
    
    if voices:
        print(f"\nSelecting first voice: {voices[0].name}")
        engine.setProperty("voice", voices[0].id)
    
    print("Setting rate and volume...")
    engine.setProperty("rate", 165)
    engine.setProperty("volume", 1.0)
    
    print("Playing voice test...")
    engine.say("Hello, this is a test.")
    engine.runAndWait()
    
    print("Voice test completed successfully!")
    
except Exception as e:
    print(f"Error in voice test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
