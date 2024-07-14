import json
import re
from datetime import datetime

class TranscriptionProcessor:
    def __init__(self):
        self.current_sentence = ""
        self.last_written_sentence = ""

    def process_message(self, message):
        data = json.loads(message)
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']
            if transcript:
                return self.process_transcript(transcript)
        return ""

    def process_transcript(self, transcript):
        combined = self.current_sentence + " " + transcript
        sentences = re.split(r'(?<=[.!?])\s+', combined)
        
        if len(sentences) > 1:
            completed_sentences = sentences[:-1]
            self.current_sentence = sentences[-1]
            
            new_content = ""
            for sentence in completed_sentences:
                if sentence and sentence != self.last_written_sentence:
                    current_time = datetime.now().strftime("%H:%M:%S")
                    new_content += f"[{current_time}] {sentence}\n"
                    self.last_written_sentence = sentence
            
            return new_content.strip()
        else:
            self.current_sentence = combined
            return ""