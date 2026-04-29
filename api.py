"""FastAPI backend for the writing assistant."""
import os
import yaml
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import Style, ContextCategory, Tone, GenerationRequest
from embeddings import EmbeddingStore
from generator import StyleGenerator
from feedback import FeedbackManager

app = FastAPI(title="Personal Writing Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://voicelora.alanbouo.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loaded singletons
_store: Optional[EmbeddingStore] = None
_generator: Optional[StyleGenerator] = None
_feedback_mgr: Optional[FeedbackManager] = None


def get_store() -> EmbeddingStore:
    global _store
    if _store is None:
        _store = EmbeddingStore()
    return _store


def get_generator() -> StyleGenerator:
    global _generator
    if _generator is None:
        _generator = StyleGenerator(get_store())
    return _generator


def get_feedback_mgr() -> FeedbackManager:
    global _feedback_mgr
    if _feedback_mgr is None:
        _feedback_mgr = FeedbackManager(get_store())
    return _feedback_mgr


# === Request/Response Models ===

class GenerateRequest(BaseModel):
    prompt: str
    style: str = "email_decontracte"
    context: Optional[str] = None


class GenerateResponse(BaseModel):
    text: str
    generation_id: str
    examples_used: int
    style: str


class RatingRequest(BaseModel):
    generation_id: str
    rating: int  # 1 = thumbs down, 5 = thumbs up
    feedback: Optional[str] = None  # Modification instructions


class ExampleResponse(BaseModel):
    id: str
    response: str
    context: Optional[str]
    style: str
    is_golden: bool


class StatsResponse(BaseModel):
    total_examples: int
    golden_examples: int
    total_ratings: int
    average_rating: float


class ConfigResponse(BaseModel):
    your_name: str
    your_emails: list[str]
    slack_folder: Optional[str]
    whatsapp_folder: Optional[str]
    email_folder: Optional[str]


class ImportRequest(BaseModel):
    source: str  # "slack", "whatsapp", "email"


class ImportStatus(BaseModel):
    status: str
    message: str
    count: int = 0


# === Endpoints ===

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    store = get_store()
    feedback_mgr = get_feedback_mgr()
    
    store_stats = store.get_stats()
    feedback_stats = feedback_mgr.get_feedback_stats()
    
    return StatsResponse(
        total_examples=store_stats["total_examples"],
        golden_examples=store_stats["golden_examples"],
        total_ratings=feedback_stats["total_ratings"],
        average_rating=feedback_stats["average_rating"],
    )


@app.get("/api/styles")
def get_styles():
    """Get available writing styles."""
    labels = {
        "email_formel": "Email formel",
        "email_decontracte": "Email décontracté",
        "message_perso": "Message perso",
        "slack_equipe": "Slack équipe",
        "linkedin": "LinkedIn",
        "twitter": "Twitter",
    }
    return [{"value": s.value, "label": labels.get(s.value, s.value)} for s in Style]


# Keep old endpoints for backward compatibility
@app.get("/api/categories")
def get_categories():
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} 
            for c in ContextCategory]


@app.get("/api/tones")
def get_tones():
    return [{"value": t.value, "label": t.value.title()} for t in Tone]


@app.post("/api/generate", response_model=GenerateResponse)
def generate_text(req: GenerateRequest):
    try:
        style = Style(req.style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid style: {req.style}")
    
    generator = get_generator()
    
    request = GenerationRequest(
        prompt=req.prompt,
        style=style,
        additional_context=req.context,
    )
    
    result = generator.generate(request)
    
    return GenerateResponse(
        text=result.generated_text,
        generation_id=result.id,
        examples_used=len(result.retrieved_examples),
        style=req.style,
    )


@app.post("/api/rate")
def rate_generation(req: RatingRequest):
    if not 1 <= req.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    
    feedback_mgr = get_feedback_mgr()
    feedback_mgr.record_rating(req.generation_id, req.rating, req.feedback)
    
    return {"status": "ok", "message": f"Rated {req.rating}/5"}


@app.get("/api/examples", response_model=list[ExampleResponse])
def get_examples(
    style: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    golden_only: bool = False,
):
    store = get_store()
    results = store.examples_collection.get(include=["metadatas"])
    
    examples = []
    for i, id_ in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        
        # Support both old category and new style
        item_style = meta.get("style") or meta.get("category", "")
        if style and item_style != style:
            continue
        if golden_only and not meta.get("is_golden"):
            continue
        
        examples.append(ExampleResponse(
            id=id_,
            response=meta.get("response", "")[:500],
            context=meta.get("context", ""),
            style=item_style,
            is_golden=meta.get("is_golden", False),
        ))
    
    return examples[offset:offset + limit]


@app.post("/api/examples/{example_id}/golden")
def toggle_golden(example_id: str, is_golden: bool = True):
    store = get_store()
    feedback_mgr = get_feedback_mgr()
    
    if is_golden:
        feedback_mgr.promote_to_golden(example_id)
    
    return {"status": "ok", "is_golden": is_golden}


@app.delete("/api/examples/{example_id}")
def delete_example(example_id: str):
    store = get_store()
    store.examples_collection.delete(ids=[example_id])
    return {"status": "ok"}


@app.get("/api/config", response_model=ConfigResponse)
def get_config():
    config_path = Path("my_config.yaml")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Config not found")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    return ConfigResponse(
        your_name=config.get("your_name", ""),
        your_emails=config.get("your_emails", []),
        slack_folder=config.get("slack_folder"),
        whatsapp_folder=config.get("whatsapp_folder"),
        email_folder=config.get("email_folder"),
    )


@app.post("/api/import/{source}", response_model=ImportStatus)
def import_data(source: str, background_tasks: BackgroundTasks):
    valid_sources = ["slack", "whatsapp", "email"]
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Source must be one of {valid_sources}")
    
    # For now, run synchronously (could be made async with background tasks)
    config_path = Path("my_config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    store = get_store()
    count = 0
    
    if source == "email":
        from importers.email_importer import EmailImporter
        folder = config.get("email_folder")
        if not folder or not Path(folder).exists():
            raise HTTPException(status_code=400, detail="Email folder not configured")
        
        importer = EmailImporter(config.get("your_emails", []))
        messages = importer.import_from_eml_folder(folder)
        store.add_messages_batch(messages)
        count = len(messages)
    
    elif source == "slack":
        from importers.slack_importer import SlackImporter
        folder = config.get("slack_folder")
        if not folder or not Path(folder).exists():
            raise HTTPException(status_code=400, detail="Slack folder not configured")
        
        importer = SlackImporter(
            config.get("slack_user_id", ""),
            config.get("slack_username", ""),
        )
        messages = importer.import_from_directory(folder)
        store.add_messages_batch(messages)
        count = len(messages)
    
    elif source == "whatsapp":
        from importers.whatsapp_importer import WhatsAppImporter
        folder = config.get("whatsapp_folder")
        if not folder or not Path(folder).exists():
            raise HTTPException(status_code=400, detail="WhatsApp folder not configured")
        
        importer = WhatsAppImporter(config.get("your_name", ""))
        for file in Path(folder).glob("*.txt"):
            messages = importer.import_from_file(str(file))
            store.add_messages_batch(messages)
            count += len(messages)
    
    return ImportStatus(
        status="ok",
        message=f"Imported {count} messages from {source}",
        count=count,
    )


@app.post("/api/clear")
def clear_database():
    store = get_store()
    try:
        store.client.delete_collection("message_examples")
    except:
        pass
    try:
        store.client.delete_collection("golden_examples")
    except:
        pass
    
    # Reset singleton
    global _store, _generator, _feedback_mgr
    _store = None
    _generator = None
    _feedback_mgr = None
    
    return {"status": "ok", "message": "Database cleared"}


@app.post("/api/export/finetune")
def export_for_finetuning():
    """Export golden examples in JSONL format for fine-tuning."""
    import json
    
    store = get_store()
    results = store.examples_collection.get(include=["metadatas"])
    
    exports = []
    for i, id_ in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        if meta.get("is_golden"):
            exports.append({
                "instruction": meta.get("context", ""),
                "output": meta.get("response", ""),
                "category": meta.get("category", ""),
                "tone": meta.get("tone", ""),
            })
    
    # Save to file
    export_path = Path("exports/finetune_data.jsonl")
    export_path.parent.mkdir(exist_ok=True)
    
    with open(export_path, "w", encoding="utf-8") as f:
        for item in exports:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    return {
        "status": "ok",
        "count": len(exports),
        "path": str(export_path),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
