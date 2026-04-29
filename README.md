# Personal Writing Style Assistant (Phase 1: RAG + Example Curation)

A local AI writing assistant that mimics your personal writing style using RAG-based few-shot learning with feedback-driven example curation.

## Features

- **Style-aware generation** across 5 contexts: professional emails, LinkedIn posts, Slack messages, WhatsApp chats, Twitter/X posts
- **Tone control**: formal, casual, friendly, professional, witty
- **Feedback curation**: Rate outputs → good ones become "golden" examples that improve future generations
- **Fully local**: Uses Ollama for LLM inference, ChromaDB for vector storage, no data leaves your machine

## Prerequisites

1. **Python 3.10+**
2. **Ollama** installed and running with a model:
   ```bash
   # Install Ollama from https://ollama.ai
   ollama pull llama3.1:8b
   # Or use a smaller model:
   ollama pull qwen2.5:7b
   ```

## Installation

```bash
cd my_voice_lora
pip install -r requirements.txt
```

## Quick Start

### 1. Load sample data
```bash
python cli.py load-samples
```

### 2. Generate in your style
```bash
# Simple generation
python cli.py generate "follow up on our meeting about the Q2 roadmap" -c email_professional -t professional

# Interactive mode
python cli.py interactive
```

### 3. Add your own examples
Create a JSON file in `data/examples/` with your real messages:

```json
[
  {
    "context": "Following up on project discussion",
    "response": "Hey! Just wanted to check in on that thing we talked about. Any updates?",
    "category": "slack_casual",
    "tone": "casual",
    "tags": ["followup"]
  }
]
```

Then import:
```bash
python cli.py import-data
```

### 4. Rate and curate
When you rate a generation 4-5 stars, it automatically becomes a "golden example" that gets prioritized in future retrievals.

```bash
# View your stats
python cli.py stats

# Analyze what's not working
python cli.py analyze-failures
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `generate <prompt>` | Generate text in your style |
| `interactive` | Interactive generation mode |
| `load-samples` | Load sample data to get started |
| `import-data [path]` | Import your message data |
| `add-example <text>` | Manually add a single example |
| `stats` | Show statistics |
| `analyze-failures` | Review low-rated generations |

## Data Format

### JSON (Recommended)
```json
[
  {
    "context": "optional - what you're responding to",
    "response": "your actual message",
    "category": "email_professional|linkedin_post|slack_casual|whatsapp_personal|twitter_post",
    "tone": "formal|casual|friendly|professional|witty",
    "tags": ["optional", "tags"]
  }
]
```

### CSV
```csv
context,response,category,tone,tags
"Project update needed","Here's the latest on the project...",email_professional,professional,"update,work"
```

## Configuration

Edit `config.py` to change:
- `LLM_MODEL`: Default is `llama3.1:8b`
- `EMBEDDING_MODEL`: Default is `BAAI/bge-small-en-v1.5`
- `NUM_EXAMPLES_TO_RETRIEVE`: How many examples to include in prompts (default: 5)

## How It Works

1. **Embedding**: Your messages are embedded using a local sentence transformer
2. **Retrieval**: When you request a generation, similar examples are retrieved from ChromaDB
3. **Few-shot prompting**: Retrieved examples are included in the prompt to guide style
4. **Feedback loop**: Good outputs become golden examples, improving future generations

## Tips for Best Results

1. **Quality over quantity**: 50 high-quality examples beat 500 noisy ones
2. **Cover variety**: Include different situations within each category
3. **Be consistent with ratings**: Your feedback shapes the system
4. **Add golden examples manually**: If you write something great, add it directly:
   ```bash
   python cli.py add-example "your great message" -c slack_casual -t witty
   ```

## Next Steps (Phase 2)

If RAG alone isn't capturing your style well enough, Phase 2 adds QLoRA fine-tuning:
- Train a LoRA adapter on your curated examples
- Combine with RAG for best of both worlds
- See `conversation_log.md` for the full roadmap

---

Built for privacy. All processing happens locally.
