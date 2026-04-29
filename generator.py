"""LLM generation with RAG-based few-shot prompting."""
from typing import Optional
import ollama

from config import LLM_MODEL, LLM_BASE_URL, get_logger

logger = get_logger(__name__)
from models import GenerationRequest, GenerationResult, Style
from embeddings import EmbeddingStore


# System prompts per style
STYLE_PROMPTS = {
    Style.EMAIL_FORMEL: """Tu m'aides à écrire des emails professionnels/formels.
Respecte exactement mon style d'écriture basé sur les exemples fournis.
Traits clés : vocabulaire, structure des phrases, formules de salutation/conclusion, niveau de formalité.""",

    Style.EMAIL_DECONTRACTE: """Tu m'aides à écrire des emails décontractés/personnels.
Respecte mon style personnel : ton amical, expressions familières, structure détendue.
Garde l'authenticité de ma façon de communiquer avec mes proches.""",

    Style.MESSAGE_PERSO: """Tu m'aides à écrire des messages personnels (WhatsApp/SMS).
Respecte mon style de textos : abréviations, emojis, humour, chaleur.
Sois authentique à ma façon de texter.""",

    Style.SLACK_EQUIPE: """Tu m'aides à écrire des messages Slack pour mes collègues.
Respecte mon style casual au travail : brièveté, emojis, humour, ton informel.
Garde ça naturel et conversationnel.""",

    Style.LINKEDIN: """Tu m'aides à écrire des posts LinkedIn.
Respecte mon style : structure des idées, longueur typique, hashtags, ton professionnel.
Maintiens ma voix tout en restant engageant.""",

    Style.TWITTER: """Tu m'aides à écrire des tweets.
Respecte ma voix Twitter : accroches, style de thread, hashtags, engagement.
Garde ma personnalité tout en étant concis.""",
}


class StyleGenerator:
    """Generates text in your personal style using RAG."""
    
    def __init__(self, embedding_store: Optional[EmbeddingStore] = None):
        self.store = embedding_store or EmbeddingStore()
        self.client = ollama.Client(host=LLM_BASE_URL)
    
    def _build_prompt(
        self,
        request: GenerationRequest,
        examples: list[dict],
    ) -> tuple[str, str]:
        """Build system and user prompts with retrieved examples."""
        
        # System prompt
        system_parts = [
            STYLE_PROMPTS.get(request.style, STYLE_PROMPTS[Style.EMAIL_DECONTRACTE]),
            "",
            "CRITIQUE: Écris dans la MÊM LANGUE que les exemples fournis. Si les exemples sont en français, écris en français.",
            "",
            "IMPORTANT: Écris UNIQUEMENT le message lui-même. Pas d'explications, pas de 'Voici un brouillon', juste le message tel que je l'écrirais.",
        ]
        system_prompt = "\n".join(system_parts)
        
        # User prompt with examples
        user_parts = ["Here are examples of how I write in this style:", ""]
        
        for i, ex in enumerate(examples, 1):
            metadata = ex["metadata"]
            golden_marker = " ⭐" if ex.get("is_golden") else ""
            user_parts.append(f"--- Example {i}{golden_marker} ---")
            if metadata.get("context"):
                user_parts.append(f"Context: {metadata['context']}")
            user_parts.append(f"My message: {metadata['response']}")
            user_parts.append("")
        
        user_parts.append("---")
        user_parts.append("")
        user_parts.append("Now write a message for me:")
        user_parts.append(f"Task: {request.prompt}")
        
        if request.additional_context:
            user_parts.append(f"Additional context: {request.additional_context}")
        
        if request.max_length:
            user_parts.append(f"Target length: approximately {request.max_length} characters")
        
        user_parts.append("")
        user_parts.append("Write my message:")
        
        user_prompt = "\n".join(user_parts)
        
        return system_prompt, user_prompt
    
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate text in your style based on the request."""
        
        logger.info("Generating style=%s prompt=%.60s", request.style.value, request.prompt)
        # Retrieve relevant examples
        query = f"{request.style.value} {request.prompt}"
        examples = self.store.retrieve_examples(
            query=query,
            style=request.style,
        )
        
        # Build prompts
        system_prompt, user_prompt = self._build_prompt(request, examples)
        
        # Generate with LLM
        try:
            response = self.client.chat(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            )
        except ollama.ResponseError as e:
            logger.error("Ollama API error: %s", e)
            if e.status_code == 404:
                raise RuntimeError(
                    f"Model '{LLM_MODEL}' not found. Run: ollama pull {LLM_MODEL}"
                ) from e
            raise RuntimeError(f"Ollama API error: {e}") from e
        except Exception as e:
            logger.error("Ollama connection error: %s", e)
            if "connect" in str(e).lower():
                raise RuntimeError(
                    f"Cannot connect to Ollama at {LLM_BASE_URL}. Is it running? Try: ollama serve"
                ) from e
            raise

        generated_text = response["message"]["content"].strip()
        generated_text = self._clean_output(generated_text)
        logger.info("Generated %d chars from %d examples", len(generated_text), len(examples))
        
        return GenerationResult(
            request=request,
            generated_text=generated_text,
            retrieved_examples=[ex["metadata"]["response"][:100] for ex in examples],
        )
    
    def _clean_output(self, text: str) -> str:
        """Remove common LLM artifacts from output."""
        # Remove common preambles
        prefixes_to_remove = [
            "Here's a draft:",
            "Here's the message:",
            "Here you go:",
            "Sure, here's",
            "Draft:",
        ]
        
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        
        # Remove quotes if entire message is quoted
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        return text.strip()
    
    def regenerate(self, result: GenerationResult, feedback: str = "") -> GenerationResult:
        """Regenerate with optional feedback for adjustment."""
        # Modify request based on feedback
        new_request = result.request.model_copy()
        
        if feedback:
            if new_request.additional_context:
                new_request.additional_context += f"\n\nAdjustment: {feedback}"
            else:
                new_request.additional_context = f"Adjustment: {feedback}"
        
        return self.generate(new_request)
