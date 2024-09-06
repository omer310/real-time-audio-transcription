import asyncio
import soundcard as sc
import numpy as np

class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

    def set_capture_mode(self, mode):
        mode = mode.lower()
        if mode == "microphone":
            self.capture_function = lambda: sc.get_microphone(id=sc.default_microphone().name).recorder(samplerate=self.sample_rate)
        elif mode == "computer audio":
            self.capture_function = lambda: sc.get_microphone(id=sc.default_speaker().name, include_loopback=True).recorder(samplerate=self.sample_rate)
        elif mode == "both":
            self.capture_function = self.capture_both
        else:
            raise ValueError(f"Invalid capture mode: {mode}")

    def capture_both(self):
        mic = sc.get_microphone(id=sc.default_microphone().name).recorder(samplerate=self.sample_rate)
        speaker = sc.get_microphone(id=sc.default_speaker().name, include_loopback=True).recorder(samplerate=self.sample_rate)
        return mic, speaker

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