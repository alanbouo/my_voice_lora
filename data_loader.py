"""Data loading utilities for importing your message history."""
import json
import csv
from pathlib import Path
from typing import Optional
from datetime import datetime

from config import EXAMPLES_DIR
from models import Message, ContextCategory, Tone
from embeddings import EmbeddingStore


class DataLoader:
    """Load and import message data from various formats."""
    
    def __init__(self, embedding_store: Optional[EmbeddingStore] = None):
        self.store = embedding_store or EmbeddingStore()
    
    def load_from_json(self, filepath: Path) -> list[Message]:
        """
        Load messages from JSON file.
        
        Expected format:
        [
            {
                "context": "optional context/prompt",
                "response": "your actual message",
                "category": "email_professional|linkedin_post|slack_casual|whatsapp_personal|twitter_post",
                "tone": "formal|casual|friendly|professional|witty",
                "tags": ["optional", "tags"]
            }
        ]
        """
        data = json.loads(filepath.read_text(encoding="utf-8"))
        messages = []
        
        for item in data:
            try:
                message = Message(
                    context=item.get("context"),
                    response=item["response"],
                    category=ContextCategory(item["category"]),
                    tone=Tone(item.get("tone", "casual")),
                    tags=item.get("tags", []),
                )
                messages.append(message)
            except Exception as e:
                print(f"Skipping invalid item: {e}")
        
        return messages
    
    def load_from_csv(self, filepath: Path) -> list[Message]:
        """
        Load messages from CSV file.
        
        Expected columns: context, response, category, tone, tags (comma-separated)
        """
        messages = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    tags = []
                    if row.get("tags"):
                        tags = [t.strip() for t in row["tags"].split(",")]
                    
                    message = Message(
                        context=row.get("context") or None,
                        response=row["response"],
                        category=ContextCategory(row["category"]),
                        tone=Tone(row.get("tone", "casual")),
                        tags=tags,
                    )
                    messages.append(message)
                except Exception as e:
                    print(f"Skipping invalid row: {e}")
        
        return messages
    
    def load_from_text(
        self,
        filepath: Path,
        category: ContextCategory,
        tone: Tone = Tone.CASUAL,
    ) -> list[Message]:
        """
        Load messages from plain text file (one message per line).
        """
        messages = []
        lines = filepath.read_text(encoding="utf-8").strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                message = Message(
                    response=line,
                    category=category,
                    tone=tone,
                )
                messages.append(message)
        
        return messages
    
    def import_to_store(self, messages: list[Message]) -> int:
        """Import messages to the vector store."""
        if not messages:
            return 0
        
        self.store.add_messages_batch(messages)
        return len(messages)
    
    def load_and_import_directory(self, directory: Optional[Path] = None) -> dict:
        """
        Load all data files from a directory.
        
        Expects files named: {category}.json, {category}.csv, or {category}.txt
        """
        directory = directory or EXAMPLES_DIR
        stats = {"loaded": 0, "files": []}
        
        for filepath in directory.iterdir():
            if filepath.is_file():
                messages = []
                
                if filepath.suffix == ".json":
                    messages = self.load_from_json(filepath)
                elif filepath.suffix == ".csv":
                    messages = self.load_from_csv(filepath)
                elif filepath.suffix == ".txt":
                    # Try to infer category from filename
                    category_name = filepath.stem.lower()
                    category_map = {
                        "email": ContextCategory.EMAIL_PROFESSIONAL,
                        "linkedin": ContextCategory.LINKEDIN_POST,
                        "slack": ContextCategory.SLACK_CASUAL,
                        "whatsapp": ContextCategory.WHATSAPP_PERSONAL,
                        "twitter": ContextCategory.TWITTER_POST,
                    }
                    category = category_map.get(category_name, ContextCategory.SLACK_CASUAL)
                    messages = self.load_from_text(filepath, category)
                
                if messages:
                    self.import_to_store(messages)
                    stats["loaded"] += len(messages)
                    stats["files"].append({
                        "file": filepath.name,
                        "count": len(messages),
                    })
        
        return stats


def create_sample_data():
    """Create sample data files to demonstrate the expected format."""
    EXAMPLES_DIR.mkdir(exist_ok=True)
    
    # Sample JSON
    sample_json = [
        {
            "context": "Following up on our meeting",
            "response": "Hi Sarah,\n\nGreat chatting with you earlier! I've attached the proposal we discussed. Let me know if you have any questions.\n\nBest,\n[Name]",
            "category": "email_professional",
            "tone": "professional",
            "tags": ["followup", "meeting"]
        },
        {
            "context": "Sharing a career insight",
            "response": "Hot take: The best career advice I ever got was 'be so good they can't ignore you.'\n\nNot 'network more' or 'get an MBA.'\n\nJust: master your craft.\n\n3 years later, opportunities find me. 🎯\n\n#CareerAdvice #Growth",
            "category": "linkedin_post",
            "tone": "professional",
            "tags": ["advice", "engagement"]
        },
        {
            "context": "Quick work update",
            "response": "hey! just pushed the fix, should be good now 👍 lmk if you see any issues",
            "category": "slack_casual",
            "tone": "casual",
            "tags": ["work", "quick"]
        },
        {
            "context": "Making weekend plans",
            "response": "yooo saturday works! thinking we grab brunch then hit that new coffee place? ☕",
            "category": "whatsapp_personal",
            "tone": "friendly",
            "tags": ["plans", "friends"]
        },
        {
            "context": "Sharing a tech opinion",
            "response": "unpopular opinion: most 'AI tools' in 2026 are just fancy autocomplete\n\nthe real magic is when AI actually understands your intent, not just your words",
            "category": "twitter_post",
            "tone": "witty",
            "tags": ["tech", "opinion"]
        },
    ]
    
    sample_file = EXAMPLES_DIR / "sample_messages.json"
    sample_file.write_text(json.dumps(sample_json, indent=2))
    
    # Sample CSV template
    csv_template = EXAMPLES_DIR / "template.csv"
    csv_template.write_text("context,response,category,tone,tags\n")
    
    return {
        "json_sample": str(sample_file),
        "csv_template": str(csv_template),
    }
