import asyncio
import numpy as np
import queue
import pyaudiowpatch as pyaudio

class WindowsAudioCapture:
    def __init__(self, sample_rate=16000, chunk_size=1024, device_index=None, microphone_index=None):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.stream = None
        self.device_index = device_index  # Output/loopback device index
        self.microphone_index = microphone_index  # Microphone device index (for Both mode)
        
        # For "Both" mode - separate queues and streams
        self.mic_queue = queue.Queue()
        self.loopback_queue = queue.Queue()
        self.mic_stream = None
        self.loopback_stream = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for PyAudio stream"""
        if self.is_recording:
            self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def _mic_callback(self, in_data, frame_count, time_info, status):
        """Callback function for microphone stream (Both mode)"""
        if self.is_recording:
            self.mic_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def _loopback_callback(self, in_data, frame_count, time_info, status):
        """Callback function for loopback stream (Both mode)"""
        if self.is_recording:
            self.loopback_queue.put(in_data)
        return (None, pyaudio.paContinue)
    
    def _find_loopback_device(self):
        """Find WASAPI loopback device (defaults to system default speaker loopback)"""
        # If user specified a device, use that
        if self.device_index is not None:
            return self.device_index
            
        try:
            # Get default WASAPI info
            wasapi_info = self.audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            
            # First try to find the default speaker's loopback
            default_speakers = self.audio.get_default_output_device_info()
            default_name = default_speakers.get('name', '')
            
            # Look for the loopback version of the default speakers
            for i in range(wasapi_info["deviceCount"]):
                device_info = self.audio.get_device_info_by_host_api_device_index(
                    wasapi_info["index"], i
                )
                
                if (device_info.get("maxInputChannels") > 0 and 
                    "[Loopback]" in device_info.get("name", "")):
                    # Check if this is the loopback of the default speakers
                    if default_name.split('(')[0].strip() in device_info.get("name", ""):
                        print(f"Found default system loopback device: {device_info['name']}")
                        return device_info["index"]
            
            # If no match for default, return any loopback device
            for i in range(wasapi_info["deviceCount"]):
                device_info = self.audio.get_device_info_by_host_api_device_index(
                    wasapi_info["index"], i
                )
                
                if (device_info.get("maxInputChannels") > 0 and 
                    "[Loopback]" in device_info.get("name", "")):
                    print(f"Found loopback device: {device_info['name']}")
                    return device_info["index"]
            
            return None
        except Exception as e:
            print(f"Error finding loopback device: {e}")
            return None
    
    @staticmethod
    def get_all_output_devices():
        """Get all available output (loopback) devices"""
        audio = pyaudio.PyAudio()
        devices = []
        try:
            wasapi_info = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            for i in range(wasapi_info["deviceCount"]):
                device_info = audio.get_device_info_by_host_api_device_index(
                    wasapi_info["index"], i
                )
                if (device_info.get("maxInputChannels") > 0 and 
                    "[Loopback]" in device_info.get("name", "")):
                    devices.append({
                        'index': device_info['index'],
                        'name': device_info['name']
                    })
        except Exception as e:
            print(f"Error getting output devices: {e}")
        finally:
            audio.terminate()
        return devices
    
    @staticmethod
    def get_all_input_devices():
        """Get all available input (microphone) devices"""
        audio = pyaudio.PyAudio()
        devices = []
        try:
            for i in range(audio.get_device_count()):
                device_info = audio.get_device_info_by_index(i)
                if (device_info.get("maxInputChannels") > 0 and 
                    "[Loopback]" not in device_info.get("name", "")):
                    devices.append({
                        'index': device_info['index'],
                        'name': device_info['name']
                    })
        except Exception as e:
            print(f"Error getting input devices: {e}")
        finally:
            audio.terminate()
        return devices
    
    def list_wasapi_devices(self):
        """List all WASAPI devices for debugging"""
        try:
            wasapi_info = self.audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            print(f"WASAPI devices:")
            
            for i in range(wasapi_info["deviceCount"]):
                device_info = self.audio.get_device_info_by_host_api_device_index(
                    wasapi_info["index"], i
                )
                print(f"  {device_info['index']}: {device_info['name']} "
                      f"(in: {device_info['maxInputChannels']}, "
                      f"out: {device_info['maxOutputChannels']})")
        except Exception as e:
            print(f"Error listing WASAPI devices: {e}")
    
    async def capture_and_send_audio_to_whisper(self, whisper_client):
        """Capture system audio using WASAPI loopback and send to Whisper"""
        self.is_recording = True
        buffer = b""
        
        try:
            # List available devices for debugging
            self.list_wasapi_devices()
            
            # Find loopback device
            loopback_device = self._find_loopback_device()
            
            if loopback_device is None:
                print("No WASAPI loopback device found!")
                print("Make sure your audio drivers support WASAPI loopback.")
                return
            
            # Get device info to check supported sample rate
            device_info = self.audio.get_device_info_by_index(loopback_device)
            device_sample_rate = int(device_info['defaultSampleRate'])
            channels = int(device_info['maxInputChannels'])
            
            print(f"Device sample rate: {device_sample_rate}, channels: {channels}")
            
            # Use device's native sample rate
            actual_sample_rate = device_sample_rate
            
            # Open audio stream with loopback device
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=actual_sample_rate,
                input=True,
                input_device_index=loopback_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            print(f"Started WASAPI loopback capture on device {loopback_device}")
            
            while whisper_client.is_active and self.stream.is_active():
                try:
                    # Get audio data from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get_nowait()
                        
                        # Convert to numpy array
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        
                        # Convert stereo to mono if needed
                        if channels > 1 and len(audio_array) % channels == 0:
                            audio_array = audio_array.reshape(-1, channels)
                            audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                        
                        # Resample to 16kHz if needed (simple resampling)
                        if actual_sample_rate != self.sample_rate:
                            # Simple resampling
                            ratio = self.sample_rate / actual_sample_rate
                            new_length = int(len(audio_array) * ratio)
                            if new_length > 0:
                                audio_array = np.interp(
                                    np.linspace(0, len(audio_array), new_length),
                                    np.arange(len(audio_array)),
                                    audio_array
                                ).astype(np.int16)
                        
                        audio_data = audio_array.tobytes()
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
            
            self.stream.stop_stream()
            self.stream.close()
            
        except Exception as e:
            print(f"Error in Windows audio capture: {e}")
            raise
        finally:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
    
    async def capture_and_send_audio_to_deepgram(self, deepgram_client):
        """Capture system audio using WASAPI loopback and send to Deepgram"""
        self.is_recording = True
        buffer = b""
        
        try:
            # List available devices for debugging
            self.list_wasapi_devices()
            
            # Find loopback device
            loopback_device = self._find_loopback_device()
            
            if loopback_device is None:
                print("No WASAPI loopback device found!")
                print("Make sure your audio drivers support WASAPI loopback.")
                return
            
            # Get device info to check supported sample rate
            device_info = self.audio.get_device_info_by_index(loopback_device)
            device_sample_rate = int(device_info['defaultSampleRate'])
            channels = int(device_info['maxInputChannels'])
            
            print(f"Device sample rate: {device_sample_rate}, channels: {channels}")
            
            # Use device's native sample rate
            actual_sample_rate = device_sample_rate
            
            # Open audio stream with loopback device
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=actual_sample_rate,
                input=True,
                input_device_index=loopback_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            print(f"Started WASAPI loopback capture on device {loopback_device}")
            
            while deepgram_client.is_active and self.stream.is_active():
                try:
                    # Get audio data from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get_nowait()
                        
                        # Convert to numpy array
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        
                        # Convert stereo to mono if needed
                        if channels > 1 and len(audio_array) % channels == 0:
                            audio_array = audio_array.reshape(-1, channels)
                            audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                        
                        # Resample to 16kHz if needed (simple resampling)
                        if actual_sample_rate != self.sample_rate:
                            # Simple resampling
                            ratio = self.sample_rate / actual_sample_rate
                            new_length = int(len(audio_array) * ratio)
                            if new_length > 0:
                                audio_array = np.interp(
                                    np.linspace(0, len(audio_array), new_length),
                                    np.arange(len(audio_array)),
                                    audio_array
                                ).astype(np.int16)
                        
                        audio_data = audio_array.tobytes()
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
            
            self.stream.stop_stream()
            self.stream.close()
            
        except Exception as e:
            print(f"Error in Windows audio capture: {e}")
            raise
        finally:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
    
    async def capture_microphone_to_deepgram(self, deepgram_client):
        """Capture ONLY microphone audio and send to Deepgram"""
        self.is_recording = True
        buffer = b""
        
        try:
            print("\n=== MICROPHONE MODE ===")
            self.list_wasapi_devices()
            
            # Find microphone device
            mic_device = self.microphone_index if self.microphone_index is not None else self.device_index
            
            if mic_device is None:
                # Use system default microphone
                try:
                    default_mic = self.audio.get_default_input_device_info()
                    mic_device = default_mic['index']
                    print(f"Using default microphone: {default_mic['name']}")
                except:
                    print("ERROR: No microphone found!")
                    return
            else:
                mic_info = self.audio.get_device_info_by_index(mic_device)
                print(f"Using microphone: {mic_info['name']}")
            
            # Get device info
            device_info = self.audio.get_device_info_by_index(mic_device)
            device_sample_rate = int(device_info['defaultSampleRate'])
            channels = min(2, int(device_info['maxInputChannels']))
            
            print(f"Microphone: {device_sample_rate}Hz, {channels} channel(s)")
            
            # Open audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=device_sample_rate,
                input=True,
                input_device_index=mic_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            print(f"Started microphone capture\n")
            
            while deepgram_client.is_active and self.stream.is_active():
                try:
                    # Get audio data from queue
                    if not self.audio_queue.empty():
                        audio_data = self.audio_queue.get_nowait()
                        
                        # Convert to numpy array
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        
                        # Convert stereo to mono if needed
                        if channels > 1 and len(audio_array) % channels == 0:
                            audio_array = audio_array.reshape(-1, channels)
                            audio_array = np.mean(audio_array, axis=1).astype(np.int16)
                        
                        # Resample to 16kHz if needed
                        if device_sample_rate != self.sample_rate:
                            ratio = self.sample_rate / device_sample_rate
                            new_length = int(len(audio_array) * ratio)
                            if new_length > 0:
                                audio_array = np.interp(
                                    np.linspace(0, len(audio_array), new_length),
                                    np.arange(len(audio_array)),
                                    audio_array
                                ).astype(np.int16)
                        
                        audio_data = audio_array.tobytes()
                        buffer += audio_data
                        
                        # Send buffer every 1 second
                        if len(buffer) >= self.sample_rate * 1 * 2:
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
            
            self.stream.stop_stream()
            self.stream.close()
            
        except Exception as e:
            print(f"Error in microphone capture: {e}")
            raise
        finally:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
    
    async def capture_both_audio_to_deepgram(self, deepgram_client):
        """Capture BOTH microphone and computer audio simultaneously and send to Deepgram
        
        This method:
        1. Opens a microphone stream
        2. Opens a loopback stream (computer audio)
        3. Mixes both audio sources together
        4. Sends combined audio to Deepgram
        """
        self.is_recording = True
        mic_buffer = b""
        loopback_buffer = b""
        
        try:
            print("\n=== BOTH MODE: Capturing Microphone + Computer Audio ===")
            
            # List available devices
            self.list_wasapi_devices()
            
            # 1. Find and setup MICROPHONE device
            mic_device = self.microphone_index
            if mic_device is None:
                # Use system default microphone
                try:
                    default_mic = self.audio.get_default_input_device_info()
                    mic_device = default_mic['index']
                    print(f"Using default microphone: {default_mic['name']}")
                except:
                    print("ERROR: No microphone found!")
                    return
            else:
                mic_info = self.audio.get_device_info_by_index(mic_device)
                print(f"Using selected microphone: {mic_info['name']}")
            
            # 2. Find and setup LOOPBACK device (computer audio)
            loopback_device = self._find_loopback_device()
            if loopback_device is None:
                print("WARNING: No loopback device found! Only microphone will be captured.")
                print("Computer audio requires WASAPI loopback support.")
                # Continue with just mic if no loopback
            else:
                loopback_info = self.audio.get_device_info_by_index(loopback_device)
                print(f"Using loopback device: {loopback_info['name']}")
            
            # Get microphone info
            mic_info = self.audio.get_device_info_by_index(mic_device)
            mic_sample_rate = int(mic_info['defaultSampleRate'])
            mic_channels = min(2, int(mic_info['maxInputChannels']))
            
            print(f"Microphone: {mic_sample_rate}Hz, {mic_channels} channel(s)")
            
            # Open MICROPHONE stream
            self.mic_stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=mic_channels,
                rate=mic_sample_rate,
                input=True,
                input_device_index=mic_device,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._mic_callback
            )
            self.mic_stream.start_stream()
            print("✓ Microphone stream started")
            
            # Open LOOPBACK stream if available
            if loopback_device is not None:
                loopback_info = self.audio.get_device_info_by_index(loopback_device)
                loopback_sample_rate = int(loopback_info['defaultSampleRate'])
                loopback_channels = int(loopback_info['maxInputChannels'])
                
                print(f"Loopback: {loopback_sample_rate}Hz, {loopback_channels} channel(s)")
                
                self.loopback_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=loopback_channels,
                    rate=loopback_sample_rate,
                    input=True,
                    input_device_index=loopback_device,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._loopback_callback
                )
                self.loopback_stream.start_stream()
                print("✓ Loopback stream started")
            else:
                loopback_sample_rate = mic_sample_rate
                loopback_channels = 0
            
            print("=== Both streams active ===\n")
            
            # Process audio from both sources
            while deepgram_client.is_active and (
                self.mic_stream.is_active() or 
                (self.loopback_stream and self.loopback_stream.is_active())
            ):
                try:
                    # Get microphone data
                    mic_data = None
                    if not self.mic_queue.empty():
                        mic_data = self.mic_queue.get_nowait()
                        
                        # Convert to numpy, handle stereo -> mono
                        mic_array = np.frombuffer(mic_data, dtype=np.int16)
                        if mic_channels > 1 and len(mic_array) % mic_channels == 0:
                            mic_array = mic_array.reshape(-1, mic_channels)
                            mic_array = np.mean(mic_array, axis=1).astype(np.int16)
                        
                        # Resample to 16kHz if needed
                        if mic_sample_rate != self.sample_rate:
                            ratio = self.sample_rate / mic_sample_rate
                            new_length = int(len(mic_array) * ratio)
                            if new_length > 0:
                                mic_array = np.interp(
                                    np.linspace(0, len(mic_array), new_length),
                                    np.arange(len(mic_array)),
                                    mic_array
                                ).astype(np.int16)
                        
                        mic_buffer += mic_array.tobytes()
                    
                    # Get loopback data
                    loopback_data = None
                    if self.loopback_stream and not self.loopback_queue.empty():
                        loopback_data = self.loopback_queue.get_nowait()
                        
                        # Convert to numpy, handle stereo -> mono
                        loopback_array = np.frombuffer(loopback_data, dtype=np.int16)
                        if loopback_channels > 1 and len(loopback_array) % loopback_channels == 0:
                            loopback_array = loopback_array.reshape(-1, loopback_channels)
                            loopback_array = np.mean(loopback_array, axis=1).astype(np.int16)
                        
                        # Resample to 16kHz if needed
                        if loopback_sample_rate != self.sample_rate:
                            ratio = self.sample_rate / loopback_sample_rate
                            new_length = int(len(loopback_array) * ratio)
                            if new_length > 0:
                                loopback_array = np.interp(
                                    np.linspace(0, len(loopback_array), new_length),
                                    np.arange(len(loopback_array)),
                                    loopback_array
                                ).astype(np.int16)
                        
                        loopback_buffer += loopback_array.tobytes()
                    
                    # Mix and send when we have enough data from both sources
                    # (or just mic if no loopback)
                    target_buffer_size = self.sample_rate * 1 * 2  # 1 second
                    
                    if len(mic_buffer) >= target_buffer_size:
                        # Get matching lengths
                        if self.loopback_stream and len(loopback_buffer) > 0:
                            # Mix both sources
                            min_len = min(len(mic_buffer), len(loopback_buffer))
                            mic_chunk = np.frombuffer(mic_buffer[:min_len], dtype=np.int16)
                            loopback_chunk = np.frombuffer(loopback_buffer[:min_len], dtype=np.int16)
                            
                            # Mix: average both sources (prevents clipping)
                            mixed = ((mic_chunk.astype(np.int32) + loopback_chunk.astype(np.int32)) // 2).astype(np.int16)
                            
                            # Send mixed audio
                            await deepgram_client.send_audio(mixed.tobytes())
                            
                            # Remove processed data
                            mic_buffer = mic_buffer[min_len:]
                            loopback_buffer = loopback_buffer[min_len:]
                        else:
                            # No loopback, just send mic
                            await deepgram_client.send_audio(mic_buffer[:target_buffer_size])
                            mic_buffer = mic_buffer[target_buffer_size:]
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as process_error:
                    print(f"Error processing audio: {process_error}")
                    await asyncio.sleep(0.1)
                    continue
            
            # Send any remaining buffers
            if len(mic_buffer) > 0 or len(loopback_buffer) > 0:
                if self.loopback_stream and len(loopback_buffer) > 0:
                    min_len = min(len(mic_buffer), len(loopback_buffer))
                    if min_len > 0:
                        mic_chunk = np.frombuffer(mic_buffer[:min_len], dtype=np.int16)
                        loopback_chunk = np.frombuffer(loopback_buffer[:min_len], dtype=np.int16)
                        mixed = ((mic_chunk.astype(np.int32) + loopback_chunk.astype(np.int32)) // 2).astype(np.int16)
                        await deepgram_client.send_audio(mixed.tobytes())
                elif len(mic_buffer) > 0:
                    await deepgram_client.send_audio(mic_buffer)
            
            # Stop streams
            if self.mic_stream:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            if self.loopback_stream:
                self.loopback_stream.stop_stream()
                self.loopback_stream.close()
            
        except Exception as e:
            print(f"Error in Both mode audio capture: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.is_recording = False
            if self.mic_stream:
                try:
                    self.mic_stream.stop_stream()
                    self.mic_stream.close()
                except:
                    pass
            if self.loopback_stream:
                try:
                    self.loopback_stream.stop_stream()
                    self.loopback_stream.close()
                except:
                    pass
    
    def __del__(self):
        """Cleanup PyAudio resources"""
        if hasattr(self, 'audio'):
            self.audio.terminate()