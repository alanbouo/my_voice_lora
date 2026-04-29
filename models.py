"""Data models for messages and examples."""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Style(str, Enum):
    """Unified style combining context and tone."""
    EMAIL_FORMEL = "email_formel"          # Email professionnel/formel
    EMAIL_DECONTRACTE = "email_decontracte"  # Email personnel/décontracté
    MESSAGE_PERSO = "message_perso"        # WhatsApp/SMS personnel
    SLACK_EQUIPE = "slack_equipe"          # Slack avec collègues
    LINKEDIN = "linkedin"                  # Post LinkedIn
    TWITTER = "twitter"                    # Tweet


# Keep old enums for backward compatibility during migration
class ContextCategory(str, Enum):
    EMAIL_PROFESSIONAL = "email_professional"
    LINKEDIN_POST = "linkedin_post"
    SLACK_CASUAL = "slack_casual"
    WHATSAPP_PERSONAL = "whatsapp_personal"
    TWITTER_POST = "twitter_post"


class Tone(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    WITTY = "witty"


def category_to_style(category: ContextCategory, tone: Tone = None) -> Style:
    """Convert old category+tone to new unified style."""
    mapping = {
        ContextCategory.EMAIL_PROFESSIONAL: Style.EMAIL_FORMEL,
        ContextCategory.WHATSAPP_PERSONAL: Style.MESSAGE_PERSO,
        ContextCategory.SLACK_CASUAL: Style.SLACK_EQUIPE,
        ContextCategory.LINKEDIN_POST: Style.LINKEDIN,
        ContextCategory.TWITTER_POST: Style.TWITTER,
    }
    return mapping.get(category, Style.EMAIL_DECONTRACTE)


class Message(BaseModel):
    """A single message example for training/retrieval."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    context: Optional[str] = None  # Conversation context / prompt
    response: str  # Your actual message/response
    style: Style = Style.EMAIL_DECONTRACTE
    # Keep for backward compat
    category: Optional[ContextCategory] = None
    tone: Optional[Tone] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    def to_embedding_text(self) -> str:
        """Create text representation for embedding."""
        parts = [f"Style: {self.style.value}"]
        if self.context:
            parts.append(f"Context: {self.context}")
        parts.append(f"Response: {self.response}")
        return "\n".join(parts)
    
    def to_few_shot_example(self) -> str:
        """Format as a few-shot example for the prompt."""
        if self.context:
            return f"[Context: {self.context}]\nYour response: {self.response}"
        return f"Your response: {self.response}"


class GoldenExample(BaseModel):
    """A curated high-quality example promoted via feedback."""
    message: Message
    rating: int = Field(ge=1, le=5, default=5)
    feedback_note: Optional[str] = None
    promoted_at: datetime = Field(default_factory=datetime.now)


class GenerationRequest(BaseModel):
    """Request for generating a new message."""
    prompt: str  # What you want to write about
    style: Style = Style.EMAIL_DECONTRACTE
    additional_context: Optional[str] = None
    max_length: Optional[int] = None  # Approximate target length


class GenerationResult(BaseModel):
    """Result of a generation with metadata for feedback."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    request: GenerationRequest
    generated_text: str
    retrieved_examples: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    rating: Optional[int] = None
    feedback: Optional[str] = None
