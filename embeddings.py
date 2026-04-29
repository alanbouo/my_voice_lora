"""Embedding and vector store management using ChromaDB."""
import json
from typing import Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import CHROMA_DIR, EMBEDDING_MODEL, NUM_EXAMPLES_TO_RETRIEVE, get_logger
from models import Message, GoldenExample, Style

logger = get_logger(__name__)


class EmbeddingStore:
    """Manages embeddings and retrieval of message examples."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self._init_collections()
    
    def _init_collections(self):
        """Initialize ChromaDB collections."""
        # Main collection for all examples
        self.examples_collection = self.client.get_or_create_collection(
            name="message_examples",
            metadata={"description": "All message examples for retrieval"}
        )
        # Golden examples get priority in retrieval
        self.golden_collection = self.client.get_or_create_collection(
            name="golden_examples",
            metadata={"description": "Curated high-quality examples"}
        )
    
    def _embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return self.embedding_model.encode(text).tolist()
    
    def add_message(self, message: Message, is_golden: bool = False):
        """Add a message to the vector store."""
        embedding_text = message.to_embedding_text()
        embedding = self._embed(embedding_text)
        
        metadata = {
            "style": message.style.value,
            "category": message.category.value if message.category else "",
            "tone": message.tone.value if message.tone else "",
            "tags": json.dumps(message.tags),
            "context": message.context or "",
            "response": message.response,
            "is_golden": is_golden,
        }
        
        # Add to main collection
        self.examples_collection.upsert(
            ids=[message.id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[embedding_text]
        )
        
        # Also add to golden collection if promoted
        if is_golden:
            self.golden_collection.upsert(
                ids=[message.id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[embedding_text]
            )
    
    def add_messages_batch(self, messages: list[Message]):
        """Add multiple messages at once."""
        if not messages:
            return
        
        ids = [m.id for m in messages]
        embeddings = [self._embed(m.to_embedding_text()) for m in messages]
        metadatas = [
            {
                "style": m.style.value,
                "category": m.category.value if m.category else "",
                "tone": m.tone.value if m.tone else "",
                "tags": json.dumps(m.tags),
                "context": m.context or "",
                "response": m.response,
                "is_golden": False,
            }
            for m in messages
        ]
        documents = [m.to_embedding_text() for m in messages]
        
        self.examples_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        logger.info("Added %d messages to store", len(messages))
    
    def promote_to_golden(self, message_id: str):
        """Promote an existing message to golden status."""
        # Get from main collection
        result = self.examples_collection.get(
            ids=[message_id],
            include=["embeddings", "metadatas", "documents"]
        )
        
        if not result["ids"]:
            raise ValueError(f"Message {message_id} not found")
        
        # Update metadata
        metadata = result["metadatas"][0]
        metadata["is_golden"] = True
        
        # Update in main collection
        self.examples_collection.update(
            ids=[message_id],
            metadatas=[metadata]
        )
        
        # Add to golden collection
        self.golden_collection.upsert(
            ids=[message_id],
            embeddings=result["embeddings"],
            metadatas=[metadata],
            documents=result["documents"]
        )
        logger.info("Promoted message %s to golden", message_id)
    
    def retrieve_examples(
        self,
        query: str,
        style: Optional[Style] = None,
        n_results: int = NUM_EXAMPLES_TO_RETRIEVE,
        prioritize_golden: bool = True,
    ) -> list[dict]:
        """Retrieve relevant examples for a query."""
        query_embedding = self._embed(query)
        
        # Build filter for style
        where_filter = None
        if style:
            where_filter = {"style": style.value}
        
        results = []
        
        # First, get golden examples if prioritizing
        if prioritize_golden:
            golden_count = self.golden_collection.count()
            if golden_count > 0:
                n_golden = min(n_results // 2 + 1, golden_count)
                golden_results = self.golden_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_golden,
                    where=where_filter,
                    include=["metadatas", "documents", "distances"]
                )
                
                for i, doc_id in enumerate(golden_results["ids"][0]):
                    results.append({
                        "id": doc_id,
                        "metadata": golden_results["metadatas"][0][i],
                        "document": golden_results["documents"][0][i],
                        "distance": golden_results["distances"][0][i],
                        "is_golden": True,
                    })
        
        # Get remaining from main collection
        remaining = n_results - len(results)
        if remaining > 0:
            # Exclude already retrieved golden examples
            existing_ids = {r["id"] for r in results}
            
            main_results = self.examples_collection.query(
                query_embeddings=[query_embedding],
                n_results=remaining + len(existing_ids),  # Get extra to filter
                where=where_filter,
                include=["metadatas", "documents", "distances"]
            )
            
            for i, doc_id in enumerate(main_results["ids"][0]):
                if doc_id not in existing_ids and len(results) < n_results:
                    results.append({
                        "id": doc_id,
                        "metadata": main_results["metadatas"][0][i],
                        "document": main_results["documents"][0][i],
                        "distance": main_results["distances"][0][i],
                        "is_golden": main_results["metadatas"][0][i].get("is_golden", False),
                    })
        
        # Sort by distance (lower is better)
        results.sort(key=lambda x: x["distance"])
        
        return results[:n_results]
    
    def get_stats(self) -> dict:
        """Get statistics about the collections."""
        return {
            "total_examples": self.examples_collection.count(),
            "golden_examples": self.golden_collection.count(),
        }
    
    def delete_message(self, message_id: str):
        """Remove a message from all collections."""
        self.examples_collection.delete(ids=[message_id])
        try:
            self.golden_collection.delete(ids=[message_id])
        except:
            pass  # May not exist in golden
