import imaplib
import email
from email.header import decode_header
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def connect_gmail(email_address: str, app_password: str):
    """Connexion à Gmail via IMAP."""
    imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    imap.login(email_address, app_password)
    return imap

def fetch_emails(imap, folder: str = "INBOX", limit: int = 10):
    """Récupère les derniers emails d'un dossier."""
    # Guillemets nécessaires pour dossiers avec caractères spéciaux
    imap.select(f'"{folder}"')
    
    # Rechercher tous les emails
    status, messages = imap.search(None, "ALL")
    email_ids = messages[0].split()
    
    # Prendre les N derniers (ou tous si limit=None)
    if limit is None:
        latest_ids = email_ids
    else:
        latest_ids = email_ids[-limit:] if len(email_ids) >= limit else email_ids
    
    emails = []
    for email_id in reversed(latest_ids):
        status, msg_data = imap.fetch(email_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Décoder le sujet
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                
                # Expéditeur
                from_ = msg.get("From")
                date = msg.get("Date")
                
                # Corps du message
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                            except:
                                body = part.get_payload(decode=True).decode("latin-1")
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = msg.get_payload(decode=True).decode("latin-1")
                
                emails.append({
                    "subject": subject,
                    "from": from_,
                    "date": date,
                    "body": body
                })
    
    return emails

def search_emails(imap, folder: str = "INBOX", search_criteria: str = "ALL"):
    """
    Recherche emails avec critères.
    Exemples de critères:
    - 'FROM "example@gmail.com"'
    - 'SUBJECT "important"'
    - 'SINCE "01-Jan-2024"'
    - 'UNSEEN' (non lus)
    """
    imap.select(f'"{folder}"')
    status, messages = imap.search(None, search_criteria)
    return messages[0].split()

def list_folders(imap):
    """Liste tous les dossiers Gmail disponibles."""
    status, folders = imap.list()
    folder_names = []
    for folder in folders:
        # Decode folder name
        parts = folder.decode().split(' "/" ')
        if len(parts) == 2:
            folder_names.append(parts[1].strip('"'))
    return folder_names

def save_to_json(emails: list, filename: str):
    """Sauvegarde les emails en JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)
    print(f"Sauvegardé {len(emails)} emails dans {filename}")


if __name__ == "__main__":
    # Configuration
    EMAIL = os.environ["GMAIL_ADDRESS"]
    APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
    
    # Dossiers Gmail courants:
    # - "INBOX" : Boîte de réception
    # - "[Gmail]/Sent Mail" : Messages envoyés (EN)
    # - "[Gmail]/Messages envoy&AOk-s" : Messages envoyés (FR)
    # - "[Gmail]/All Mail" : Tous les messages
    # - "[Gmail]/Drafts" : Brouillons
    
    FOLDER = "[Gmail]/Messages envoy&AOk-s"  # Messages envoyés (FR)
    LIMIT = None  # Nombre d'emails à récupérer (None = tous)
    OUTPUT_FILE = "data/sent_emails_personal.json"  # Emails personnels
    
    try:
        print("Connexion à Gmail...")
        imap = connect_gmail(EMAIL, APP_PASSWORD)
        
        # Lister les dossiers disponibles
        print("\nDossiers disponibles:")
        for folder in list_folders(imap):
            print(f"  - {folder}")
        
        print(f"\nRécupération des {LIMIT} derniers emails de '{FOLDER}'...")
        emails = fetch_emails(imap, folder=FOLDER, limit=LIMIT)
        
        print(f"\n{len(emails)} emails récupérés.")
        
        # Aperçu des 3 premiers
        for i, email_data in enumerate(emails[:3], 1):
            print(f"\n--- Email {i} ---")
            print(f"De: {email_data['from']}")
            print(f"Sujet: {email_data['subject']}")
            print(f"Date: {email_data['date']}")
            print(f"Aperçu: {email_data['body'][:150]}...")
        
        # Sauvegarder en JSON
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        save_to_json(emails, OUTPUT_FILE)
        
        imap.logout()
        print("\nDéconnexion réussie.")
        
    except Exception as e:
        print(f"Erreur: {e}")
