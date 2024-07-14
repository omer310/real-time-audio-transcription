import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox, font as tkfont
import logging
import os
from datetime import datetime
from modules.audio_capture import AudioCapture
from modules.transcription_processor import TranscriptionProcessor
from modules.deepgram_client import DeepgramClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StyledButton(tk.Canvas):
    def __init__(self, master, text, command, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.command = command
        self.text = text
        
        self.configure(bg="#f0f0f0", highlightthickness=0)
        self.text_widget = self.create_text(75, 25, text=text, fill="#333333", font=("Arial", 12, "bold"))
        self.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        if self.command:
            self.command()

class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Real-time Audio Transcription")
        master.geometry("600x500")
        master.configure(bg="#f0f0f0")

        self.api_key = os.getenv('DEEPGRAM_API_KEY')
        if not self.api_key:
            messagebox.showerror("Error", "DEEPGRAM_API_KEY environment variable not set.")
            master.quit()
            return

        self.setup_fonts()
        self.create_widgets()

        self.is_transcribing = False
        self.transcription_task = None
        self.output_file = None

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Set up asyncio event loop
        self.loop = asyncio.get_event_loop()

    def setup_fonts(self):
        self.title_font = tkfont.Font(family="Arial", size=18, weight="bold")
        self.text_font = tkfont.Font(family="Arial", size=12)

    def create_widgets(self):
        # Title
        title = tk.Label(self.master, text="Audio Transcription", font=self.title_font, bg="#f0f0f0", fg="#333333")
        title.pack(pady=(20, 10))

        # Microphone icon (represented as a circle)
        self.mic_canvas = tk.Canvas(self.master, width=100, height=100, bg="#f0f0f0", highlightthickness=0)
        self.mic_canvas.pack(pady=10)
        
        # Create the circle
        circle_x0, circle_y0 = 10, 10
        circle_x1, circle_y1 = 90, 90
        self.mic_icon = self.mic_canvas.create_oval(circle_x0, circle_y0, circle_x1, circle_y1, fill="#ff4f5e", outline="")
        
        # Calculate the center of the circle
        center_x = (circle_x0 + circle_x1) / 2
        center_y = (circle_y0 + circle_y1) / 2
        
        # Place the microphone icon text at the center
        # Using a custom Unicode character for microphone and adjusting its position
        self.mic_status = self.mic_canvas.create_text(center_x, center_y + 2, text="\uD83C\uDF99", font=("Arial", 36), fill="white")

        # Buttons
        button_frame = tk.Frame(self.master, bg="#f0f0f0")
        button_frame.pack(pady=10)

        self.start_button = StyledButton(button_frame, text="Start Transcription", command=self.start_transcription, width=150, height=50)
        self.start_button.pack(side=tk.LEFT, padx=10)

        self.stop_button = StyledButton(button_frame, text="Stop Transcription", command=self.stop_transcription, width=150, height=50)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        self.stop_button.configure(state=tk.DISABLED)

        # Transcription area
        self.transcription_area = scrolledtext.ScrolledText(self.master, wrap=tk.WORD, width=70, height=15, font=self.text_font)
        self.transcription_area.pack(padx=20, pady=20)

    def start_transcription(self):
        self.is_transcribing = True
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.transcription_area.delete('1.0', tk.END)
        self.mic_canvas.itemconfig(self.mic_icon, fill="#4CAF50")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = os.path.join("output", f"transcription_{timestamp}.txt")
        
        # Run the asyncio coroutine
        self.loop.create_task(self.run_transcription())

    def stop_transcription(self):
        self.is_transcribing = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.mic_canvas.itemconfig(self.mic_icon, fill="#ff4f5e")
        
        if self.output_file:
            messagebox.showinfo("Transcription Completed", f"Transcription saved to:\n{self.output_file}")

    async def run_transcription(self):
        audio_capture = AudioCapture()
        processor = TranscriptionProcessor()
        client = DeepgramClient(self.api_key)

        try:
            async with client.connect() as websocket:
                send_task = asyncio.create_task(audio_capture.capture_and_send_audio(websocket))
                receive_task = asyncio.create_task(self.receive_transcription(websocket, processor))
                await asyncio.gather(send_task, receive_task)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            self.master.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))

    async def receive_transcription(self, websocket, processor):
        try:
            async for message in websocket:
                if not self.is_transcribing:
                    break
                transcript = processor.process_message(message)
                if transcript:
                    self.master.after(0, self.update_transcription_area, transcript)
        except Exception as e:
            logging.error(f"Error in receive_transcription: {e}")

    def update_transcription_area(self, transcript):
        self.transcription_area.insert(tk.END, transcript + "\n")
        self.transcription_area.see(tk.END)
        with open(self.output_file, "a") as f:
            f.write(transcript + "\n")

def main():
    root = tk.Tk()
    app = TranscriptionApp(root)

    # Set up asyncio with Tkinter
    async def async_mainloop():
        while True:
            root.update()
            await asyncio.sleep(0.05)

    loop = asyncio.get_event_loop()
    loop.create_task(async_mainloop())
    loop.run_forever()

if __name__ == "__main__":
    main()