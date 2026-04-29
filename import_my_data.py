"""
Unified data import script for your personal messages.

Usage:
    1. Edit my_config.yaml with your details
    2. Run: python import_my_data.py
    
That's it! The script reads all settings from my_config.yaml
"""
import sys
from pathlib import Path
import yaml

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from importers.slack_importer import SlackImporter
from importers.whatsapp_importer import WhatsAppImporter
from importers.email_importer import EmailImporter
from embeddings import EmbeddingStore
from data_loader import DataLoader

CONFIG_FILE = Path(__file__).parent / "my_config.yaml"


def load_config() -> dict:
    """Load configuration from YAML file."""
    if not CONFIG_FILE.exists():
        print(f"❌ Config file not found: {CONFIG_FILE}")
        print("   Please create my_config.yaml first.")
        sys.exit(1)
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    return config


def main():
    print("=" * 60)
    print("Personal Message Importer")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Extract settings
    your_name = config.get("your_name", "")
    # Support both old single email and new multiple emails format
    your_emails = config.get("your_emails") or [config.get("your_email", "")]
    if isinstance(your_emails, str):
        your_emails = [your_emails]
    slack_user_id = config.get("slack_user_id")
    slack_username = config.get("slack_username", "")
    
    slack_path = config.get("slack_export_path")
    slack_channels = config.get("slack_channels")
    whatsapp_path = config.get("whatsapp_folder")
    email_path = config.get("email_folder")
    
    print(f"\n📋 Config loaded from: {CONFIG_FILE.name}")
    print(f"   Your name: {your_name}")
    print(f"   Your emails: {', '.join(your_emails)}")
    
    store = EmbeddingStore()
    loader = DataLoader(store)
    
    total_imported = 0
    
    # Import Slack
    if slack_path and Path(slack_path).exists():
        print(f"\n📱 Importing Slack messages from: {slack_path}")
        
        slack = SlackImporter(
            your_user_id=slack_user_id,
            your_username=slack_username
        )
        
        # Help find user ID if not set
        if not slack_user_id:
            users = slack.find_your_user_id(Path(slack_path))
            if users:
                print(f"  💡 Found users in export: {users}")
                print(f"     Set slack_user_id in my_config.yaml for better matching")
        
        messages = slack.import_export_folder(
            Path(slack_path), 
            channels=slack_channels
        )
        
        if messages:
            loader.import_to_store(messages)
            total_imported += len(messages)
            print(f"  ✓ Imported {len(messages)} Slack messages")
    elif slack_path:
        print(f"\n⚠️  Slack path not found: {slack_path}")
    
    # Import WhatsApp
    if whatsapp_path and Path(whatsapp_path).exists():
        print(f"\n💬 Importing WhatsApp messages from: {whatsapp_path}")
        
        whatsapp = WhatsAppImporter(your_name=your_name)
        messages = whatsapp.import_folder(Path(whatsapp_path))
        
        if messages:
            loader.import_to_store(messages)
            total_imported += len(messages)
            print(f"  ✓ Imported {len(messages)} WhatsApp messages")
    elif whatsapp_path:
        print(f"\n⚠️  WhatsApp path not found: {whatsapp_path}")
    
    # Import Email
    if email_path and Path(email_path).exists():
        print(f"\n📧 Importing emails from: {email_path}")
        
        email_importer = EmailImporter(
            your_emails=your_emails,
            your_name=your_name
        )
        messages = email_importer.import_folder(Path(email_path))
        
        if messages:
            loader.import_to_store(messages)
            total_imported += len(messages)
            print(f"  ✓ Imported {len(messages)} emails")
    elif email_path:
        print(f"\n⚠️  Email path not found: {email_path}")
    
    # Summary
    print("\n" + "=" * 60)
    if total_imported > 0:
        stats = store.get_stats()
        print(f"✅ Import complete!")
        print(f"   Total messages imported: {total_imported}")
        print(f"   Total in database: {stats['total_examples']}")
        print(f"   Golden examples: {stats['golden_examples']}")
        print("\n🚀 You can now generate text in your style:")
        print('   python cli.py generate "your prompt" -c slack_casual')
        print("   python cli.py interactive")
    else:
        print("⚠️  No data sources configured or paths not found!")
        print("\nTo import your data:")
        print(f"1. Edit {CONFIG_FILE.name}")
        print("2. Fill in your_name and your_email")
        print("3. Set paths to your exported data")
        print("4. Run this script again: python import_my_data.py")


if __name__ == "__main__":
    main()
