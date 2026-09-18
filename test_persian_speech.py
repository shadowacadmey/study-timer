# -*- coding: utf-8 -*-
"""
Test Persian TTS using persian-speech library
"""
from persian_speech_runtime import talk
import tempfile
import os

try:
    print("Testing Persian TTS...")
    text = "سلام، این یک تست است."
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        temp_path = temp_file.name
    
    print(f"Generating speech for: {text}")
    talk(text, temp_path)
    print(f"Audio saved to: {temp_path}")
    
    # Play the file
    if os.name == 'nt':
        print("Playing audio...")
        os.startfile(temp_path)
    
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()