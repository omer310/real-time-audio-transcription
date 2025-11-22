import asyncio
import io
import wave
import tempfile
import os
import numpy as np
from datetime import datetime
from deepgram import DeepgramClient
from typing import Callable
import logging


class DeepgramLiveClient:
    def __init__(self, api_key):
        """Initialize Deepgram transcription client with built-in speaker diarization
        
        Args:
            api_key: Deepgram API key
        """
        self.api_key = api_key
        # Correct initialization for SDK v5.x
        self.client = DeepgramClient(api_key=api_key)
        self.sample_rate = 16000
        self.is_active = True
        self.transcription_callback = None
        # Nova-3 is the best model for accuracy and speed
        self.model = "nova-3"
        
        # Buffer for accumulating audio
        self.audio_buffer = bytearray()
        self.is_processing = False
        self.min_buffer_size = self.sample_rate * 2 * 2  # 2 seconds of audio in bytes
        
        logging.info(f"DeepgramLiveClient initialized with model: {self.model} (speaker diarization enabled)")
        
    def set_transcription_callback(self, callback: Callable):
        """Set the callback function for transcription results"""
        self.transcription_callback = callback
    
    def _format_transcript_with_speakers(self, words):
        """Format transcript with speaker labels
        
        Args:
            words: List of word objects from Deepgram response, each with:
                   - word: the word text
                   - speaker: speaker ID (0, 1, 2, etc.)
                   - speaker_confidence: confidence score (optional)
                   
        Returns:
            Formatted string with speaker labels like: "[Speaker 0] Hello [Speaker 1] Hi there"
        """
        if not words:
            return ""
        
        # Group words by speaker
        current_speaker = None
        formatted_parts = []
        current_text = []
        
        for word_obj in words:
            word = word_obj.word if hasattr(word_obj, 'word') else str(word_obj)
            speaker = word_obj.speaker if hasattr(word_obj, 'speaker') else None
            
            if speaker is None:
                # No speaker info, just add the word
                current_text.append(word)
            elif speaker != current_speaker:
                # Speaker changed
                if current_text:
                    # Save previous speaker's text
                    formatted_parts.append(' '.join(current_text))
                    current_text = []
                
                # Start new speaker section
                current_speaker = speaker
                formatted_parts.append(f"[Speaker {speaker}]")
                current_text.append(word)
            else:
                # Same speaker, continue
                current_text.append(word)
        
        # Add remaining text
        if current_text:
            formatted_parts.append(' '.join(current_text))
        
        return ' '.join(formatted_parts)
    
    async def send_audio(self, audio_data):
        """Send audio data to Deepgram for transcription
        
        Args:
            audio_data: Raw audio bytes
        """
        if not self.is_active:
            return
        
        # Remove prefixes if they exist
        if audio_data.startswith(b"mic:"):
            audio_data = audio_data[4:]
        elif audio_data.startswith(b"speaker:"):
            audio_data = audio_data[8:]
        
        # Add to buffer (Deepgram handles speaker diarization internally)
        self.audio_buffer.extend(audio_data)
        
        # When buffer reaches minimum size, transcribe
        if len(self.audio_buffer) >= self.min_buffer_size and not self.is_processing:
            await self._process_audio_chunk()
    
    async def _process_audio_chunk(self):
        """Process accumulated audio buffer with Deepgram"""
        if self.is_processing or len(self.audio_buffer) == 0:
            return
        
        self.is_processing = True
        
        try:
            # Take a chunk from the buffer
            chunk_size = self.sample_rate * 3 * 2  # 3 seconds in bytes
            chunk_data = bytes(self.audio_buffer[:chunk_size])
            
            # Keep overlap to ensure NO words are missed
            overlap_size = int(self.sample_rate * 1.5 * 2)  # 1.5 second overlap
            if len(self.audio_buffer) > chunk_size:
                self.audio_buffer = self.audio_buffer[chunk_size - overlap_size:]
            else:
                self.audio_buffer = bytearray()
            
            # Create a temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                # Write WAV file
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(chunk_data)
                
                # Transcribe with Deepgram
                try:
                    with open(temp_path, 'rb') as audio_file:
                        logging.debug(f"[Deepgram] Transcribing {len(chunk_data)} bytes of audio...")
                        
                        # Read audio file into memory
                        audio_data = audio_file.read()
                        
                        # Use Deepgram SDK v5.x API - correct method path
                        # Enable speaker diarization with diarize=True
                        def transcribe():
                            return self.client.listen.v1.media.transcribe_file(
                                request=audio_data,
                                model=self.model,
                                language="en-US",
                                punctuate=True,
                                smart_format=True,
                                diarize=True  # Enable built-in speaker diarization
                            )
                        
                        # Run in thread pool to avoid blocking the event loop
                        response = await asyncio.to_thread(transcribe)
                        
                        # Extract transcript from response with speaker labels
                        # Response structure: response.results.channels[0].alternatives[0]
                        if response and hasattr(response, 'results'):
                            results = response.results
                            if (hasattr(results, 'channels') and 
                                len(results.channels) > 0 and
                                hasattr(results.channels[0], 'alternatives') and
                                len(results.channels[0].alternatives) > 0):
                                
                                alternative = results.channels[0].alternatives[0]
                                
                                # Check if we have words with speaker labels
                                if hasattr(alternative, 'words') and alternative.words:
                                    # Format transcript with speaker labels
                                    formatted_text = self._format_transcript_with_speakers(alternative.words)
                                    
                                    if formatted_text.strip():
                                        logging.debug(f"[Deepgram] Transcribed with speakers: {formatted_text[:100]}...")
                                        
                                        # Call the callback with the transcription
                                        if self.transcription_callback:
                                            timestamp = datetime.now().strftime("%H:%M:%S")
                                            formatted_transcript = f"[{timestamp}] {formatted_text.strip()}"
                                            
                                            if asyncio.iscoroutinefunction(self.transcription_callback):
                                                await self.transcription_callback(formatted_transcript)
                                            else:
                                                self.transcription_callback(formatted_transcript)
                                    else:
                                        logging.debug("[Deepgram] Empty transcript received")
                                else:
                                    # Fallback to plain transcript if no words available
                                    transcript = alternative.transcript if hasattr(alternative, 'transcript') else ""
                                    
                                    if transcript.strip():
                                        logging.debug(f"[Deepgram] Transcribed (no speakers): {transcript[:100]}...")
                                        
                                        if self.transcription_callback:
                                            timestamp = datetime.now().strftime("%H:%M:%S")
                                            formatted_transcript = f"[{timestamp}] {transcript.strip()}"
                                            
                                            if asyncio.iscoroutinefunction(self.transcription_callback):
                                                await self.transcription_callback(formatted_transcript)
                                            else:
                                                self.transcription_callback(formatted_transcript)
                            else:
                                logging.warning("[Deepgram] Response missing expected structure")
                        else:
                            logging.warning("[Deepgram] No results in response")
                        
                except Exception as e:
                    logging.error(f"[Deepgram] Error transcribing audio: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[Deepgram] Error processing audio chunk: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_processing = False
    
    def stop(self):
        """Stop the client from processing more audio"""
        self.is_active = False
    
    async def finalize_transcription(self):
        """Process any remaining audio in the buffer"""
        self.is_active = False
        if len(self.audio_buffer) > 0:
            await self._process_audio_chunk()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.finalize_transcription()
