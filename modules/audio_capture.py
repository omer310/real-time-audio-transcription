import asyncio
import soundcard as sc
import numpy as np

class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

    async def capture_and_send_audio(self, websocket):
        buffer = b""
        try:
            with sc.get_microphone(id=sc.default_speaker().name, include_loopback=True).recorder(samplerate=self.sample_rate) as mic:
                while True:
                    data = mic.record(numframes=self.chunk_size)
                    data = data.mean(axis=1)  # Convert stereo to mono
                    data = (data * 32767).astype(np.int16).tobytes()
                    
                    buffer += data
                    if len(buffer) >= self.chunk_size * 4:
                        await websocket.send(buffer)
                        buffer = b""
                    
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in capture_and_send_audio: {e}")
            raise