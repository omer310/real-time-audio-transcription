import asyncio
import sounddevice as sd
import numpy as np
import threading
import queue
import sys

class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_size=1024, device_index=None):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.capture_mode = "microphone"
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.device_index = device_index  # User-specified device index

    def set_capture_mode(self, mode):
        self.capture_mode = mode.lower()

    def _audio_callback(self, indata, frames, time, status):
        """Callback function for sounddevice stream"""
        if self.is_recording and status.input_underflow == False:
            # Convert to int16 and put in queue
            audio_data = (indata * 32767).astype(np.int16)
            if audio_data.ndim > 1:
                # Convert stereo to mono
                audio_data = np.mean(audio_data, axis=1).astype(np.int16)
            self.audio_queue.put(audio_data.tobytes())
    
    def _find_loopback_device(self):
        """Find a device that can capture system audio"""
        devices = sd.query_devices()
        
        # Look for WASAPI loopback devices first
        for i, device in enumerate(devices):
            if (device['max_input_channels'] > 0 and 
                'WASAPI' in device['name'] and 
                'loopback' in device['name'].lower()):
                return i
        
        # Look for stereo mix or similar
        for i, device in enumerate(devices):
            device_name = device['name'].lower()
            if (device['max_input_channels'] > 0 and 
                ('stereo mix' in device_name or 
                 'what u hear' in device_name or 
                 'wave out mix' in device_name)):
                return i
        
        return None
    
    def list_audio_devices(self):
        """List all available audio devices for debugging"""
        print("Available audio devices:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"  {i}: {device['name']} (inputs: {device['max_input_channels']})")
        return devices
    
    @staticmethod
    def get_all_input_devices():
        """Get all available input (microphone) devices"""
        devices = []
        all_devices = sd.query_devices()
        for i, device in enumerate(all_devices):
            if device['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': device['name']
                })
        return devices

    async def capture_and_send_audio_to_whisper(self, whisper_client):
        """Capture audio and send to Whisper client for processing"""
        self.is_recording = True
        buffer = b""
        
        try:
            # List available devices for debugging
            self.list_audio_devices()
            
            # Determine input device based on capture mode
            device = None
            channels = 1
            
            if self.capture_mode == "computer audio":
                device = self._find_loopback_device()
                if device is None:
                    print("\nWarning: Could not find system audio loopback device.")
                    print("To capture computer audio on Windows:")
                    print("1. Right-click on speaker icon in system tray")
                    print("2. Select 'Open Sound settings'")
                    print("3. Go to 'Sound Control Panel' -> Recording tab")
                    print("4. Right-click and 'Show Disabled Devices'")
                    print("5. Enable 'Stereo Mix' if available")
                    print("6. Or try using 'Microphone' mode and play audio through speakers")
                    print("\nFalling back to default microphone...")
                else:
                    device_info = sd.query_devices(device)
                    channels = min(2, device_info['max_input_channels'])
                    print(f"\nUsing system audio device: {device_info['name']}")
            
            elif self.capture_mode == "microphone":
                # Use user-specified device or system default
                device = self.device_index  # None means use system default
                if device is not None:
                    device_info = sd.query_devices(device)
                    print(f"\nUsing microphone device: {device_info['name']}")
                else:
                    print(f"\nUsing system default microphone")
            
            elif self.capture_mode == "both":
                print("\nBoth mode not fully implemented yet, using microphone")
            
            # Start audio stream
            self.stream = sd.InputStream(
                device=device,
                channels=channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            self.stream.start()
            print(f"Audio stream started - Mode: {self.capture_mode}, Device: {device}, Channels: {channels}")
            
            # sounddevice.InputStream uses .active property, not .is_active() method
            while whisper_client.is_active and self.stream.active:
                try:
                    # Get audio data from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get_nowait()
                        buffer += audio_data
                        
                        # Send buffer more frequently (every 1 second) for better responsiveness
                        # This ensures audio is continuously sent without long gaps
                        if len(buffer) >= self.sample_rate * 1 * 2:  # 1 second * 2 bytes per sample
                            await whisper_client.send_audio(buffer)
                            buffer = b""
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as record_error:
                    print(f"Error processing audio: {record_error}")
                    await asyncio.sleep(0.1)
                    continue
            
            # Send any remaining buffer
            if len(buffer) > 0:
                await whisper_client.send_audio(buffer)
            
            self.stream.stop()
            self.stream.close()
            
        except Exception as e:
            print(f"Error in capture_and_send_audio_to_whisper: {e}")
            raise
        finally:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass

    async def capture_and_send_audio_to_deepgram(self, deepgram_client):
        """Capture audio and send to Deepgram client for processing"""
        self.is_recording = True
        buffer = b""
        
        try:
            # List available devices for debugging
            self.list_audio_devices()
            
            # Determine input device based on capture mode
            device = None
            channels = 1
            
            if self.capture_mode == "computer audio":
                device = self._find_loopback_device()
                if device is None:
                    print("\nWarning: Could not find system audio loopback device.")
                    print("To capture computer audio on Windows:")
                    print("1. Right-click on speaker icon in system tray")
                    print("2. Select 'Open Sound settings'")
                    print("3. Go to 'Sound Control Panel' -> Recording tab")
                    print("4. Right-click and 'Show Disabled Devices'")
                    print("5. Enable 'Stereo Mix' if available")
                    print("6. Or try using 'Microphone' mode and play audio through speakers")
                    print("\nFalling back to default microphone...")
                else:
                    device_info = sd.query_devices(device)
                    channels = min(2, device_info['max_input_channels'])
                    print(f"\nUsing system audio device: {device_info['name']}")
            
            elif self.capture_mode == "microphone":
                # Use user-specified device or system default
                device = self.device_index  # None means use system default
                if device is not None:
                    device_info = sd.query_devices(device)
                    print(f"\nUsing microphone device: {device_info['name']}")
                else:
                    print(f"\nUsing system default microphone")
            
            elif self.capture_mode == "both":
                print("\nBoth mode not fully implemented yet, using microphone")
            
            # Start audio stream
            self.stream = sd.InputStream(
                device=device,
                channels=channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            self.stream.start()
            print(f"Audio stream started - Mode: {self.capture_mode}, Device: {device}, Channels: {channels}")
            
            # sounddevice.InputStream uses .active property, not .is_active() method
            while deepgram_client.is_active and self.stream.active:
                try:
                    # Get audio data from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get_nowait()
                        buffer += audio_data
                        
                        # Send buffer more frequently (every 1 second) for better responsiveness
                        # This ensures audio is continuously sent without long gaps
                        if len(buffer) >= self.sample_rate * 1 * 2:  # 1 second * 2 bytes per sample
                            await deepgram_client.send_audio(buffer)
                            buffer = b""
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as record_error:
                    print(f"Error processing audio: {record_error}")
                    await asyncio.sleep(0.1)
                    continue
            
            # Send any remaining buffer
            if len(buffer) > 0:
                await deepgram_client.send_audio(buffer)
            
            self.stream.stop()
            self.stream.close()
            
        except Exception as e:
            print(f"Error in capture_and_send_audio_to_deepgram: {e}")
            raise
        finally:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except:
                    pass

    async def capture_and_send_audio(self, websocket):
        buffer_mic = b""
        buffer_speaker = b""
        try:
            if self.capture_function == self.capture_both:
                mic, speaker = self.capture_function()
                with mic, speaker:
                    while True:
                        mic_data = mic.record(numframes=self.chunk_size)
                        speaker_data = speaker.record(numframes=self.chunk_size)
                        
                        # Process microphone data
                        mic_data = mic_data.mean(axis=1)  # Convert stereo to mono
                        mic_data = (mic_data * 32767).astype(np.int16).tobytes()
                        buffer_mic += mic_data
                        
                        # Process speaker data
                        speaker_data = speaker_data.mean(axis=1)  # Convert stereo to mono
                        speaker_data = (speaker_data * 32767).astype(np.int16).tobytes()
                        buffer_speaker += speaker_data
                        
                        if len(buffer_mic) >= self.chunk_size * 2:
                            await websocket.send(b"mic:" + buffer_mic)
                            buffer_mic = b""
                        
                        if len(buffer_speaker) >= self.chunk_size * 2:
                            await websocket.send(b"speaker:" + buffer_speaker)
                            buffer_speaker = b""
                        
                        await asyncio.sleep(0.01)
            else:
                buffer = b""
                with self.capture_function() as mic:
                    while True:
                        data = mic.record(numframes=self.chunk_size)
                        data = data.mean(axis=1)  # Convert stereo to mono
                        data = (data * 32767).astype(np.int16).tobytes()
                        
                        buffer += data
                        if len(buffer) >= self.chunk_size * 2:
                            await websocket.send(buffer)
                            buffer = b""
                        
                        await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in capture_and_send_audio: {e}")
            raise