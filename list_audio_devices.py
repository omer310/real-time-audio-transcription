#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List all available audio devices for system audio and microphone capture"""

from modules.windows_audio_capture import WindowsAudioCapture

print("\n" + "="*70)
print("AUDIO DEVICE SELECTION HELPER")
print("="*70)

print("\n[MICROPHONE DEVICES]")
print("-" * 70)
mics = WindowsAudioCapture.get_all_input_devices()
if mics:
    for device in mics:
        print(f"  ID {device['index']:2d} | {device['name']}")
else:
    print("  No microphone devices found!")

print("\n[LOOPBACK DEVICES - FOR SYSTEM AUDIO CAPTURE]")
print("-" * 70)
loopbacks = WindowsAudioCapture.get_all_loopback_devices()
if loopbacks:
    for device in loopbacks:
        print(f"  ID {device['index']:2d} | {device['name']}")
else:
    print("  No loopback devices found!")
    print("  To capture system audio, enable Stereo Mix or NVIDIA Broadcast")

print("\n" + "="*70)
print("INSTRUCTIONS:")
print("="*70)
print("""
1. If the app is capturing from the WRONG MICROPHONE:
   - Note the ID of the microphone you want to use
   - Edit Live.py and find the run_transcription() method
   - Change: audio_capture = AudioCapture()
   - To: audio_capture = AudioCapture(device_index=YOUR_MIC_ID)
   - Example: audio_capture = AudioCapture(device_index=30)

2. If the app is capturing from the WRONG LOOPBACK DEVICE (system audio):
   - Note the ID of the loopback device for your PRIMARY SPEAKERS
   - Edit Live.py and find the run_transcription() method
   - Change: audio_capture = WindowsAudioCapture(sample_rate=16000)
   - To: audio_capture = WindowsAudioCapture(sample_rate=16000, loopback_index=YOUR_ID)
   - Example: audio_capture = WindowsAudioCapture(sample_rate=16000, loopback_index=34)

3. Save and restart the app with your chosen device!
""")
print("="*70 + "\n")


