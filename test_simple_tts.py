# -*- coding: utf-8 -*-
"""
Simple test of Edge TTS playback
"""
import sys
import io

# Set console encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import edge_tts
import asyncio
import os
import tempfile

async def test_simple_tts():
    try:
        print("Testing simple Edge TTS...")
        text = "جلسه شروع شد؛ موفق باشی!"
        
        voice = 'fa-IR-DilaraNeural'
        communicate = edge_tts.Communicate(text, voice)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_path = temp_file.name
        
        print(f"Generating audio for: {text}")
        await communicate.save(temp_path)
        print(f"Audio saved to: {temp_path}")
        
        # Try different playback methods
        print("\nTrying os.startfile...")
        os.startfile(temp_path)
        
        print("Audio should be playing now...")
        print(f"File size: {os.path.getsize(temp_path)} bytes")
        
        # Keep the file for manual inspection
        print(f"\nFile location: {temp_path}")
        print("File will be kept for manual inspection.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_tts())