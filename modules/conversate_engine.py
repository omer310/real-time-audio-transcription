import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

class ConversateEngine:
    """
    AI-powered conversation assistant with chat interface.
    Maintains full context of ongoing transcription and allows user to ask questions.
    """
    
    SYSTEM_PROMPT = """You are an intelligent conversation assistant helping a user during a live conversation or meeting.

Context: The user is in a live conversation that is being transcribed in real-time. You have access to the FULL transcript of everything said so far. The user can ask you questions at any time to:
- Get summaries of what was discussed
- Ask for suggestions on what to say or ask next
- Get context or background information on topics being discussed
- Request relevant facts or information
- Get advice on how to respond or participate
- Understand key points or decisions made

Your capabilities:
1. You can see the ENTIRE conversation transcript up to this moment
2. You track speakers (e.g., Speaker 0, Speaker 1)
3. You understand context, topics, and conversation flow
4. You provide actionable, helpful responses

Response guidelines:
- Be conversational and natural (like a helpful colleague)
- Reference specific parts of the transcript when relevant
- Provide concise but complete answers (2-5 sentences typically)
- If asked for suggestions, be specific and actionable
- If asked about "what was just said", focus on the most recent parts
- If asked about topics, provide clear summaries
- Always be aware that the conversation is ONGOING - your advice should be timely

Important: The transcript you see is the conversation the user is CURRENTLY IN, not a historical conversation. Your suggestions should be relevant for real-time use."""

    def __init__(self, openai_client, enabled: bool = True):
        """
        Initialize the Conversate engine.
        
        Args:
            openai_client: OpenAI client instance
            enabled: Whether chat assistant is enabled
        """
        self.openai_client = openai_client
        self.enabled = enabled
        self.transcript_buffer = []  # All transcript segments (full conversation)
        self.chat_history = []  # Chat message history (user questions + AI responses)
        self.max_chat_history = 10  # Keep last 10 exchanges for context
        self.is_processing = False
        
        logging.info("ConversateEngine initialized in chat mode")
    
    def add_transcript(self, transcript: str):
        """
        Add a new transcript segment to the full transcript buffer.
        
        Args:
            transcript: New transcript text to add
        """
        if not transcript or not transcript.strip():
            return
        
        # Add timestamp to transcript
        timestamped_transcript = {
            'text': transcript.strip(),
            'timestamp': datetime.now()
        }
        
        self.transcript_buffer.append(timestamped_transcript)
        logging.debug(f"Added transcript segment (total: {len(self.transcript_buffer)})")
    
    def get_full_transcript(self) -> str:
        """
        Get the complete conversation transcript.
        
        Returns:
            Formatted full transcript string
        """
        if not self.transcript_buffer:
            return ""
        
        transcript_lines = []
        for segment in self.transcript_buffer:
            time_str = segment['timestamp'].strftime("%H:%M:%S")
            transcript_lines.append(f"[{time_str}] {segment['text']}")
        
        return "\n".join(transcript_lines)
    
    def get_recent_transcript(self, max_segments: int = 10) -> str:
        """
        Get recent transcript segments.
        
        Args:
            max_segments: Maximum number of recent segments to include
        
        Returns:
            Formatted recent transcript string
        """
        segments = self.transcript_buffer[-max_segments:] if max_segments else self.transcript_buffer
        
        if not segments:
            return ""
        
        transcript_lines = []
        for segment in segments:
            time_str = segment['timestamp'].strftime("%H:%M:%S")
            transcript_lines.append(f"[{time_str}] {segment['text']}")
        
        return "\n".join(transcript_lines)
    
    async def ask_question(self, user_question: str) -> Optional[str]:
        """
        Process a user question with full conversation context.
        
        Args:
            user_question: The question from the user
        
        Returns:
            AI response or None if error
        """
        if not self.enabled or self.is_processing:
            return None
        
        try:
            self.is_processing = True
            
            # Get full transcript for context
            full_transcript = self.get_full_transcript()
            
            if not full_transcript:
                return "I don't have any conversation context yet. Start the transcription and I'll be able to help!"
            
            # Build messages with chat history for continuity
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT}
            ]
            
            # Add recent chat history for context (last 5 exchanges)
            recent_history = self.chat_history[-(self.max_chat_history * 2):]
            for msg in recent_history:
                messages.append(msg)
            
            # Add current transcript context and user question
            messages.append({
                "role": "user",
                "content": f"FULL CONVERSATION TRANSCRIPT:\n{full_transcript}\n\n---\n\nMY QUESTION: {user_question}"
            })
            
            logging.info(f"Processing user question: {user_question[:50]}...")
            
            # Get AI response
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Store in chat history
            self.chat_history.append({"role": "user", "content": user_question})
            self.chat_history.append({"role": "assistant", "content": ai_response})
            
            # Maintain chat history limit
            if len(self.chat_history) > self.max_chat_history * 2:
                self.chat_history = self.chat_history[-(self.max_chat_history * 2):]
            
            logging.info("AI response generated successfully")
            return ai_response
            
        except Exception as e:
            logging.error(f"Error processing question: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
        finally:
            self.is_processing = False
    
    def clear_context(self):
        """Clear all conversation context and chat history."""
        self.transcript_buffer = []
        self.chat_history = []
        logging.info("Conversation context and chat history cleared")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable chat assistant."""
        self.enabled = enabled
        logging.info(f"ConversateEngine chat {'enabled' if enabled else 'disabled'}")
    
    def get_stats(self) -> Dict:
        """Get current statistics about the engine."""
        return {
            'enabled': self.enabled,
            'transcript_segments': len(self.transcript_buffer),
            'chat_messages': len(self.chat_history),
            'is_processing': self.is_processing
        }
