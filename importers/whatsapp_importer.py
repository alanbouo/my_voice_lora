"""Import messages from WhatsApp chat exports."""
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models import Message, ContextCategory, Tone


class WhatsAppImporter:
    """
    Import your messages from WhatsApp chat exports.
    
    How to export from WhatsApp:
    1. Open the chat you want to export
    2. Tap the three dots menu > More > Export chat
    3. Choose "Without media" (faster, smaller)
    4. Save the .txt file
    """
    
    # Common WhatsApp date/time formats
    PATTERNS = [
        # Format: [DD/MM/YYYY, HH:MM:SS] Name: Message
        r'\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]\s*([^:]+):\s*(.*)',
        # Format: DD/MM/YYYY, HH:MM - Name: Message
        r'(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\s*-\s*([^:]+):\s*(.*)',
        # Format: MM/DD/YY, HH:MM AM/PM - Name: Message
        r'(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*([^:]+):\s*(.*)',
    ]
    
    def __init__(self, your_name: str):
        """
        Args:
            your_name: Your name as it appears in WhatsApp exports (exact match)
        """
        self.your_name = your_name
        self.your_name_lower = your_name.lower()
    
    def _is_my_message(self, sender: str) -> bool:
        """Check if this message is from you."""
        return sender.lower().strip() == self.your_name_lower
    
    def _parse_line(self, line: str) -> Optional[tuple]:
        """Parse a WhatsApp message line. Returns (date, time, sender, text) or None."""
        for pattern in self.PATTERNS:
            match = re.match(pattern, line.strip())
            if match:
                return match.groups()
        return None
    
    def _detect_tone(self, text: str) -> Tone:
        """Detect tone from message content."""
        text_lower = text.lower()
        
        # WhatsApp tends to be casual/friendly
        casual_indicators = ['lol', 'haha', '😂', '🤣', 'lmao', 'omg', '!!']
        if any(ind in text_lower for ind in casual_indicators):
            return Tone.CASUAL
        
        friendly_indicators = ['❤️', '😊', '🥰', 'love', 'miss you', 'thanks']
        if any(ind in text_lower for ind in friendly_indicators):
            return Tone.FRIENDLY
        
        witty_indicators = ['😏', '🙃', '😜', '🤪']
        if any(ind in text for ind in witty_indicators):
            return Tone.WITTY
        
        return Tone.FRIENDLY  # Default for WhatsApp
    
    def _is_system_message(self, text: str) -> bool:
        """Check if this is a WhatsApp system message."""
        system_phrases = [
            'messages and calls are end-to-end encrypted',
            'created group',
            'added you',
            'left the group',
            'changed the subject',
            'changed this group',
            'deleted this message',
            '<media omitted>',
            'missed voice call',
            'missed video call',
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in system_phrases)
    
    def import_chat(self, chat_file: Path, chat_name: Optional[str] = None) -> list[Message]:
        """
        Import your messages from a WhatsApp chat export file.
        
        Args:
            chat_file: Path to the exported .txt file
            chat_name: Optional name for this chat (for tagging)
        """
        chat_file = Path(chat_file)
        chat_tag = chat_name or chat_file.stem
        
        messages = []
        all_parsed = []
        
        # Read and parse all lines
        with open(chat_file, "r", encoding="utf-8") as f:
            current_msg = None
            
            for line in f:
                parsed = self._parse_line(line)
                
                if parsed:
                    # New message starts
                    if current_msg:
                        all_parsed.append(current_msg)
                    current_msg = {
                        "date": parsed[0],
                        "time": parsed[1],
                        "sender": parsed[2].strip(),
                        "text": parsed[3].strip(),
                    }
                elif current_msg:
                    # Continuation of previous message
                    current_msg["text"] += "\n" + line.strip()
            
            if current_msg:
                all_parsed.append(current_msg)
        
        # Extract your messages with context
        for i, msg in enumerate(all_parsed):
            if not self._is_my_message(msg["sender"]):
                continue
            
            text = msg["text"].strip()
            
            # Skip system messages and very short messages
            if self._is_system_message(text) or len(text) < 3:
                continue
            
            # Get context (previous message if from someone else)
            context = None
            if i > 0:
                prev_msg = all_parsed[i - 1]
                if not self._is_my_message(prev_msg["sender"]):
                    prev_text = prev_msg["text"].strip()
                    if not self._is_system_message(prev_text):
                        context = prev_text
            
            tone = self._detect_tone(text)
            
            messages.append(Message(
                context=context,
                response=text,
                category=ContextCategory.WHATSAPP_PERSONAL,
                tone=tone,
                tags=["whatsapp", chat_tag],
            ))
        
        return messages
    
    def import_folder(self, folder: Path) -> list[Message]:
        """Import all WhatsApp exports from a folder."""
        folder = Path(folder)
        all_messages = []
        
        for txt_file in folder.glob("*.txt"):
            chat_msgs = self.import_chat(txt_file)
            all_messages.extend(chat_msgs)
            print(f"  Imported {len(chat_msgs)} messages from {txt_file.name}")
        
        return all_messages
