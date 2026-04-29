"""Import messages from Slack JSON exports."""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
import re
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models import Message, ContextCategory, Tone


class SlackImporter:
    """
    Import your messages from Slack export.
    
    How to export from Slack:
    1. Go to your Slack workspace settings
    2. Settings & administration > Workspace settings > Import/Export Data
    3. Export your workspace data (you'll get a ZIP file)
    4. Extract the ZIP - each channel has a folder with JSON files
    """
    
    def __init__(self, your_user_id: Optional[str] = None, your_username: Optional[str] = None):
        """
        Args:
            your_user_id: Your Slack user ID (e.g., "U01234567")
            your_username: Your Slack username/display name (fallback if ID not provided)
        """
        self.your_user_id = your_user_id
        self.your_username = your_username.lower() if your_username else None
    
    def _is_my_message(self, msg: dict) -> bool:
        """Check if this message is from you."""
        if self.your_user_id and msg.get("user") == self.your_user_id:
            return True
        if self.your_username:
            username = msg.get("user_profile", {}).get("display_name", "").lower()
            real_name = msg.get("user_profile", {}).get("real_name", "").lower()
            if self.your_username in username or self.your_username in real_name:
                return True
        return False
    
    def _clean_message(self, text: str) -> str:
        """Clean Slack message formatting."""
        # Remove user mentions like <@U01234567>
        text = re.sub(r'<@[A-Z0-9]+>', '@someone', text)
        # Remove channel mentions like <#C01234567|channel-name>
        text = re.sub(r'<#[A-Z0-9]+\|([^>]+)>', r'#\1', text)
        # Remove URLs but keep display text
        text = re.sub(r'<(https?://[^|>]+)\|([^>]+)>', r'\2', text)
        text = re.sub(r'<(https?://[^>]+)>', r'\1', text)
        # Clean up extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _get_context(self, messages: list, current_idx: int) -> Optional[str]:
        """Get the message being replied to (if any)."""
        msg = messages[current_idx]
        
        # Check if it's a thread reply
        if msg.get("thread_ts") and msg.get("thread_ts") != msg.get("ts"):
            # Find parent message
            parent_ts = msg.get("thread_ts")
            for m in messages:
                if m.get("ts") == parent_ts:
                    return self._clean_message(m.get("text", ""))
        
        # Otherwise, check previous message in channel
        if current_idx > 0:
            prev_msg = messages[current_idx - 1]
            if not self._is_my_message(prev_msg):
                return self._clean_message(prev_msg.get("text", ""))
        
        return None
    
    def _detect_tone(self, text: str) -> Tone:
        """Detect tone from message content."""
        text_lower = text.lower()
        
        # Check for casual indicators
        casual_indicators = ['lol', 'haha', '😂', '🤣', 'lmao', 'omg', 'tbh', 'ngl']
        if any(ind in text_lower for ind in casual_indicators):
            return Tone.CASUAL
        
        # Check for witty/humor
        if '😏' in text or '🙃' in text or '/s' in text_lower:
            return Tone.WITTY
        
        # Check for friendly
        friendly_indicators = ['thanks!', 'thank you!', '🙏', '❤️', 'awesome', 'great job']
        if any(ind in text_lower for ind in friendly_indicators):
            return Tone.FRIENDLY
        
        # Default to casual for Slack
        return Tone.CASUAL
    
    def import_channel(self, channel_folder: Path) -> list[Message]:
        """Import all your messages from a single channel folder."""
        messages = []
        
        # Load all JSON files in the channel folder
        all_msgs = []
        for json_file in sorted(channel_folder.glob("*.json")):
            with open(json_file, "r", encoding="utf-8") as f:
                day_msgs = json.load(f)
                all_msgs.extend(day_msgs)
        
        # Sort by timestamp
        all_msgs.sort(key=lambda x: float(x.get("ts", 0)))
        
        # Extract your messages
        for i, msg in enumerate(all_msgs):
            if not self._is_my_message(msg):
                continue
            
            text = msg.get("text", "")
            if not text or len(text) < 5:  # Skip very short messages
                continue
            
            clean_text = self._clean_message(text)
            if not clean_text:
                continue
            
            context = self._get_context(all_msgs, i)
            tone = self._detect_tone(clean_text)
            
            messages.append(Message(
                context=context,
                response=clean_text,
                category=ContextCategory.SLACK_CASUAL,
                tone=tone,
                tags=["slack", channel_folder.name],
            ))
        
        return messages
    
    def import_export_folder(self, export_path: Path, channels: Optional[list[str]] = None) -> list[Message]:
        """
        Import messages from a Slack export folder.
        
        Args:
            export_path: Path to extracted Slack export folder
            channels: Optional list of channel names to import (imports all if None)
        """
        export_path = Path(export_path)
        all_messages = []
        
        for item in export_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if channels and item.name not in channels:
                    continue
                
                channel_msgs = self.import_channel(item)
                all_messages.extend(channel_msgs)
                print(f"  Imported {len(channel_msgs)} messages from #{item.name}")
        
        return all_messages
    
    def find_your_user_id(self, export_path: Path) -> dict:
        """Helper to find your user ID from the export."""
        users_file = Path(export_path) / "users.json"
        if users_file.exists():
            with open(users_file, "r", encoding="utf-8") as f:
                users = json.load(f)
                return {u.get("name"): u.get("id") for u in users}
        return {}
