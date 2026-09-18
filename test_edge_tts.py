# -*- coding: utf-8 -*-
"""
Test Edge TTS for Persian
"""
import edge_tts
import tempfile
import os
import asyncio
import sys

# Set console encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_persian_edge_tts():
    try:
        print("Testing Edge TTS for Persian...")
        text = "سلام، این یک تست است."
        
        # Persian voice - using Microsoft Dilara (Persian female voice)
        voice = 'fa-IR-DilaraNeural'
        
        print(f"Generating speech for: {text}")
        print(f"Using voice: {voice}")
        
        communicate = edge_tts.Communicate(text, voice)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
        
        await communicate.save(temp_path)
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

if __name__ == "__main__":
    asyncio.run(test_persian_edge_tts())