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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.deepgram_api_key = '6382ca5f48262b75747d5bb78fc0a9e803dc4f59'
        self.openai_api_key = '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'
        
        if not self.deepgram_api_key or not self.openai_api_key:
            ctk.CTkMessagebox.showerror("Error", "DEEPGRAM_API_KEY or OPENAI_API_KEY is not set.")
            self.root.quit()
            return

        self.openai_client = OpenAI(api_key=self.openai_api_key)

        self.create_widgets()

        self.is_transcribing = False
        self.transcription_task = None
        self.output_file = None

        # Set the output directory
        self.output_dir = r"C:\Users\omers\OneDrive\Documents\output for live"
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Set up asyncio event loop
        self.loop = asyncio.get_event_loop()

        self.timestamp = None

    def create_widgets(self):
        # Main frame (remove scrollbar)
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(main_frame, text="Audio Transcription", font=("Arial", 24, "bold"), text_color="white").pack(pady=(0, 20))

        # Title entry (adjusted to be closer to the label)
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(title_frame, text="Transcription Title:", text_color="white").pack(side="left", padx=(0, 5))
        self.title_entry = ctk.CTkEntry(title_frame, width=300, fg_color="#3b3b3b", text_color="white", border_color="#1f6aa5")
        self.title_entry.pack(side="left")
        self.title_entry.insert(0, "Untitled")

        # Microphone status (use an icon instead of text)
        self.mic_status = ctk.CTkLabel(main_frame, text="🎙️", font=("Arial", 48))
        self.mic_status.pack(pady=(0, 20))

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 20))
        self.start_button = ctk.CTkButton(button_frame, text="Start Transcription", command=self.start_transcription, fg_color="#1f6aa5", hover_color="#2980b9")
        self.start_button.pack(side="left", expand=True, padx=(0, 10))
        self.stop_button = ctk.CTkButton(button_frame, text="Stop Transcription", command=self.stop_transcription, state="disabled", fg_color="#1f6aa5", hover_color="#2980b9")
        self.stop_button.pack(side="left", expand=True, padx=(10, 0))

        # Transcription area (remove scrollbar)
        self.transcription_area = ctk.CTkTextbox(main_frame, wrap="word", height=300, fg_color="#3b3b3b", text_color="white", border_color="#1f6aa5")
        self.transcription_area.pack(fill="both", expand=True)

    def start_transcription(self):
        self.is_transcribing = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.transcription_area.delete("0.0", "end")
        self.mic_status.configure(text="🎙️ Recording...")

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_output_file = os.path.join(self.output_dir, f"temp_{self.timestamp}.txt")
        
        # Run the asyncio coroutine
        self.loop.create_task(self.run_transcription())

    def stop_transcription(self):
        self.is_transcribing = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.mic_status.configure(text="🎙️")
        
        if hasattr(self, 'temp_output_file') and os.path.exists(self.temp_output_file):
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
                    self.process_transcription_with_openai()
            except Exception as e:
                logging.error(f"Error renaming file: {e}")
                ctk.CTkMessagebox.showerror("Error", f"An error occurred while saving the file: {e}")
        else:
            logging.warning("No temporary file found to rename.")
            ctk.CTkMessagebox.showwarning("Warning", "No transcription data was saved.")

    def process_transcription_with_openai(self):
        with open(self.output_file, "r") as f:
            transcription = f.read()

        try:
            # Clean up transcription
            cleanup_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert in cleaning up speech transcriptions. Your task is to improve the readability and clarity of the conversation while maintaining its original meaning. Only proivde the cleaned transcription and nothing else."},
                    {"role": "user", "content": f"Please clean up this transcription by doing the following:\n"
                                            f"1. Remove filler words, stutters, and false starts.\n"
                                            f"2. Correct any obvious word errors or misheard words.\n"
                                            f"3. Remove unnecessary repetitions.\n"
                                            f"4. Improve sentence structure for clarity, but maintain the conversational tone.\n"
                                            f"5. Do not add any new information or change the meaning of the conversation.\n\n"
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

            ctk.CTkMessagebox.showinfo("Processing Complete", 
                                f"Original transcription: {self.output_file}\n"
                                f"Cleaned transcription: {cleaned_file}\n"
                                f"Summary: {summary_file}")

        except Exception as e:
            logging.error(f"Error processing transcription with OpenAI: {e}")
            ctk.CTkMessagebox.showerror("Error", f"An error occurred while processing the transcription: {e}")

    async def run_transcription(self):
        audio_capture = AudioCapture()
        processor = TranscriptionProcessor()
        client = DeepgramClient(self.deepgram_api_key)

        try:
            async with client.connect() as websocket:
                send_task = asyncio.create_task(audio_capture.capture_and_send_audio(websocket))
                receive_task = asyncio.create_task(self.receive_transcription(websocket, processor))
                await asyncio.gather(send_task, receive_task)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            self.root.after(0, lambda: ctk.CTkMessagebox.showerror("Error", f"An error occurred: {e}"))

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