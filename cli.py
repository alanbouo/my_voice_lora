"""CLI interface for the RAG writing assistant."""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich import print as rprint
from typing import Optional

from models import Style, GenerationRequest
from embeddings import EmbeddingStore
from generator import StyleGenerator
from feedback import FeedbackManager
from data_loader import DataLoader, create_sample_data
from config import LLM_MODEL

app = typer.Typer(help="Personal Writing Style Assistant")
console = Console()


@app.command()
def generate(
    prompt: str = typer.Argument(..., help="What you want to write about"),
    style: str = typer.Option("slack_equipe", "-s", "--style",
        help="Style: email_formel, email_decontracte, message_perso, slack_equipe, linkedin, twitter"),
    context: Optional[str] = typer.Option(None, "--context", help="Additional context"),
):
    """Generate text in your personal style."""
    try:
        style_enum = Style(style)
    except ValueError as e:
        console.print(f"[red]Invalid style: {e}[/red]")
        raise typer.Exit(1)

    store = EmbeddingStore()
    generator = StyleGenerator(store)
    feedback_mgr = FeedbackManager(store)

    stats = store.get_stats()
    if stats["total_examples"] == 0:
        console.print("[yellow]Warning: No examples loaded. Run 'load-samples' or import your data first.[/yellow]")

    request = GenerationRequest(
        prompt=prompt,
        style=style_enum,
        additional_context=context,
    )

    console.print(f"\n[dim]Generating with {LLM_MODEL}...[/dim]\n")

    result = generator.generate(request)

    console.print(Panel(
        result.generated_text,
        title=f"[bold green]Generated ({style})[/bold green]",
        border_style="green",
    ))
    
    # Show retrieved examples used
    if result.retrieved_examples:
        console.print(f"\n[dim]Based on {len(result.retrieved_examples)} retrieved examples[/dim]")
    
    # Prompt for feedback
    console.print()
    if Confirm.ask("Rate this generation?", default=True):
        rating = IntPrompt.ask("Rating (1-5)", default=3)
        feedback = Prompt.ask("Feedback (optional)", default="")
        
        feedback_mgr.rate_generation(result, rating, feedback or None)
        
        if rating >= 4:
            console.print("[green]✓ Added to golden examples[/green]")
        elif rating <= 2:
            console.print("[yellow]Logged for improvement analysis[/yellow]")


@app.command()
def interactive():
    """Interactive mode for continuous generation and feedback."""
    store = EmbeddingStore()
    generator = StyleGenerator(store)
    feedback_mgr = FeedbackManager(store)
    
    console.print(Panel(
        "[bold]Personal Writing Assistant[/bold]\n\n"
        "Commands:\n"
        "  /quit - Exit\n"
        "  /stats - Show statistics\n"
        "  /style <name> - Change style\n"
        "  /regen - Regenerate last output\n"
        "  Or just type what you want to write!",
        title="Interactive Mode",
    ))
    
    current_style = Style.SLACK_EQUIPE
    last_result = None

    while True:
        console.print(f"\n[dim]({current_style.value})[/dim]")
        user_input = Prompt.ask("[bold blue]You[/bold blue]")

        if not user_input:
            continue

        if user_input.lower() == "/quit":
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() == "/stats":
            show_stats()
            continue

        if user_input.lower().startswith("/style "):
            try:
                current_style = Style(user_input.split(" ", 1)[1].strip())
                console.print(f"[green]Style set to: {current_style.value}[/green]")
            except ValueError:
                console.print(f"[red]Invalid style. Options: {[s.value for s in Style]}[/red]")
            continue

        if user_input.lower() == "/regen" and last_result:
            feedback = Prompt.ask("Adjustment (or Enter to regenerate as-is)", default="")
            result = generator.regenerate(last_result, feedback)
        else:
            request = GenerationRequest(
                prompt=user_input,
                style=current_style,
            )
            result = generator.generate(request)
        
        last_result = result
        
        console.print(Panel(
            result.generated_text,
            title="[bold green]Generated[/bold green]",
            border_style="green",
        ))
        
        # Quick rating
        rating_input = Prompt.ask(
            "[dim]Rate 1-5 (or Enter to skip)[/dim]",
            default=""
        )
        
        if rating_input.isdigit() and 1 <= int(rating_input) <= 5:
            rating = int(rating_input)
            feedback_mgr.rate_generation(result, rating)
            if rating >= 4:
                console.print("[green]✓ Promoted to golden[/green]")


@app.command("load-samples")
def load_samples():
    """Load sample data to get started."""
    console.print("[dim]Creating sample data...[/dim]")
    files = create_sample_data()
    
    loader = DataLoader()
    from pathlib import Path
    messages = loader.load_from_json(Path(files["json_sample"]))
    count = loader.import_to_store(messages)
    
    console.print(f"[green]✓ Loaded {count} sample messages[/green]")
    console.print(f"[dim]Sample file: {files['json_sample']}[/dim]")
    console.print(f"[dim]CSV template: {files['csv_template']}[/dim]")
    console.print("\n[yellow]Now add your own messages to data/examples/ and run 'import-data'[/yellow]")


@app.command("import-data")
def import_data(
    path: Optional[str] = typer.Argument(None, help="Path to file or directory to import"),
):
    """Import your message data from files."""
    from pathlib import Path
    from config import EXAMPLES_DIR
    
    loader = DataLoader()
    
    if path:
        filepath = Path(path)
        if filepath.is_file():
            if filepath.suffix == ".json":
                messages = loader.load_from_json(filepath)
            elif filepath.suffix == ".csv":
                messages = loader.load_from_csv(filepath)
            else:
                console.print(f"[red]Unsupported file type: {filepath.suffix}[/red]")
                raise typer.Exit(1)
            
            count = loader.import_to_store(messages)
            console.print(f"[green]✓ Imported {count} messages from {filepath.name}[/green]")
        elif filepath.is_dir():
            stats = loader.load_and_import_directory(filepath)
            console.print(f"[green]✓ Imported {stats['loaded']} messages from {len(stats['files'])} files[/green]")
        else:
            console.print(f"[red]Path not found: {path}[/red]")
            raise typer.Exit(1)
    else:
        stats = loader.load_and_import_directory(EXAMPLES_DIR)
        console.print(f"[green]✓ Imported {stats['loaded']} messages from {len(stats['files'])} files[/green]")


@app.command()
def add_example(
    response: str = typer.Argument(..., help="Your message text"),
    style: str = typer.Option(..., "-s", "--style",
        help="Style: email_formel, email_decontracte, message_perso, slack_equipe, linkedin, twitter"),
    context: Optional[str] = typer.Option(None, "--context", help="Optional context"),
    golden: bool = typer.Option(True, "--golden/--no-golden", help="Mark as golden example"),
):
    """Manually add a single example."""
    try:
        style_enum = Style(style)
    except ValueError as e:
        console.print(f"[red]Invalid style: {e}[/red]")
        raise typer.Exit(1)

    if golden:
        feedback_mgr = FeedbackManager()
        message = feedback_mgr.add_manual_golden_example(
            response=response,
            style=style_enum,
            context=context,
        )
        console.print(f"[green]✓ Added golden example: {message.id}[/green]")
    else:
        from models import Message
        store = EmbeddingStore()
        message = Message(
            response=response,
            style=style_enum,
            context=context,
        )
        store.add_message(message)
        console.print(f"[green]✓ Added example: {message.id}[/green]")


@app.command()
def stats():
    """Show statistics about examples and feedback."""
    show_stats()


def show_stats():
    """Display statistics."""
    store = EmbeddingStore()
    feedback_mgr = FeedbackManager(store)
    
    store_stats = store.get_stats()
    feedback_stats = feedback_mgr.get_feedback_stats()
    
    table = Table(title="System Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Examples", str(store_stats["total_examples"]))
    table.add_row("Golden Examples", str(store_stats["golden_examples"]))
    table.add_row("Total Ratings", str(feedback_stats["total_ratings"]))
    table.add_row("Average Rating", f"{feedback_stats['average_rating']:.2f}")
    
    console.print(table)
    
    if feedback_stats["total_ratings"] > 0:
        console.print("\n[bold]Rating Distribution:[/bold]")
        for rating, count in feedback_stats["rating_distribution"].items():
            bar = "█" * count
            console.print(f"  {rating}★: {bar} ({count})")


@app.command()
def clear_database(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all examples from the database (for re-import)."""
    if not confirm:
        if not Confirm.ask("[red]This will delete ALL examples. Continue?[/red]"):
            console.print("Cancelled.")
            return
    
    store = EmbeddingStore()
    
    # Delete and recreate collections
    try:
        store.client.delete_collection("message_examples")
    except:
        pass
    try:
        store.client.delete_collection("golden_examples")
    except:
        pass
    
    console.print("[green]✓ Database cleared. Run import again.[/green]")


@app.command()
def show_examples(
    count: int = typer.Option(5, "-n", "--count", help="Number of examples to show"),
    style: Optional[str] = typer.Option(None, "-s", "--style", help="Filter by style"),
    random_sample: bool = typer.Option(True, "--random/--first", help="Random sample or first N"),
):
    """Show examples from the database to verify quality."""
    import random
    
    store = EmbeddingStore()
    
    # Get all examples
    results = store.examples_collection.get(include=["metadatas", "documents"])
    
    if not results["ids"]:
        console.print("[yellow]No examples in database.[/yellow]")
        return
    
    # Combine into list of examples
    examples = []
    for i, id_ in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        item_style = meta.get("style") or meta.get("category", "")
        if style and item_style != style:
            continue
        examples.append({
            "id": id_,
            "response": meta.get("response", "")[:300],
            "context": meta.get("context", ""),
            "style": item_style,
            "is_golden": meta.get("is_golden", False),
        })

    if not examples:
        console.print(f"[yellow]No examples found for style '{style}'[/yellow]")
        return
    
    # Sample
    if random_sample and len(examples) > count:
        examples = random.sample(examples, count)
    else:
        examples = examples[:count]
    
    console.print(f"\n[bold]Showing {len(examples)} examples from database:[/bold]\n")
    
    for i, ex in enumerate(examples, 1):
        golden = " ⭐" if ex["is_golden"] else ""
        console.print(Panel(
            f"[dim]Context:[/dim] {ex['context'][:100] if ex['context'] else '(none)'}\n\n"
            f"[bold]Response:[/bold]\n{ex['response']}",
            title=f"Example {i}{golden} [{ex['style']}]",
            border_style="blue",
        ))


@app.command()
def analyze_failures():
    """Analyze low-rated generations to identify patterns."""
    feedback_mgr = FeedbackManager()
    failures = feedback_mgr.get_low_rated_patterns()
    
    if not failures:
        console.print("[green]No low-rated generations found![/green]")
        return
    
    console.print(f"\n[bold]Found {len(failures)} low-rated generations:[/bold]\n")
    
    for f in failures[:10]:  # Show last 10
        console.print(Panel(
            f"[bold]Request:[/bold] {f.get('request', {}).get('prompt', 'N/A')}\n\n"
            f"[bold]Generated:[/bold] {f.get('generated_text', 'N/A')[:200]}...\n\n"
            f"[bold]Feedback:[/bold] {f.get('feedback', 'None')}",
            title=f"Rating: {f.get('rating', '?')}★",
            border_style="red",
        ))


if __name__ == "__main__":
    app()
