# -*- coding: utf-8 -*-
"""
Test integrated voice system with Edge TTS
"""
from voice import VoiceNotifier
import config

def test_voice_notifier():
    try:
        print("Testing VoiceNotifier with Edge TTS...")
        
        # Create voice notifier with TTS mode
        voice = VoiceNotifier(mode="tts", volume=1.0)
        
        print(f"Voice mode: {voice.mode}")
        print(f"Edge TTS available: {voice._edge_tts_available}")
        
        # Test different notification types
        print("\n[1] Testing session start notification...")
        voice.notify("session_start")
        
        import time
        time.sleep(3)  # Wait for TTS to play
        
        print("\n[2] Testing block end notification...")
        voice.notify("block_end", done="تماشای ویدیو آموزشی 🎥", nxt="تمرین عملی و کدنویسی 💻")
        
        time.sleep(5)  # Wait for TTS to play
        
        print("\n[3] Testing session complete notification...")
        voice.notify("session_complete")
        
        time.sleep(4)  # Wait for TTS to play
        
        print("\n[4] Testing session rest notification...")
        voice.notify("session_rest")
        
        time.sleep(3)  # Wait for TTS to play
        
        print("\nVoice integration test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_voice_notifier()