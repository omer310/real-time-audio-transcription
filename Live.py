import asyncio
import customtkinter as ctk
from customtkinter import CTkScrollableFrame, CTkTextbox
import logging
import os
from datetime import datetime
from modules.audio_capture import AudioCapture
from modules.transcription_processor import TranscriptionProcessor
from modules.deepgram_client import DeepgramClient
import openai
from openai import OpenAI
import re
from tkinter import messagebox
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv() 

class TranscriptionApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Real-time Audio Transcription")
        self.root.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Set a consistent background color
        self.root.configure(fg_color="#2b2b2b")  # Dark gray background

        # Directly use the API keys instead of os.getenv
        self.deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.deepgram_api_key or not self.openai_api_key:
            messagebox.showerror("Error", "DEEPGRAM_API_KEY or OPENAI_API_KEY is not set.")
            self.root.quit()
            return

        self.openai_client = OpenAI(api_key=self.openai_api_key)

        self.create_widgets()

        self.is_transcribing = False
        self.transcription_task = None
        self.output_file = None
        self.word_count = 0

        # Set the output directory
        self.output_dir = r"C:\Users\omers\OneDrive\Documents\output for live"
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Set up asyncio event loop
        self.loop = asyncio.get_event_loop()

        self.timestamp = None

        self.capture_mode = "computer audio"  # Default mode

    def create_widgets(self):
        # Main frame
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(main_frame, text="Audio Transcription", font=("Arial", 24, "bold"), text_color="white").pack(pady=(0, 20))

        # Title entry
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(title_frame, text="Transcription Title:", text_color="white").pack(side="left", padx=(0, 5))
        self.title_entry = ctk.CTkEntry(title_frame, width=300, fg_color="#3b3b3b", text_color="white", border_color="#1f6aa5")
        self.title_entry.pack(side="left")
        self.title_entry.insert(0, "Untitled")

        # Capture mode buttons (replaced with segmented button)
        capture_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        capture_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(capture_frame, text="Capture Mode:", text_color="white").pack(side="left", padx=(0, 5))
        self.capture_mode_var = ctk.StringVar(value="Computer Audio")
        self.capture_mode_segment = ctk.CTkSegmentedButton(
            capture_frame,
            values=["Microphone", "Computer Audio", "Both"],
            command=self.set_capture_mode,
            variable=self.capture_mode_var
        )
        self.capture_mode_segment.pack(side="left", padx=(5, 0))

        # Status indicator frame
        status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        status_frame.pack(fill="x", pady=(0, 20))
        
        # Microphone status (now uses colored icons and text)
        self.mic_status_icon = ctk.CTkLabel(status_frame, text="⚪", font=("Arial", 24))
        self.mic_status_icon.pack(side="left", padx=(0, 10))
        self.mic_status_text = ctk.CTkLabel(status_frame, text="Ready", font=("Arial", 16, "bold"), text_color="white")
        self.mic_status_text.pack(side="left")

        # Recording duration
        self.duration_label = ctk.CTkLabel(status_frame, text="00:00", font=("Arial", 16), text_color="white")
        self.duration_label.pack(side="right")

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 20))
        self.start_button = ctk.CTkButton(button_frame, text="Start Transcription", command=self.start_transcription, fg_color="#1f6aa5", hover_color="#2980b9")
        self.start_button.pack(side="left", expand=True, padx=(0, 5))
        self.stop_button = ctk.CTkButton(button_frame, text="Stop Transcription", command=self.stop_transcription, state="disabled", fg_color="#1f6aa5", hover_color="#2980b9")
        self.stop_button.pack(side="left", expand=True, padx=(5, 5))
        self.clear_button = ctk.CTkButton(button_frame, text="Clear", command=self.clear_transcription, fg_color="#e74c3c", hover_color="#c0392b")
        self.clear_button.pack(side="left", expand=True, padx=(5, 0))

        # Transcription area
        self.transcription_area = ctk.CTkTextbox(main_frame, wrap="word", height=300, fg_color="#3b3b3b", text_color="white", border_color="#1f6aa5")
        self.transcription_area.pack(fill="both", expand=True)

        # Word count label
        self.word_count_label = ctk.CTkLabel(main_frame, text="Words: 0", text_color="white")
        self.word_count_label.pack(pady=(10, 0))

        # Progress indicator
        self.progress_bar = ctk.CTkProgressBar(main_frame, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0)

        # Dark/Light mode toggle
        self.theme_switch = ctk.CTkSwitch(main_frame, text="Dark Mode", command=self.toggle_theme)
        self.theme_switch.pack(pady=(10, 0))
        self.theme_switch.select()  # Start in dark mode

        # Status bar
        self.status_bar = ctk.CTkLabel(self.root, text="Ready", anchor="w", text_color="white")
        self.status_bar.pack(side="bottom", fill="x", padx=10, pady=5)

    def set_capture_mode(self, value):
        self.capture_mode = value.lower()

    def clear_transcription(self):
        self.transcription_area.delete("0.0", "end")
        self.word_count = 0
        self.word_count_label.configure(text="Words: 0")
        self.mic_status_icon.configure(text="⚪")
        self.mic_status_text.configure(text="Ready", text_color="white")
        self.duration_label.configure(text="00:00")

    def toggle_theme(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_switch.deselect()
        else:
            ctk.set_appearance_mode("dark")
            self.theme_switch.select()

    def start_transcription(self):
        self.is_transcribing = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.transcription_area.delete("0.0", "end")
        self.mic_status_icon.configure(text="🔴")
        self.mic_status_text.configure(text="Recording", text_color="#FF4136")
        self.progress_bar.start()
        self.status_bar.configure(text="Transcribing...")

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_output_file = os.path.join(self.output_dir, f"temp_{self.timestamp}.txt")
        logging.info(f"Starting transcription. Temp file: {self.temp_output_file}")
        
        self.start_time = datetime.now()
        self.update_duration()
        
        # Run the asyncio coroutine
        self.loop.create_task(self.run_transcription())

    def stop_transcription(self):
        self.is_transcribing = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.mic_status_icon.configure(text="⚪")
        self.mic_status_text.configure(text="Ready", text_color="white")
        self.progress_bar.stop()
        self.status_bar.configure(text="Ready")
        
        # Cancel the duration update
        if hasattr(self, 'duration_update_job'):
            self.root.after_cancel(self.duration_update_job)
        
        if hasattr(self, 'temp_output_file') and os.path.exists(self.temp_output_file):
            logging.info(f"Stopping transcription. Temp file exists: {self.temp_output_file}")
            title = self.title_entry.get().strip() or "Untitled"
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)  # Replace invalid filename characters
            final_output_file = os.path.join(self.output_dir, f"{safe_title}.txt")
            
            # Ensure filename is unique
            counter = 1
            while os.path.exists(final_output_file):
                final_output_file = os.path.join(self.output_dir, f"{safe_title}_{counter}.txt")
                counter += 1
            
            try:
                os.rename(self.temp_output_file, final_output_file)
                self.output_file = final_output_file
                
                if self.output_file:
                    # Process the transcription without showing a message
                    self.process_transcription_with_openai()
            except Exception as e:
                logging.error(f"Error renaming file: {e}")
                messagebox.showerror("Error", f"An error occurred while saving the file: {e}")
        else:
            logging.warning(f"No temporary file found: {getattr(self, 'temp_output_file', 'Not set')}")
            messagebox.showwarning("Warning", "No transcription data was saved.")

    def process_transcription_with_openai(self):
        with open(self.output_file, "r") as f:
            transcription = f.read()

        try:
            # Clean up transcription
            cleanup_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in cleaning up speech transcriptions. Your task is to improve the readability and clarity of the conversation while maintaining its original meaning. Only provide the cleaned transcription and nothing else."},
                    {"role": "user", "content": f"Please clean up this transcription by doing the following:\n"
                                            f"1. Remove filler words, stutters, and false starts.\n"
                                            f"2. Correct any obvious word errors or misheard words.\n"
                                            f"3. Remove unnecessary repetitions.\n"
                                            f"4. Improve sentence structure for clarity, but maintain the conversational tone.\n"
                                            f"5. Do not add any new information or change the meaning of the conversation.\n"
                                            f"6. Leave the timestamps and dont remove them.\n"
                                            f"Here's the transcription:\n{transcription}"}
                ]
            )
            cleaned_transcription = cleanup_response.choices[0].message.content

            # Summarize transcription
            summary_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes transcriptions."},
                    {"role": "user", "content": f"Please provide a brief summary of this transcription: {cleaned_transcription}"}
                ]
            )
            summary = summary_response.choices[0].message.content

            # Save cleaned transcription and summary
            base_name = os.path.splitext(os.path.basename(self.output_file))[0]
            cleaned_file = os.path.join(self.output_dir, f"{base_name}_cleaned.txt")
            summary_file = os.path.join(self.output_dir, f"{base_name}_summary.txt")

            # Ensure filenames are unique
            counter = 1
            while os.path.exists(cleaned_file) or os.path.exists(summary_file):
                cleaned_file = os.path.join(self.output_dir, f"{base_name}_cleaned_{counter}.txt")
                summary_file = os.path.join(self.output_dir, f"{base_name}_summary_{counter}.txt")
                counter += 1

            with open(cleaned_file, "w") as f:
                f.write(cleaned_transcription)

            with open(summary_file, "w") as f:
                f.write(summary)

            logging.info(f"Processing complete. Files saved: {self.output_file}, {cleaned_file}, {summary_file}")

        except Exception as e:
            logging.error(f"Error processing transcription with OpenAI: {e}")
            # We're not showing an error message to the user, but we're logging it

    async def run_transcription(self):
        audio_capture = AudioCapture()
        audio_capture.set_capture_mode(self.capture_mode)
        processor = TranscriptionProcessor()
        client = DeepgramClient(self.deepgram_api_key)

        try:
            async with client.connect() as websocket:
                send_task = asyncio.create_task(audio_capture.capture_and_send_audio(websocket))
                receive_task = asyncio.create_task(self.receive_transcription(websocket, processor))
                await asyncio.gather(send_task, receive_task)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {e}"))

    async def receive_transcription(self, websocket, processor):
        try:
            async for message in websocket:
                if not self.is_transcribing:
                    break
                transcript = processor.process_message(message)
                if transcript:
                    self.root.after(0, self.update_transcription_area, transcript)
        except Exception as e:
            logging.error(f"Error in receive_transcription: {e}")

    def update_transcription_area(self, transcript):
        self.transcription_area.insert("end", transcript + "\n")
        self.transcription_area.see("end")
        with open(self.temp_output_file, "a") as f:
            f.write(transcript + "\n")
        
        self.word_count += len(transcript.split())
        self.word_count_label.configure(text=f"Words: {self.word_count}")

    def update_duration(self):
        if self.is_transcribing:
            duration = datetime.now() - self.start_time
            minutes, seconds = divmod(duration.seconds, 60)
            self.duration_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.duration_update_job = self.root.after(1000, self.update_duration)

def main():
    app = TranscriptionApp()
    
    # Set up asyncio with customtkinter
    async def async_mainloop():
        while True:
            app.root.update()
            await asyncio.sleep(0.05)

    loop = asyncio.get_event_loop()
    loop.create_task(async_mainloop())
    loop.run_forever()

if __name__ == "__main__":
    main()