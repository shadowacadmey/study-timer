# -*- coding: utf-8 -*-
"""
Test Google TTS for Persian
"""
from gtts import gTTS
import tempfile
import os

try:
    print("Testing Google TTS for Persian...")
    text = "سلام، این یک تست است."
    
    tts = gTTS(text=text, lang='fa', slow=False)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        temp_path = temp_file.name
    
    tts.save(temp_path)
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
    
