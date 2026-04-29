"""Feedback and curation system for improving examples."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import GOLDEN_EXAMPLES_FILE, FEEDBACK_LOG_FILE, DATA_DIR, get_logger
from models import Message, GoldenExample, GenerationResult, Style
from embeddings import EmbeddingStore

logger = get_logger(__name__)


class FeedbackManager:
    """Manages feedback collection and example curation."""
    
    def __init__(self, embedding_store: Optional[EmbeddingStore] = None):
        self.store = embedding_store or EmbeddingStore()
        self._ensure_files()
    
    def _ensure_files(self):
        """Ensure feedback files exist."""
        DATA_DIR.mkdir(exist_ok=True)
        
        if not GOLDEN_EXAMPLES_FILE.exists():
            GOLDEN_EXAMPLES_FILE.write_text("[]")
        
        if not FEEDBACK_LOG_FILE.exists():
            FEEDBACK_LOG_FILE.write_text("[]")
    
    def _load_json(self, path: Path) -> list:
        """Load JSON file."""
        try:
            return json.loads(path.read_text())
        except:
            return []
    
    def _save_json(self, path: Path, data: list):
        """Save JSON file."""
        path.write_text(json.dumps(data, indent=2, default=str))
    
    def rate_generation(
        self,
        result: GenerationResult,
        rating: int,
        feedback: Optional[str] = None,
    ) -> GenerationResult:
        """Rate a generated output and optionally promote to golden."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        result.rating = rating
        result.feedback = feedback
        logger.info("Rated generation %s: %d/5", result.id, rating)

        # Log the feedback
        feedback_log = self._load_json(FEEDBACK_LOG_FILE)
        feedback_log.append({
            "id": result.id,
            "request": result.request.model_dump(),
            "generated_text": result.generated_text,
            "rating": rating,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_json(FEEDBACK_LOG_FILE, feedback_log)
        
        # If highly rated (4-5), offer to promote to golden
        if rating >= 4:
            self._promote_generation_to_golden(result)
        
        return result
    
    def _promote_generation_to_golden(self, result: GenerationResult):
        """Promote a highly-rated generation to golden examples."""
        # Create a message from the generation
        message = Message(
            id=f"gen_{result.id}",
            context=result.request.prompt,
            response=result.generated_text,
            style=result.request.style,
            tags=["generated", "promoted"],
        )

        # Add to vector store as golden
        self.store.add_message(message, is_golden=True)
        logger.info("Promoted generation %s to golden (style=%s)", result.id, result.request.style.value)
        
        # Also save to golden examples file
        golden_examples = self._load_json(GOLDEN_EXAMPLES_FILE)
        golden_example = GoldenExample(
            message=message,
            rating=result.rating,
            feedback_note=result.feedback,
        )
        golden_examples.append(golden_example.model_dump())
        self._save_json(GOLDEN_EXAMPLES_FILE, golden_examples)
    
    def promote_existing_message(self, message_id: str, rating: int = 5):
        """Promote an existing message in the store to golden status."""
        self.store.promote_to_golden(message_id)
        
        # Log the promotion
        feedback_log = self._load_json(FEEDBACK_LOG_FILE)
        feedback_log.append({
            "action": "promote_to_golden",
            "message_id": message_id,
            "rating": rating,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_json(FEEDBACK_LOG_FILE, feedback_log)
    
    def add_manual_golden_example(
        self,
        response: str,
        style: Style,
        context: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ):
        """Manually add a golden example (e.g., a real message you wrote)."""
        message = Message(
            context=context,
            response=response,
            style=style,
            tags=tags or ["manual", "golden"],
        )
        
        self.store.add_message(message, is_golden=True)
        logger.info("Added manual golden example %s (style=%s)", message.id, style.value)

        # Save to file
        golden_examples = self._load_json(GOLDEN_EXAMPLES_FILE)
        golden_example = GoldenExample(message=message, rating=5)
        golden_examples.append(golden_example.model_dump())
        self._save_json(GOLDEN_EXAMPLES_FILE, golden_examples)

        return message
    
    def get_feedback_stats(self) -> dict:
        """Get statistics about feedback and curation."""
        feedback_log = self._load_json(FEEDBACK_LOG_FILE)
        golden_examples = self._load_json(GOLDEN_EXAMPLES_FILE)
        
        ratings = [f["rating"] for f in feedback_log if "rating" in f]
        
        return {
            "total_ratings": len(ratings),
            "average_rating": sum(ratings) / len(ratings) if ratings else 0,
            "golden_examples": len(golden_examples),
            "rating_distribution": {
                i: ratings.count(i) for i in range(1, 6)
            },
        }
    
    def get_low_rated_patterns(self) -> list[dict]:
        """Analyze low-rated generations to identify failure patterns."""
        feedback_log = self._load_json(FEEDBACK_LOG_FILE)
        
        low_rated = [
            f for f in feedback_log 
            if f.get("rating", 0) <= 2
        ]
        
        return low_rated
