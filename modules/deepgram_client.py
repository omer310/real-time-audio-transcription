import websockets

class DeepgramClient:
    def __init__(self, api_key, sample_rate=16000, channels=1):
        self.api_key = api_key
        self.sample_rate = sample_rate
        self.channels = channels
        self.uri = f"wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate={sample_rate}&channels={channels}&model=nova-2&interim_results=true&punctuate=true"

    def connect(self):
        return websockets.connect(self.uri, extra_headers={"Authorization": f"Token {self.api_key}"})