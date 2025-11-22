import asyncio
import customtkinter as ctk
from customtkinter import CTkScrollableFrame, CTkTextbox, CTkTabview
import logging
import os
from datetime import datetime
from modules.audio_capture import AudioCapture
from modules.windows_audio_capture import WindowsAudioCapture
import platform
from modules.deepgram_client import DeepgramLiveClient
from modules.conversate_engine import ConversateEngine
from openai import OpenAI
import re
from tkinter import messagebox, filedialog
from dotenv import load_dotenv
import subprocess
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv() 

class TranscriptionApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("TRANSCRIBE")
        self.root.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Teenage Engineering inspired color palette
        self.colors = {
            'bg_dark': '#0a0a0a',      # Almost black background
            'bg_medium': '#1a1a1a',    # Medium dark panels
            'bg_light': '#2a2a2a',     # Light panels
            'accent': '#ff6600',       # Teenage Engineering signature orange
            'text_primary': '#ffffff', # White text
            'text_secondary': '#888888', # Grey text
            'success': '#00ff41',      # Green
            'error': '#ff3b30',        # Red
            'border': '#333333',       # Subtle borders
            'te_orange': '#ff6600',    # TE signature orange (for buttons)
            'te_yellow': '#ffff00'     # TE accent yellow
        }
        
        # Font size settings (default larger)
        self.font_scale = 1.2  # Default scale factor
        self.fonts = {
            'header': 12,      # Section headers
            'body': 11,        # Normal text
            'small': 9,        # Metadata
            'code': 11,        # Monospace/code
            'button': 11       # Button text
        }
        
        self.root.configure(fg_color=self.colors['bg_dark'])

        # Get Deepgram API key from environment for transcription
        self.deepgram_api_key = os.getenv('DEEPGRAM_API_KEY')
        
        if not self.deepgram_api_key:
            messagebox.showerror("Error", "DEEPGRAM_API_KEY is not set.")
            self.root.quit()
            return

        # Get OpenAI API key from environment for post-processing
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.openai_api_key:
            messagebox.showerror("Error", "OPENAI_API_KEY is not set.")
            self.root.quit()
            return

        self.openai_client = OpenAI(api_key=self.openai_api_key)

        self.is_transcribing = False
        self.is_processing = False  # Track if post-processing is happening
        self.transcription_task = None
        self.output_file = None
        self.word_count = 0

        # Set the output directory
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Set up asyncio event loop
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.timestamp = None
        self.capture_mode = "computer audio"  # Default mode
        
        # Device and app preferences
        self.config_file = os.path.join(self.output_dir, "app_config.json")
        self.selected_input_device = None
        self.selected_output_device = None
        
        # Initialize Conversate state (can be overridden by config)
        self.conversate_enabled = False  # Default disabled
        
        # Get available devices (will be used in settings tab)
        if platform.system() == "Windows":
            self.input_devices = WindowsAudioCapture.get_all_input_devices()
            self.output_devices = WindowsAudioCapture.get_all_output_devices()
        else:
            self.input_devices = AudioCapture.get_all_input_devices()
            self.output_devices = []
        
        self.load_device_config()
        
        # Deepgram handles speaker diarization natively - no external dependencies needed!
        logging.info("Speaker diarization enabled via Deepgram")
        
        # Initialize Conversate Engine for AI insights
        self.conversate_engine = ConversateEngine(self.openai_client, enabled=self.conversate_enabled)
        self.insights_update_task = None
        self._toggling_conversate = False  # Flag to prevent recursive toggle calls
        
        # Create UI
        self.create_widgets()

    def create_widgets(self):
        # Main container with proper padding
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Create tabbed interface with minimal styling
        self.tabview = CTkTabview(
            main_container, 
            fg_color=self.colors['bg_dark'],
            segmented_button_fg_color=self.colors['bg_medium'],
            segmented_button_selected_color=self.colors['accent'],
            segmented_button_selected_hover_color=self.colors['accent'],
            segmented_button_unselected_color=self.colors['bg_medium'],
            text_color=self.colors['text_primary']
        )
        self.tabview.pack(fill="both", expand=True)

        # Add tabs with clean text-only labels
        self.tabview.add("TRANSCRIBE")
        self.tabview.add("FILES")
        self.tabview.add("SETTINGS")

        # Create tab contents
        self.create_transcription_tab()
        self.create_history_tab()
        self.create_settings_tab()

        # Minimalist status bar
        status_container = ctk.CTkFrame(self.root, fg_color=self.colors['bg_medium'], height=30)
        status_container.pack(side="bottom", fill="x", padx=20, pady=(0, 20))
        status_container.pack_propagate(False)
        
        self.status_bar = ctk.CTkLabel(
            status_container, 
            text="READY  |  MODEL: DEEPGRAM NOVA-3", 
            anchor="w", 
            text_color=self.colors['text_secondary'],
            font=("Consolas", self.get_font_size('small'))
        )
        self.status_bar.pack(side="left", padx=15, pady=8)

    def create_transcription_tab(self):
        """Main transcription interface"""
        tab = self.tabview.tab("TRANSCRIBE")
        tab.configure(fg_color=self.colors['bg_dark'])
        
        # Control panel with grid layout for perfect alignment
        control_frame = ctk.CTkFrame(tab, fg_color=self.colors['bg_medium'], corner_radius=0)
        control_frame.pack(fill="x", padx=0, pady=0)
        control_frame.grid_columnconfigure(1, weight=1)
        
        # Row 1: Title entry
        ctk.CTkLabel(
            control_frame, 
            text="TITLE", 
            text_color=self.colors['text_secondary'], 
            font=("Consolas", self.get_font_size('header'), "bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        self.title_entry = ctk.CTkEntry(
            control_frame, 
            height=40,
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_primary'], 
            border_color=self.colors['border'],
            border_width=1,
            font=("Consolas", self.get_font_size('body'))
        )
        self.title_entry.grid(row=0, column=1, sticky="ew", padx=(10, 20), pady=(20, 10))
        self.title_entry.insert(0, "Untitled")

        # Row 2: Audio source selection
        ctk.CTkLabel(
            control_frame, 
            text="SOURCE", 
            text_color=self.colors['text_secondary'], 
            font=("Consolas", self.get_font_size('header'), "bold"),
            anchor="w"
        ).grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        # Convert saved capture_mode to UI format (e.g., "computer audio" → "Computer Audio")
        capture_mode_display = self.capture_mode.title()  # Capitalizes first letter of each word
        
        self.capture_mode_var = ctk.StringVar(value=capture_mode_display)
        self.capture_mode_segment = ctk.CTkSegmentedButton(
            control_frame,
            values=["Microphone", "Computer Audio", "Both"],
            command=self.set_capture_mode,
            variable=self.capture_mode_var,
            font=("Consolas", self.get_font_size('body')),
            fg_color=self.colors['bg_light'],
            selected_color=self.colors['accent'],
            selected_hover_color=self.colors['accent'],
            unselected_color=self.colors['bg_light'],
            unselected_hover_color=self.colors['bg_medium'],
            text_color=self.colors['text_primary'],
            border_width=0
        )
        self.capture_mode_segment.grid(row=1, column=1, sticky="w", padx=(10, 20), pady=10)

        # Row 3: Status display
        status_container = ctk.CTkFrame(control_frame, fg_color="transparent")
        status_container.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        status_container.grid_columnconfigure(1, weight=1)
        
        # Status indicator
        self.mic_status_frame = ctk.CTkFrame(status_container, fg_color=self.colors['bg_light'], corner_radius=0, height=40)
        self.mic_status_frame.grid(row=0, column=0, sticky="w", padx=(0, 15))
        self.mic_status_frame.grid_propagate(False)  # Prevent frame from shrinking
        
        # Use grid layout for better alignment
        self.mic_status_icon = ctk.CTkLabel(
            self.mic_status_frame, 
            text="●", 
            font=("Consolas", int(self.get_font_size('body') * 1.5)), 
            text_color=self.colors['text_secondary'],
            width=30
        )
        self.mic_status_icon.grid(row=0, column=0, sticky="ns", padx=(12, 5))
        
        self.mic_status_text = ctk.CTkLabel(
            self.mic_status_frame, 
            text="READY", 
            font=("Consolas", self.get_font_size('body'), "bold"), 
            text_color=self.colors['text_secondary'],
            width=100,
            anchor="w"
        )
        self.mic_status_text.grid(row=0, column=1, sticky="ns", padx=(0, 12))
        
        # Configure row to center content vertically
        self.mic_status_frame.grid_rowconfigure(0, weight=1)

        # Duration
        duration_frame = ctk.CTkFrame(status_container, fg_color=self.colors['bg_light'], corner_radius=0, height=40)
        duration_frame.grid(row=0, column=1, sticky="w", padx=(0, 15))
        
        self.duration_label = ctk.CTkLabel(
            duration_frame, 
            text="00:00", 
            font=("Consolas", self.get_font_size('body')), 
            text_color=self.colors['text_primary'],
            width=60,
            anchor="center"
        )
        self.duration_label.pack(padx=12)
        
        # Word count
        word_count_frame = ctk.CTkFrame(status_container, fg_color=self.colors['bg_light'], corner_radius=0, height=40)
        word_count_frame.grid(row=0, column=2, sticky="w")
        
        self.word_count_label = ctk.CTkLabel(
            word_count_frame, 
            text="WORDS: 0", 
            text_color=self.colors['text_primary'], 
            font=("Consolas", self.get_font_size('body')),
            width=100,
            anchor="w"
        )
        self.word_count_label.pack(padx=12)

        # Row 4: Control buttons with equal sizing
        button_container = ctk.CTkFrame(control_frame, fg_color="transparent")
        button_container.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(10, 20))
        button_container.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.start_button = ctk.CTkButton(
            button_container, 
            text="START", 
            command=self.start_transcription, 
            fg_color=self.colors['te_orange'],
            hover_color=self.colors['te_orange'],
            text_color=self.colors['bg_dark'],
            height=48,
            corner_radius=0,
            font=("Consolas", self.get_font_size('button'), "bold"),
            border_width=0
        )
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        
        self.stop_button = ctk.CTkButton(
            button_container, 
            text="STOP", 
            command=self.stop_transcription, 
            state="disabled", 
            fg_color="#DC143C",  # Crimson red
            hover_color="#B22222",  # Darker red on hover
            text_color="white",
            height=48,
            corner_radius=0,
            font=("Consolas", self.get_font_size('button'), "bold"),
            border_width=0
        )
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=4)
        
        self.clear_button = ctk.CTkButton(
            button_container, 
            text="CLEAR", 
            command=self.clear_transcription, 
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['bg_light'],
            text_color=self.colors['text_secondary'],
            height=48,
            corner_radius=0,
            font=("Consolas", self.get_font_size('button'), "bold"),
            border_width=1,
            border_color=self.colors['border']
        )
        self.clear_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))

        # Progress bar (minimal design)
        self.progress_bar = ctk.CTkProgressBar(
            control_frame, 
            mode="indeterminate",
            height=2,
            fg_color=self.colors['bg_dark'],
            progress_color=self.colors['accent'],
            corner_radius=0,
            border_width=0
        )
        self.progress_bar.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.progress_bar.set(0)

        # Main container for dynamic layout
        self.main_transcription_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.main_transcription_container.pack(fill="both", expand=True, padx=0, pady=(20, 0))
        
        # Split view container for transcription and chat
        self.split_container = ctk.CTkFrame(self.main_transcription_container, fg_color="transparent")
        self.split_container.pack(fill="both", expand=True)
        self.split_container.grid_columnconfigure(0, weight=1)
        self.split_container.grid_columnconfigure(1, weight=1)
        self.split_container.grid_rowconfigure(1, weight=1)
        
        # Left panel - Transcription
        self.transcript_header = ctk.CTkFrame(self.split_container, fg_color="transparent", height=40)
        self.transcript_header.grid(row=0, column=0, sticky="ew", padx=(0, 1))
        self.transcript_header.pack_propagate(False)
        self.transcript_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.transcript_header, 
            text="TRANSCRIPT", 
            text_color=self.colors['text_secondary'], 
            font=("Consolas", self.get_font_size('header'), "bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=20)
        
        # Add toggle here too for easy access
        self.transcript_toggle = ctk.CTkSwitch(
            self.transcript_header,
            text="AI",
            command=self.toggle_conversate,
            width=40,
            progress_color=self.colors['accent'],
            button_color=self.colors['bg_light'],
            button_hover_color=self.colors['accent'],
            font=("Consolas", self.get_font_size('small'), "bold")
        )
        self.transcript_toggle.grid(row=0, column=1, sticky="e", padx=20)
        if self.conversate_enabled:
            self.transcript_toggle.select()
        
        self.transcription_area = ctk.CTkTextbox(
            self.split_container, 
            wrap="word", 
            fg_color=self.colors['bg_medium'], 
            text_color=self.colors['text_primary'], 
            border_color=self.colors['border'],
            border_width=1,
            corner_radius=0,
            font=("Consolas", self.get_font_size('code'))
        )
        self.transcription_area.grid(row=1, column=0, sticky="nsew", padx=(0, 1), pady=(0, 0))
        
        # Right panel - AI Chat Assistant
        self.chat_header = ctk.CTkFrame(self.split_container, fg_color="transparent", height=40)
        self.chat_header.grid(row=0, column=1, sticky="ew")
        self.chat_header.pack_propagate(False)
        self.chat_header.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            self.chat_header, 
            text="AI ASSISTANT", 
            text_color=self.colors['text_secondary'], 
            font=("Consolas", self.get_font_size('header'), "bold"),
            anchor="w"
        ).grid(row=0, column=0, sticky="w", padx=20)
        
        # Chat container
        self.chat_container = ctk.CTkFrame(
            self.split_container,
            fg_color=self.colors['bg_medium'],
            corner_radius=0
        )
        self.chat_container.grid(row=1, column=1, sticky="nsew", pady=(0, 0))
        self.chat_container.grid_rowconfigure(0, weight=1)
        self.chat_container.grid_columnconfigure(0, weight=1)
        
        # Chat messages area (read-only textbox)
        self.chat_area = ctk.CTkTextbox(
            self.chat_container,
            wrap="word",
            fg_color=self.colors['bg_medium'],
            text_color=self.colors['text_primary'],
            border_color=self.colors['border'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('body'))
        )
        self.chat_area.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Chat input area
        self.chat_input_frame = ctk.CTkFrame(self.chat_container, fg_color=self.colors['bg_light'], corner_radius=0, height=80)
        self.chat_input_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        self.chat_input_frame.grid_propagate(False)
        self.chat_input_frame.grid_columnconfigure(0, weight=1)
        
        # Input field
        self.chat_input = ctk.CTkTextbox(
            self.chat_input_frame,
            height=60,
            wrap="word",
            fg_color=self.colors['bg_light'],
            text_color=self.colors['text_primary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('body'))
        )
        self.chat_input.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Bind Enter key to send message (Shift+Enter for new line)
        self.chat_input.bind("<Return>", self.on_chat_enter)
        self.chat_input.bind("<Shift-Return>", lambda e: None)  # Allow Shift+Enter for newlines
        
        # Send button
        self.send_button = ctk.CTkButton(
            self.chat_input_frame,
            text="SEND",
            command=self.send_chat_message,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent'],
            text_color=self.colors['bg_dark'],
            corner_radius=0,
            font=("Consolas", self.get_font_size('button'), "bold"),
            width=80,
            height=60
        )
        self.send_button.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        
        # Initial welcome message in chat
        self.add_system_message(
            "🤖 AI Assistant Ready\n\n"
            "I'm here to help during your conversation!\n\n"
            "Start transcribing, then ask me anything:\n"
            "• \"What was just discussed?\"\n"
            "• \"What should I ask about [topic]?\"\n"
            "• \"Summarize the key points\"\n"
            "• \"Give me context on [topic]\"\n\n"
            "I have access to the full transcript and can help you participate more effectively in the conversation."
        )
        
        # Apply initial layout based on conversate_enabled
        if not self.conversate_enabled:
            self.hide_chat_panel()

    def create_history_tab(self):
        """Output history browser"""
        tab = self.tabview.tab("FILES")
        tab.configure(fg_color=self.colors['bg_dark'])
        
        # Header with action buttons
        header_frame = ctk.CTkFrame(tab, fg_color=self.colors['bg_medium'], corner_radius=0)
        header_frame.pack(fill="x", padx=0, pady=0)
        
        ctk.CTkLabel(
            header_frame, 
            text="FILES", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(side="left", padx=20, pady=15)
        
        ctk.CTkButton(
            header_frame, 
            text="OPEN FOLDER", 
            command=self.open_output_folder,
            fg_color=self.colors['bg_light'],
            hover_color=self.colors['bg_light'],
            text_color=self.colors['text_primary'],
            corner_radius=0,
            border_width=1,
            border_color=self.colors['border'],
            font=("Consolas", self.get_font_size('small')),
            height=34,
            width=120
        ).pack(side="right", padx=(0, 20), pady=15)
        
        ctk.CTkButton(
            header_frame, 
            text="REFRESH", 
            command=self.refresh_history,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent'],
            text_color=self.colors['bg_dark'],
            corner_radius=0,
            border_width=0,
            font=("Consolas", self.get_font_size('small'), "bold"),
            height=34,
            width=90
        ).pack(side="right", padx=10, pady=15)

        # Content area with two panels (60/40 split)
        content_frame = ctk.CTkFrame(tab, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Configure grid for better control
        content_frame.grid_columnconfigure(0, weight=6)  # 60% for file list
        content_frame.grid_columnconfigure(1, weight=4)  # 40% for preview
        content_frame.grid_rowconfigure(0, weight=1)

        # Left panel - File list
        left_panel = ctk.CTkFrame(content_frame, fg_color=self.colors['bg_medium'], corner_radius=0)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        
        self.file_listbox = CTkScrollableFrame(left_panel, fg_color=self.colors['bg_medium'])
        self.file_listbox.pack(fill="both", expand=True, padx=0, pady=0)

        # Right panel - Preview with tabs
        right_panel = ctk.CTkFrame(content_frame, fg_color=self.colors['bg_medium'], corner_radius=0)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # Create tabbed preview area
        self.preview_tabview = CTkTabview(
            right_panel, 
            fg_color=self.colors['bg_medium'],
            segmented_button_fg_color=self.colors['bg_light'],
            segmented_button_selected_color=self.colors['accent'],
            segmented_button_selected_hover_color=self.colors['accent'],
            segmented_button_unselected_color=self.colors['bg_light'],
            text_color=self.colors['text_primary']
        )
        self.preview_tabview.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Add tabs for different versions
        self.preview_tabview.add("RAW")
        self.preview_tabview.add("CLEANED")
        self.preview_tabview.add("SUMMARY")
        
        # Create text areas for each tab
        self.preview_raw = ctk.CTkTextbox(
            self.preview_tabview.tab("RAW"),
            wrap="word", 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_primary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('small'))
        )
        self.preview_raw.pack(fill="both", expand=True, padx=15, pady=15)
        self.preview_raw.insert("1.0", "Select a file to preview...")
        self.preview_raw.configure(state="disabled")
        
        self.preview_cleaned = ctk.CTkTextbox(
            self.preview_tabview.tab("CLEANED"),
            wrap="word", 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_primary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('small'))
        )
        self.preview_cleaned.pack(fill="both", expand=True, padx=15, pady=15)
        self.preview_cleaned.insert("1.0", "Select a file to preview...")
        self.preview_cleaned.configure(state="disabled")
        
        self.preview_summary = ctk.CTkTextbox(
            self.preview_tabview.tab("SUMMARY"),
            wrap="word", 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_primary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('small'))
        )
        self.preview_summary.pack(fill="both", expand=True, padx=15, pady=15)
        self.preview_summary.insert("1.0", "Select a file to preview...")
        self.preview_summary.configure(state="disabled")

        # Load initial file list
        self.refresh_history()

    def load_device_config(self):
        """Load application configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.selected_input_device = config.get('input_device')
                    self.selected_output_device = config.get('output_device')
                    self.font_scale = config.get('font_scale', 1.2)
                    saved_output_dir = config.get('output_directory')
                    if saved_output_dir and os.path.exists(saved_output_dir):
                        self.output_dir = saved_output_dir
                    # Load capture mode (default to "computer audio" if not found)
                    self.capture_mode = config.get('capture_mode', 'computer audio')
                    # Load AI assistant state (default to False if not found)
                    self.conversate_enabled = config.get('ai_assistant_enabled', False)
                    logging.info(f"Loaded config - Input: {self.selected_input_device}, Output: {self.selected_output_device}, Capture Mode: {self.capture_mode}, Font Scale: {self.font_scale}, Output Dir: {self.output_dir}, AI Assistant: {self.conversate_enabled}")
        except Exception as e:
            logging.warning(f"Could not load config: {e}")
    
    def save_device_config(self):
        """Save application configuration to file"""
        try:
            config = {
                'input_device': self.selected_input_device,
                'output_device': self.selected_output_device,
                'font_scale': self.font_scale,
                'output_directory': self.output_dir,
                'capture_mode': self.capture_mode,
                'ai_assistant_enabled': self.conversate_enabled  # Save AI assistant state
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Saved config - Input: {self.selected_input_device}, Output: {self.selected_output_device}, Capture Mode: {self.capture_mode}, Font Scale: {self.font_scale}, Output Dir: {self.output_dir}, AI Assistant: {self.conversate_enabled}")
        except Exception as e:
            logging.error(f"Could not save config: {e}")
    
    def get_font_size(self, key):
        """Get scaled font size"""
        return int(self.fonts[key] * self.font_scale)
    
    def update_all_fonts(self):
        """Update all UI fonts with new scale"""
        # This will recreate the widgets with new font sizes
        # For now, show a message that restart is needed
        messagebox.showinfo(
            "Font Size Updated",
            "Font size preference saved!\n\nPlease restart the application for changes to take effect."
        )

    def create_settings_tab(self):
        """Settings and preferences"""
        tab = self.tabview.tab("SETTINGS")
        tab.configure(fg_color=self.colors['bg_dark'])
        
        settings_container = ctk.CTkScrollableFrame(tab, fg_color=self.colors['bg_dark'])
        settings_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Audio Devices Section
        audio_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        audio_section.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            audio_section, 
            text="AUDIO DEVICES", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Input device selection
        ctk.CTkLabel(
            audio_section, 
            text="Input Device (Microphone)", 
            font=("Consolas", self.get_font_size('small')), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(0, 5))
        
        input_device_names = ["System Default"] + [d['name'] for d in self.input_devices]
        self.input_device_var = ctk.StringVar(value="System Default")
        
        # Set current selection from config
        if self.selected_input_device is not None:
            for device in self.input_devices:
                if device['index'] == self.selected_input_device:
                    self.input_device_var.set(device['name'])
                    break
        
        self.input_device_dropdown = ctk.CTkOptionMenu(
            audio_section,
            values=input_device_names,
            variable=self.input_device_var,
            command=self.on_input_device_changed,
            font=("Consolas", self.get_font_size('small')),
            fg_color=self.colors['bg_light'],
            button_color=self.colors['accent'],
            button_hover_color=self.colors['accent'],
            text_color=self.colors['text_primary'],
            corner_radius=0,
            dropdown_fg_color=self.colors['bg_light']
        )
        self.input_device_dropdown.pack(fill="x", padx=20, pady=(0, 15))
        
        # Output device selection (for Windows computer audio capture)
        if platform.system() == "Windows":
            ctk.CTkLabel(
                audio_section, 
                text="Output Device (Computer Audio)", 
                font=("Consolas", self.get_font_size('small')), 
                text_color=self.colors['text_secondary']
            ).pack(anchor="w", padx=20, pady=(0, 5))
            
            output_device_names = ["Auto Detect"] + [d['name'] for d in self.output_devices]
            self.output_device_var = ctk.StringVar(value="Auto Detect")
            
            # Set current selection from config
            if self.selected_output_device is not None:
                for device in self.output_devices:
                    if device['index'] == self.selected_output_device:
                        self.output_device_var.set(device['name'])
                        break
            
            self.output_device_dropdown = ctk.CTkOptionMenu(
                audio_section,
                values=output_device_names,
                variable=self.output_device_var,
                command=self.on_output_device_changed,
                font=("Consolas", self.get_font_size('small')),
                fg_color=self.colors['bg_light'],
                button_color=self.colors['accent'],
                button_hover_color=self.colors['accent'],
                text_color=self.colors['text_primary'],
                corner_radius=0,
                dropdown_fg_color=self.colors['bg_light']
            )
            self.output_device_dropdown.pack(fill="x", padx=20, pady=(0, 15))
        
        # Save device preferences button
        ctk.CTkButton(
            audio_section,
            text="SAVE AS DEFAULT",
            command=self.save_device_preferences,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent'],
            text_color=self.colors['bg_dark'],
            font=("Consolas", self.get_font_size('button'), "bold"),
            corner_radius=0,
            height=40
        ).pack(fill="x", padx=20, pady=(5, 20))

        # Model Info Section
        model_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        model_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            model_section, 
            text="AI MODELS", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        model_info_frame = ctk.CTkFrame(model_section, fg_color=self.colors['bg_light'], corner_radius=0)
        model_info_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        info_text = ctk.CTkTextbox(
            model_info_frame, 
            height=120, 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_secondary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('small'))
        )
        info_text.pack(fill="x", padx=12, pady=12)
        info_text.insert("1.0", 
            "Transcription: Deepgram Nova-3\n"
            "Speaker Diarization: Deepgram (built-in)\n"
            "Post-Processing: gpt-4o-mini\n\n"
            "Nova-3: Deepgram's fastest & most accurate model\n"
            "36% improvement over Whisper | 5-40x faster\n"
            "Real-time speaker identification included"
        )
        info_text.configure(state="disabled")

        # Conversate AI Assistant Section
        conversate_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        conversate_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            conversate_section, 
            text="AI ASSISTANT (CHAT)", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Conversate description
        conversate_info_frame = ctk.CTkFrame(conversate_section, fg_color=self.colors['bg_light'], corner_radius=0)
        conversate_info_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        conversate_info = ctk.CTkTextbox(
            conversate_info_frame, 
            height=100, 
            fg_color=self.colors['bg_light'], 
            text_color=self.colors['text_secondary'],
            border_width=0,
            corner_radius=0,
            font=("Consolas", self.get_font_size('small'))
        )
        conversate_info.pack(fill="x", padx=12, pady=12)
        conversate_info.insert("1.0", 
            "The AI Assistant provides a chat interface during live transcription.\n\n"
            "Features:\n"
            "• Ask questions about the conversation at any time\n"
            "• Get summaries of what was discussed\n"
            "• Request suggestions for what to say or ask\n"
            "• Access full conversation context\n"
            "• Receive contextual information and advice\n\n"
            "The assistant has access to the entire transcript and maintains\n"
            "conversation history for better responses."
        )
        conversate_info.configure(state="disabled")

        # Font Size Section
        font_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        font_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            font_section, 
            text="FONT SIZE", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        # Font size slider
        font_size_container = ctk.CTkFrame(font_section, fg_color="transparent")
        font_size_container.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            font_size_container, 
            text="Scale", 
            font=("Consolas", self.get_font_size('small')), 
            text_color=self.colors['text_secondary']
        ).pack(side="left", padx=(0, 10))
        
        self.font_scale_var = ctk.DoubleVar(value=self.font_scale)
        self.font_scale_label = ctk.CTkLabel(
            font_size_container,
            text=f"{int(self.font_scale * 100)}%",
            font=("Consolas", self.get_font_size('body'), "bold"),
            text_color=self.colors['text_primary'],
            width=50
        )
        self.font_scale_label.pack(side="right", padx=(10, 0))
        
        self.font_slider = ctk.CTkSlider(
            font_size_container,
            from_=0.8,
            to=2.0,
            number_of_steps=12,
            variable=self.font_scale_var,
            command=self.on_font_scale_changed,
            button_color=self.colors['accent'],
            button_hover_color=self.colors['accent'],
            progress_color=self.colors['accent'],
            fg_color=self.colors['bg_light']
        )
        self.font_slider.pack(side="left", fill="x", expand=True, padx=10)
        
        # Save font size button
        ctk.CTkButton(
            font_section,
            text="SAVE FONT SIZE",
            command=self.save_font_size,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent'],
            text_color=self.colors['bg_dark'],
            font=("Consolas", self.get_font_size('button'), "bold"),
            corner_radius=0,
            height=36
        ).pack(fill="x", padx=20, pady=(5, 20))

        # Output Settings Section
        output_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        output_section.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            output_section, 
            text="OUTPUT FOLDER", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        output_path_frame = ctk.CTkFrame(output_section, fg_color=self.colors['bg_light'], corner_radius=0)
        output_path_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.output_dir_label = ctk.CTkLabel(
            output_path_frame, 
            text=f"{self.output_dir}", 
            text_color=self.colors['text_secondary'],
            font=("Consolas", self.get_font_size('small')),
            anchor="w"
        )
        self.output_dir_label.pack(anchor="w", padx=12, pady=12)
        
        # Change output folder button
        ctk.CTkButton(
            output_section,
            text="CHANGE OUTPUT FOLDER",
            command=self.change_output_folder,
            fg_color=self.colors['accent'],
            hover_color=self.colors['accent'],
            text_color=self.colors['bg_dark'],
            font=("Consolas", self.get_font_size('button'), "bold"),
            corner_radius=0,
            height=36
        ).pack(fill="x", padx=20, pady=(0, 20))

        # About Section
        about_section = ctk.CTkFrame(settings_container, fg_color=self.colors['bg_medium'], corner_radius=0)
        about_section.pack(fill="x", padx=20, pady=(10, 20))
        
        ctk.CTkLabel(
            about_section, 
            text="ABOUT", 
            font=("Consolas", self.get_font_size('header'), "bold"), 
            text_color=self.colors['text_secondary']
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        ctk.CTkLabel(
            about_section, 
            text="TRANSCRIBE v2.0\nPOWERED BY OPENAI  |  MIT LICENSE", 
            text_color=self.colors['text_secondary'],
            font=("Consolas", self.get_font_size('small')),
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def add_system_message(self, message: str):
        """Add a system message to chat area"""
        # Only add if conversate is enabled (chat panel visible)
        if not self.conversate_enabled:
            return
            
        self.chat_area.configure(state="normal")
        if self.chat_area.get("1.0", "end-1c"):  # If not empty, add separator
            self.chat_area.insert("end", "\n\n")
        self.chat_area.insert("end", f"{'─' * 50}\n", "separator")
        self.chat_area.insert("end", f"{message}\n", "system")
        self.chat_area.insert("end", f"{'─' * 50}\n", "separator")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
        
        # Configure tags for styling
        self.chat_area.tag_config("separator", foreground=self.colors['border'])
        self.chat_area.tag_config("system", foreground=self.colors['text_secondary'])
        self.chat_area.tag_config("user", foreground=self.colors['accent'])
        self.chat_area.tag_config("assistant", foreground=self.colors['text_primary'])
    
    def add_user_message(self, message: str):
        """Add a user message to chat area"""
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", "\n\n")
        self.chat_area.insert("end", "YOU:\n", "user")
        self.chat_area.insert("end", f"{message}\n", "user")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
    
    def add_assistant_message(self, message: str):
        """Add an assistant message to chat area"""
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", "\n")
        self.chat_area.insert("end", "AI:\n", "assistant")
        self.chat_area.insert("end", f"{message}\n", "assistant")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")
    
    def on_chat_enter(self, event):
        """Handle Enter key in chat input"""
        # Only send if not holding Shift
        if not event.state & 0x0001:  # Check if Shift is not pressed
            self.send_chat_message()
            return "break"  # Prevent default newline behavior
        return None
    
    def send_chat_message(self):
        """Send a chat message to the AI assistant"""
        if not self.conversate_enabled:
            messagebox.showinfo("Assistant Disabled", "Please enable the AI Assistant toggle first.")
            return
        
        # Get message from input
        message = self.chat_input.get("1.0", "end-1c").strip()
        
        if not message:
            return
        
        # Clear input
        self.chat_input.delete("1.0", "end")
        
        # Add user message to chat
        self.add_user_message(message)
        
        # Show "thinking" indicator
        self.add_assistant_message("🤔 Thinking...")
        
        # Process message asynchronously
        self.loop.create_task(self.process_chat_message(message))
    
    async def process_chat_message(self, user_message: str):
        """Process user message and get AI response"""
        try:
            # Get response from conversate engine
            response = await self.conversate_engine.ask_question(user_message)
            
            if response:
                # Remove "thinking" indicator and add real response
                self.chat_area.configure(state="normal")
                # Remove last two lines ("AI:\n" and "🤔 Thinking...\n")
                content = self.chat_area.get("1.0", "end")
                lines = content.split("\n")
                # Find and remove the thinking message
                for i in range(len(lines) - 1, max(0, len(lines) - 10), -1):
                    if "🤔 Thinking..." in lines[i]:
                        # Remove this line and the "AI:" line before it
                        lines = lines[:i-1] + lines[i+1:]
                        break
                
                # Rebuild the chat area
                self.chat_area.delete("1.0", "end")
                self.chat_area.insert("1.0", "\n".join(lines))
                self.chat_area.configure(state="disabled")
                
                # Add actual response
                self.add_assistant_message(response)
            else:
                # Replace thinking with error
                self.chat_area.configure(state="normal")
                content = self.chat_area.get("1.0", "end")
                content = content.replace("🤔 Thinking...", "❌ Error: Could not process your question.")
                self.chat_area.delete("1.0", "end")
                self.chat_area.insert("1.0", content)
                self.chat_area.see("end")
                self.chat_area.configure(state="disabled")
        
        except Exception as e:
            logging.error(f"Error processing chat message: {e}")
            self.add_assistant_message(f"❌ Error: {str(e)}")
    
    def show_chat_panel(self):
        """Show the chat panel and enable split-screen layout"""
        # Show chat panel
        self.chat_header.grid(row=0, column=1, sticky="ew")
        self.chat_container.grid(row=1, column=1, sticky="nsew", pady=(0, 0))
        
        # Update split container to 50/50
        self.split_container.grid_columnconfigure(0, weight=1)
        self.split_container.grid_columnconfigure(1, weight=1)
        
        # Update transcript area padding
        self.transcription_area.grid_configure(padx=(0, 1))
        
        logging.info("Chat panel shown - split screen layout active")
    
    def hide_chat_panel(self):
        """Hide the chat panel and expand transcript to full width"""
        # Hide chat panel
        self.chat_header.grid_remove()
        self.chat_container.grid_remove()
        
        # Make transcript full width
        self.split_container.grid_columnconfigure(0, weight=1)
        self.split_container.grid_columnconfigure(1, weight=0)
        
        # Update transcript area padding
        self.transcription_area.grid_configure(padx=0)
        
        logging.info("Chat panel hidden - full screen transcript active")
    
    def toggle_conversate(self):
        """Toggle the Conversate AI chat assistant"""
        # Prevent recursive calls when syncing toggles
        if self._toggling_conversate:
            return
        
        try:
            self._toggling_conversate = True
            
            # Toggle the internal state (flip it)
            self.conversate_enabled = not self.conversate_enabled
            
            # Update the toggle switch to match the new state
            if self.conversate_enabled:
                self.transcript_toggle.select()
            else:
                self.transcript_toggle.deselect()
            
            # Update engine (note: still collects transcript in background even when "off")
            self.conversate_engine.set_enabled(self.conversate_enabled)
        finally:
            self._toggling_conversate = False
        
        if self.conversate_enabled:
            logging.info("Conversate AI assistant enabled - showing chat panel")
            self.show_chat_panel()
            
            # Add welcome message
            self.chat_area.configure(state="normal")
            if not self.chat_area.get("1.0", "end-1c").strip():
                # Chat is empty, add initial message
                self.add_system_message(
                    "🤖 AI Assistant Ready\n\n"
                    "I'm here to help during your conversation!\n"
                    "Ask me anything about what's being discussed."
                )
            else:
                # Chat has history, just add status message
                self.add_system_message(
                    "✅ AI ASSISTANT RE-ENABLED\n\n"
                    "I'm back and have the full conversation context.\n"
                    "Ask me anything!"
                )
            
            # Enable input
            self.chat_input.configure(state="normal")
            self.send_button.configure(state="normal")
        else:
            logging.info("Conversate AI assistant disabled - reverting to full-screen")
            # Note: We still collect transcript in background for flexibility
            # If user toggles back on mid-conversation, they can ask about earlier parts
            self.hide_chat_panel()
            logging.info("UI: Full-screen transcript | Background: Still collecting context")
        
        # Save the preference
        self.save_device_config()
    
    def set_capture_mode(self, value):
        self.capture_mode = value.lower()
        # Auto-save when capture mode is changed
        self.save_device_config()
        logging.info(f"Capture mode changed to: {self.capture_mode}")
    
    def on_input_device_changed(self, device_name):
        """Handle input device selection change"""
        if device_name == "System Default":
            self.selected_input_device = None
        else:
            # Find device index by name
            for device in self.input_devices:
                if device['name'] == device_name:
                    self.selected_input_device = device['index']
                    break
        
        # Auto-save device preference
        self.save_device_config()
        logging.info(f"Input device changed to: {device_name} (index: {self.selected_input_device})")
    
    def on_output_device_changed(self, device_name):
        """Handle output device selection change"""
        if device_name == "Auto Detect":
            self.selected_output_device = None
        else:
            # Find device index by name
            for device in self.output_devices:
                if device['name'] == device_name:
                    self.selected_output_device = device['index']
                    break
        
        # Auto-save device preference
        self.save_device_config()
        logging.info(f"Output device changed to: {device_name} (index: {self.selected_output_device})")
    
    def save_device_preferences(self):
        """Save current device selections as defaults"""
        self.save_device_config()
        messagebox.showinfo("Saved", "Device preferences saved as defaults!")
    
    def on_font_scale_changed(self, value):
        """Update font scale label when slider moves"""
        self.font_scale_label.configure(text=f"{int(value * 100)}%")
    
    def save_font_size(self):
        """Save font size preference"""
        self.font_scale = self.font_scale_var.get()
        self.save_device_config()
        self.update_all_fonts()
    
    def change_output_folder(self):
        """Allow user to select a new output folder"""
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.output_dir
        )
        
        if folder:
            # Update output directory
            self.output_dir = folder
            
            # Create output directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Update the label
            self.output_dir_label.configure(text=self.output_dir)
            
            # Save preference
            self.save_device_config()
            
            messagebox.showinfo(
                "Output Folder Changed",
                f"Output folder updated to:\n{self.output_dir}\n\nAll new transcriptions will be saved here."
            )
            
            # Refresh history to show files in new location
            self.refresh_history()

    def clear_transcription(self):
        # Don't allow clearing during recording or processing
        if self.is_transcribing or self.is_processing:
            return
            
        self.transcription_area.delete("0.0", "end")
        self.word_count = 0
        self.word_count_label.configure(text="WORDS: 0")
        self.mic_status_icon.configure(text="●", text_color=self.colors['text_secondary'])
        self.mic_status_text.configure(text="READY", text_color=self.colors['text_secondary'])
        self.duration_label.configure(text="00:00")
        
        # Clear conversate context and reset chat
        self.conversate_engine.clear_context()
        
        # Clear chat area
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.configure(state="disabled")
        
        # Add appropriate message
        if self.conversate_enabled:
            self.add_system_message(
                "🔄 CONVERSATION CLEARED\n\n"
                "Ready for a new conversation.\n"
                "Start transcribing and I'll be ready to help!"
            )

    def toggle_theme(self):
        # Theme is fixed to dark mode for minimalist design
        pass

    def start_transcription(self):
        # Prevent starting if still processing previous transcription
        if self.is_processing:
            messagebox.showwarning(
                "Please Wait",
                "Previous transcription is still being processed.\n\n"
                "Please wait for processing to complete before starting a new recording."
            )
            return
        
        self.is_transcribing = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.clear_button.configure(state="disabled")  # Disable clear during recording
        
        # Keep AI toggle buttons enabled during transcription
        self.transcript_toggle.configure(state="normal")
        
        self.transcription_area.delete("0.0", "end")
        self.mic_status_icon.configure(text="●", text_color=self.colors['error'])
        self.mic_status_text.configure(text="RECORDING", text_color=self.colors['error'])
        self.progress_bar.start()
        self.status_bar.configure(text="TRANSCRIBING  |  MODEL: DEEPGRAM NOVA-3")

        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_output_file = os.path.join(self.output_dir, f"temp_{self.timestamp}.txt")
        logging.info(f"Starting transcription. Temp file: {self.temp_output_file}")
        
        # No need for separate audio file - Deepgram handles speaker diarization natively!
        
        # Clear conversate context for new session
        self.conversate_engine.clear_context()
        if self.conversate_enabled:
            self.add_system_message(
                "🎧 TRANSCRIPTION STARTED\n\n"
                "I'm now listening to the conversation.\n"
                "Ask me anything once the conversation starts!"
            )
        
        self.start_time = datetime.now()
        self.update_duration()
        
        # Run the asyncio coroutine
        self.loop.create_task(self.run_transcription())

    def stop_transcription(self):
        self.is_transcribing = False
        
        # Stop the Deepgram client
        if hasattr(self, 'deepgram_client'):
            self.deepgram_client.stop()
        
        # Show final message in chat if conversate is enabled
        if self.conversate_enabled:
            stats = self.conversate_engine.get_stats()
            self.add_system_message(
                "✅ TRANSCRIPTION STOPPED\n\n"
                f"Captured {stats['transcript_segments']} transcript segments.\n"
                "You can still ask questions about the conversation!\n\n"
                "Processing transcription..."
            )
        
        # Don't re-enable start button yet - wait for processing to complete
        self.stop_button.configure(state="disabled")
        
        # Show processing state
        self.mic_status_icon.configure(text="●", text_color=self.colors['accent'])
        self.mic_status_text.configure(text="PROCESSING", text_color=self.colors['accent'])
        self.progress_bar.start()  # Keep progress bar running during processing
        self.status_bar.configure(text="PROCESSING  |  CLEANING & SUMMARIZING")
        
        # Cancel the duration update
        if hasattr(self, 'duration_update_job'):
            self.root.after_cancel(self.duration_update_job)
        
        if hasattr(self, 'temp_output_file') and os.path.exists(self.temp_output_file):
            logging.info(f"Stopping transcription. Temp file exists: {self.temp_output_file}")
            title = self.title_entry.get().strip() or "Untitled"
            safe_title = re.sub(r'[^\w\-_\. ]', '_', title)
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
                    # Process the transcription asynchronously to avoid freezing
                    self.loop.create_task(self.process_transcription_async())
            except Exception as e:
                logging.error(f"Error renaming file: {e}")
                messagebox.showerror("Error", f"An error occurred while saving the file: {e}")
                # Re-enable buttons on error
                self.start_button.configure(state="normal")
                self.clear_button.configure(state="normal")
                self.transcript_toggle.configure(state="normal")
                self.progress_bar.stop()
                self.progress_bar.set(0)
                self.mic_status_icon.configure(text="●", text_color=self.colors['error'])
                self.mic_status_text.configure(text="ERROR", text_color=self.colors['error'])
                self.status_bar.configure(text="ERROR  |  FAILED TO SAVE FILE")
        else:
            logging.warning(f"No temporary file found: {getattr(self, 'temp_output_file', 'Not set')}")
            messagebox.showwarning("Warning", "No transcription data was saved.")
            # Re-enable buttons since no processing will happen
            self.start_button.configure(state="normal")
            self.clear_button.configure(state="normal")
            self.transcript_toggle.configure(state="normal")
            self.progress_bar.stop()
            self.progress_bar.set(0)
            self.mic_status_icon.configure(text="●", text_color=self.colors['accent'])
            self.mic_status_text.configure(text="NO DATA", text_color=self.colors['accent'])
            self.status_bar.configure(text="READY  |  MODEL: DEEPGRAM NOVA-3")

    def update_status_safe(self, message):
        """Thread-safe status bar update"""
        try:
            # Use the event loop to schedule on main thread
            self.loop.call_soon_threadsafe(lambda: self.status_bar.configure(text=message))
        except Exception as e:
            logging.error(f"Error updating status: {e}")
    
    def schedule_ui_update(self, func):
        """Thread-safe UI update scheduling"""
        try:
            self.loop.call_soon_threadsafe(func)
        except Exception as e:
            logging.error(f"Error scheduling UI update: {e}")
    
    async def process_transcription_async(self):
        """Process transcription asynchronously to avoid UI freezing"""
        self.is_processing = True
        self.status_bar.configure(text="PROCESSING  |  CLEANING & SUMMARIZING")
        
        # Run the heavy processing in a thread pool to avoid blocking
        await asyncio.to_thread(self.process_transcription_with_openai)
        
        # Re-enable UI after processing completes
        self.is_processing = False
        self.start_button.configure(state="normal")
        self.clear_button.configure(state="normal")
        self.transcript_toggle.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.mic_status_icon.configure(text="●", text_color=self.colors['success'])
        self.mic_status_text.configure(text="COMPLETE", text_color=self.colors['success'])
    
    def process_transcription_with_openai(self):
        with open(self.output_file, "r", encoding='utf-8') as f:
            transcription = f.read()
        
        # Deepgram already added speaker labels during transcription!
        logging.info("Transcription includes speaker labels from Deepgram")

        try:
            # Update status for cleanup phase
            self.update_status_safe("PROCESSING  |  CLEANING TRANSCRIPT")
            
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
                                            f"6. IMPORTANT: Preserve all speaker labels (e.g., [Speaker 0], [Speaker 1]) and timestamps.\n"
                                            f"Here's the transcription:\n{transcription}"}
                ]
            )
            cleaned_transcription = cleanup_response.choices[0].message.content

            # Update status for summary phase
            self.update_status_safe("PROCESSING  |  GENERATING SUMMARY")
            
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

            with open(cleaned_file, "w", encoding='utf-8') as f:
                f.write(cleaned_transcription)

            with open(summary_file, "w", encoding='utf-8') as f:
                f.write(summary)

            logging.info(f"Processing complete. Files saved: {self.output_file}, {cleaned_file}, {summary_file}")
            
            # Update UI - we're in a thread, so schedule on main thread
            self.update_status_safe("COMPLETE  |  TRANSCRIPTION SAVED")
            
            # Refresh the history tab
            self.schedule_ui_update(self.refresh_history)
            
            # Show completion notification
            self.schedule_ui_update(lambda: messagebox.showinfo(
                "Processing Complete", 
                f"Transcription processed successfully!\n\n"
                f"Files saved:\n"
                f"• Raw transcript\n"
                f"• Cleaned version\n"
                f"• Summary\n\n"
                f"View in the Output History tab."
            ))

        except Exception as e:
            logging.error(f"Error processing transcription with OpenAI: {e}")
            # Update UI - we're in a thread, so schedule on main thread
            self.update_status_safe(f"ERROR  |  {str(e).upper()}")
            # Re-enable buttons even on error
            self.schedule_ui_update(lambda: self.start_button.configure(state="normal"))
            self.schedule_ui_update(lambda: self.clear_button.configure(state="normal"))
            self.schedule_ui_update(lambda: self.transcript_toggle.configure(state="normal"))

    async def run_transcription(self):
        # Choose the appropriate audio capture based on mode and platform
        if platform.system() == "Windows":
            if self.capture_mode == "computer audio":
                # Use selected output device for computer audio only
                audio_capture = WindowsAudioCapture(
                    sample_rate=16000, 
                    device_index=self.selected_output_device
                )
                capture_method = audio_capture.capture_and_send_audio_to_deepgram
            elif self.capture_mode == "both":
                # Use BOTH microphone and computer audio
                audio_capture = WindowsAudioCapture(
                    sample_rate=16000,
                    device_index=self.selected_output_device,  # For computer audio
                    microphone_index=self.selected_input_device  # For microphone
                )
                capture_method = audio_capture.capture_both_audio_to_deepgram
            else:
                # Microphone only
                audio_capture = WindowsAudioCapture(
                    sample_rate=16000,
                    microphone_index=self.selected_input_device
                )
                capture_method = audio_capture.capture_microphone_to_deepgram
        else:
            # Non-Windows platforms (use AudioCapture)
            audio_capture = AudioCapture(
                sample_rate=16000,
                device_index=self.selected_input_device
            )
            audio_capture.set_capture_mode(self.capture_mode)
            capture_method = audio_capture.capture_and_send_audio_to_deepgram
        
        # Initialize Deepgram client (speaker diarization is built-in!)
        self.deepgram_client = DeepgramLiveClient(self.deepgram_api_key)
        
        # Set up the transcription callback
        self.deepgram_client.set_transcription_callback(self.handle_transcription)

        try:
            async with self.deepgram_client:
                await capture_method(self.deepgram_client)
        except Exception as e:
            error_message = str(e)
            logging.error(f"An error occurred: {error_message}")
            self.root.after(0, lambda error=error_message: messagebox.showerror("Error", f"An error occurred: {error}"))

    async def handle_transcription(self, formatted_transcript):
        """Handle transcription results from Deepgram"""
        if self.is_transcribing:
            self.root.after(0, self.update_transcription_area, formatted_transcript)

    def update_transcription_area(self, transcript):
        self.transcription_area.insert("end", transcript + "\n")
        self.transcription_area.see("end")
        with open(self.temp_output_file, "a", encoding='utf-8') as f:
            f.write(transcript + "\n")
        
        self.word_count += len(transcript.split())
        self.word_count_label.configure(text=f"WORDS: {self.word_count}")
        
        # Feed transcript to Conversate engine (always collects, even if UI is hidden)
        # This allows user to toggle chat ON mid-conversation and still have full context
        if transcript.strip():
            self.conversate_engine.add_transcript(transcript)

    
    def update_duration(self):
        if self.is_transcribing:
            duration = datetime.now() - self.start_time
            minutes, seconds = divmod(duration.seconds, 60)
            self.duration_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.duration_update_job = self.root.after(1000, self.update_duration)

    def refresh_history(self):
        """Refresh the file list in history tab"""
        # Clear existing items
        for widget in self.file_listbox.winfo_children():
            widget.destroy()

        # Get all txt files (excluding temp files)
        files = [f for f in os.listdir(self.output_dir) if f.endswith('.txt') and not f.startswith('temp_')]
        
        # Group files by base name
        file_groups = {}
        for file in files:
            base_name = file.replace('_cleaned.txt', '').replace('_summary.txt', '').replace('.txt', '')
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file)
        
        # Sort by modification time (newest first)
        sorted_groups = sorted(file_groups.items(), 
                             key=lambda x: max(os.path.getmtime(os.path.join(self.output_dir, f)) for f in x[1]),
                             reverse=True)
        
        if not sorted_groups:
            ctk.CTkLabel(
                self.file_listbox, 
                text="NO FILES\nSTART A TRANSCRIPTION TO CREATE FILES", 
                text_color=self.colors['text_secondary'],
                font=("Consolas", self.get_font_size('small')),
                justify="center"
            ).pack(pady=40)
            return

        # Create file items
        for base_name, group_files in sorted_groups:
            file_card = ctk.CTkFrame(self.file_listbox, fg_color=self.colors['bg_light'], corner_radius=0, height=90)
            file_card.pack(fill="x", pady=1, padx=15)
            file_card.pack_propagate(False)
            
            # Get main file info
            main_file = next((f for f in group_files if not ('_cleaned' in f or '_summary' in f)), group_files[0])
            file_path = os.path.join(self.output_dir, main_file)
            file_stat = os.stat(file_path)
            file_date = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            file_size_kb = file_stat.st_size / 1024
            
            # Main container with grid layout
            content_frame = ctk.CTkFrame(file_card, fg_color="transparent")
            content_frame.pack(fill="both", expand=True, padx=12, pady=12)
            content_frame.grid_columnconfigure(0, weight=1)
            
            # File name
            ctk.CTkLabel(
                content_frame, 
                text=base_name, 
                font=("Consolas", self.get_font_size('body'), "bold"), 
                text_color=self.colors['text_primary'],
                anchor="w"
            ).grid(row=0, column=0, sticky="w", pady=(0, 4))
            
            # File metadata
            ctk.CTkLabel(
                content_frame, 
                text=f"{file_date}  |  {file_size_kb:.1f}KB  |  {len(group_files)} FILES", 
                font=("Consolas", self.get_font_size('small')), 
                text_color=self.colors['text_secondary'],
                anchor="w"
            ).grid(row=1, column=0, sticky="w")
            
            # Buttons container
            btn_container = ctk.CTkFrame(content_frame, fg_color="transparent")
            btn_container.grid(row=0, column=1, rowspan=2, sticky="e", padx=(10, 0))
            
            ctk.CTkButton(
                btn_container, 
                text="VIEW", 
                width=60,
                height=30,
                command=lambda f=main_file: self.preview_file(f),
                fg_color=self.colors['accent'],
                hover_color=self.colors['accent'],
                text_color=self.colors['bg_dark'],
                corner_radius=0,
                font=("Consolas", self.get_font_size('small'), "bold"),
                border_width=0
            ).pack(side="left", padx=(0, 4))
            
            ctk.CTkButton(
                btn_container, 
                text="OPEN", 
                width=60,
                height=30,
                command=lambda f=main_file: self.open_file(f),
                fg_color=self.colors['bg_dark'],
                hover_color=self.colors['bg_dark'],
                text_color=self.colors['text_primary'],
                corner_radius=0,
                font=("Consolas", self.get_font_size('small'), "bold"),
                border_width=1,
                border_color=self.colors['border']
            ).pack(side="left", padx=2)
            
            ctk.CTkButton(
                btn_container, 
                text="DEL", 
                width=50,
                height=30,
                command=lambda bn=base_name, gf=group_files: self.delete_file_group(bn, gf),
                fg_color=self.colors['bg_dark'],
                hover_color=self.colors['error'],
                text_color=self.colors['text_secondary'],
                corner_radius=0,
                font=("Consolas", self.get_font_size('small')),
                border_width=1,
                border_color=self.colors['border']
            ).pack(side="left", padx=(4, 0))

    def preview_file(self, filename):
        """Preview all versions of a file (raw, cleaned, summary)"""
        # Get base name
        base_name = filename.replace('_cleaned.txt', '').replace('_summary.txt', '').replace('.txt', '')
        
        # File paths
        raw_file = os.path.join(self.output_dir, f"{base_name}.txt")
        cleaned_file = os.path.join(self.output_dir, f"{base_name}_cleaned.txt")
        summary_file = os.path.join(self.output_dir, f"{base_name}_summary.txt")
        
        # Load and display raw file
        try:
            if os.path.exists(raw_file):
                with open(raw_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.preview_raw.configure(state="normal")
                self.preview_raw.delete("1.0", "end")
                self.preview_raw.insert("1.0", content)
                self.preview_raw.configure(state="disabled")
            else:
                self.preview_raw.configure(state="normal")
                self.preview_raw.delete("1.0", "end")
                self.preview_raw.insert("1.0", "Raw file not found.")
                self.preview_raw.configure(state="disabled")
        except Exception as e:
            self.preview_raw.configure(state="normal")
            self.preview_raw.delete("1.0", "end")
            self.preview_raw.insert("1.0", f"Error loading raw file: {e}")
            self.preview_raw.configure(state="disabled")
        
        # Load and display cleaned file
        try:
            if os.path.exists(cleaned_file):
                # Try multiple encodings
                content = None
                for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                    try:
                        with open(cleaned_file, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content:
                    self.preview_cleaned.configure(state="normal")
                    self.preview_cleaned.delete("1.0", "end")
                    self.preview_cleaned.insert("1.0", content)
                    self.preview_cleaned.configure(state="disabled")
                else:
                    self.preview_cleaned.configure(state="normal")
                    self.preview_cleaned.delete("1.0", "end")
                    self.preview_cleaned.insert("1.0", "Could not decode file with any common encoding.")
                    self.preview_cleaned.configure(state="disabled")
            else:
                self.preview_cleaned.configure(state="normal")
                self.preview_cleaned.delete("1.0", "end")
                self.preview_cleaned.insert("1.0", "Cleaned file not found.\n\nThis file may not have been processed yet.")
                self.preview_cleaned.configure(state="disabled")
        except Exception as e:
            self.preview_cleaned.configure(state="normal")
            self.preview_cleaned.delete("1.0", "end")
            self.preview_cleaned.insert("1.0", f"Error loading cleaned file: {e}")
            self.preview_cleaned.configure(state="disabled")
        
        # Load and display summary file
        try:
            if os.path.exists(summary_file):
                with open(summary_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.preview_summary.configure(state="normal")
                self.preview_summary.delete("1.0", "end")
                self.preview_summary.insert("1.0", content)
                self.preview_summary.configure(state="disabled")
            else:
                self.preview_summary.configure(state="normal")
                self.preview_summary.delete("1.0", "end")
                self.preview_summary.insert("1.0", "Summary file not found.\n\nThis file may not have been processed yet.")
                self.preview_summary.configure(state="disabled")
        except Exception as e:
            self.preview_summary.configure(state="normal")
            self.preview_summary.delete("1.0", "end")
            self.preview_summary.insert("1.0", f"Error loading summary file: {e}")
            self.preview_summary.configure(state="disabled")

    def open_file(self, filename):
        """Open file with default application"""
        file_path = os.path.join(self.output_dir, filename)
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def delete_file_group(self, base_name, files):
        """Delete a group of related files"""
        result = messagebox.askyesno(
            "Confirm Delete", 
            f"Delete '{base_name}' and all related files?\n\nThis will delete {len(files)} file(s)."
        )
        if result:
            try:
                for file in files:
                    file_path = os.path.join(self.output_dir, file)
                    os.remove(file_path)
                self.refresh_history()
                
                # Clear all preview areas
                for preview_area in [self.preview_raw, self.preview_cleaned, self.preview_summary]:
                    preview_area.configure(state="normal")
                    preview_area.delete("1.0", "end")
                    preview_area.insert("1.0", "Select a file to preview...")
                    preview_area.configure(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete files: {e}")
    
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        try:
            if platform.system() == 'Windows':
                os.startfile(self.output_dir)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', self.output_dir])
            else:  # Linux
                subprocess.run(['xdg-open', self.output_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

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
