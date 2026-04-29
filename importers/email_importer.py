"""Import messages from email exports (Gmail/Outlook)."""
import email
import re
from pathlib import Path
from email import policy
from email.parser import BytesParser
from datetime import datetime
from typing import Optional
import mailbox
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models import Message, Style, Tone


class EmailImporter:
    """
    Import your sent emails from various email export formats.
    
    Supported formats:
    - MBOX (Gmail Takeout, Thunderbird export)
    - EML files (individual email exports)
    
    How to export from Gmail:
    1. Go to takeout.google.com
    2. Select only "Mail" 
    3. Choose MBOX format
    4. Download and extract
    
    How to export from Outlook:
    1. File > Open & Export > Import/Export
    2. Export to a file > Outlook Data File (.pst)
    3. Or drag emails to a folder to save as .eml files
    """
    
    def __init__(self, your_emails: list[str] | str, your_name: Optional[str] = None):
        """
        Args:
            your_emails: Your email address(es) - can be a single string or list
            your_name: Your name (optional, for matching)
        """
        # Support both single email and list of emails
        if isinstance(your_emails, str):
            self.your_emails = [your_emails.lower()]
        else:
            self.your_emails = [e.lower() for e in your_emails]
        self.your_name = your_name.lower() if your_name else None
    
    def _is_my_email(self, from_header: str) -> bool:
        """Check if this email is from you."""
        from_lower = from_header.lower()
        # Check all email addresses
        for email in self.your_emails:
            if email in from_lower:
                return True
        if self.your_name and self.your_name in from_lower:
            return True
        return False
    
    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract plain text body from email."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            body = payload.decode(charset, errors='replace')
                            break
                    except:
                        continue
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
            except:
                body = str(msg.get_payload())
        
        return self._clean_email_body(body)
    
    def _clean_email_body(self, body: str) -> str:
        """Clean email body - remove signatures, quotes, citations."""
        lines = body.split('\n')
        cleaned_lines = []
        
        # Markers that indicate end of original content
        stop_markers = [
            # English
            '--', '---', '____', '___', 'Best,', 'Thanks,', 'Regards,', 
            'Best regards,', 'Cheers,', 'Sent from my iPhone', 'Sent from my iPad',
            # French
            'Cordialement,', 'Bien cordialement,', 'Bien à vous,', 'Cdlt,',
            'Bonne journée,', 'Bonne soirée,', 'À bientôt,', 'Amicalement,',
            'Bisous,', 'Bises,', 'Gros bisous,',
            # Citation markers
            '---- Message d\'origine ----', '---- Original Message ----',
            '----- Message transféré -----', '----- Forwarded Message -----',
            '________________________________',  # Outlook separator
        ]
        
        # Patterns that indicate quoted/forwarded content
        quote_patterns = [
            r'^>',  # Quoted line
            r'^Le .+ a écrit\s*:',  # French "On date X wrote:"
            r'^On .+ wrote:',  # English
            r'^De\s*:.*@',  # "De: email@..."
            r'^From\s*:.*@',  # "From: email@..."
            r'^Envoyé\s*:',  # "Envoyé:"
            r'^Sent\s*:',  # "Sent:"
            r'^Date\s*:.*\d{4}',  # "Date: ... 2024"
            r'^Objet\s*:',  # "Objet:"
            r'^Subject\s*:',  # "Subject:"
            r'^À\s*:.*@',  # "À: email@..."
            r'^To\s*:.*@',  # "To: email@..."
        ]
        
        for line in lines:
            stripped = line.strip()
            
            # Stop at signature/citation markers
            if any(stripped.startswith(marker) or stripped == marker 
                   for marker in stop_markers):
                break
            
            # Skip quoted lines
            if any(re.match(pattern, stripped, re.IGNORECASE) 
                   for pattern in quote_patterns):
                continue
            
            cleaned_lines.append(line)
        
        # Join and clean up whitespace
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Reduce multiple newlines
        text = text.strip()
        
        # Remove trailing signature name if it's just the name alone
        lines = text.split('\n')
        while lines and len(lines[-1].strip()) < 50:
            last = lines[-1].strip().lower()
            # Common sign-off patterns
            if any(last.startswith(p) for p in ['aländji', 'marie', 'envoyé de']):
                lines.pop()
            elif last in ['', 'a.', 'ab', 'a']:
                lines.pop()
            else:
                break
        
        return '\n'.join(lines).strip()
    
    def _extract_quoted_context(self, body) -> Optional[str]:
        """Extract the original message being replied to."""
        # Handle case where body is a list (multipart email)
        if not isinstance(body, str):
            return None
        lines = body.split('\n')
        quoted_lines = []
        in_quote = False
        
        for line in lines:
            if re.match(r'^On .+ wrote:$', line.strip()):
                in_quote = True
                continue
            
            if in_quote and line.strip().startswith('>'):
                quoted_lines.append(line.strip()[1:].strip())
        
        if quoted_lines:
            return ' '.join(quoted_lines[:5])  # First few lines of quote
        return None
    
    def _is_personal_email(self, text: str, subject: str = "") -> bool:
        """Detect if email is personal (vs professional)."""
        combined = (text + " " + subject).lower()
        
        # Personal greetings (French)
        personal_greetings = [
            'salut', 'coucou', 'hello', 'hey', 'kikou', 'bijour',
            'mon amour', 'ma chérie', 'mon chéri', 'ma puce', 'mon cœur',
        ]
        
        # Personal closings (French)
        personal_closings = [
            'bisous', 'bises', 'gros bisous', 'je t\'embrasse', 'grosses bises',
            'à bientôt', 'on se voit', 'hâte de te voir', 'tu me manques',
            'je t\'aime', 'love', 'xoxo', '😘', '❤️', '💕',
        ]
        
        # Personal content indicators
        personal_content = [
            'maman', 'papa', 'frérot', 'soeurette', 'tonton', 'tata',
            'anniversaire', 'joyeux', 'vacances', 'week-end', 'weekend',
            'dîner', 'resto', 'apéro', 'soirée', 'fête',
        ]
        
        # Check for personal indicators
        text_start = combined[:200]  # Check beginning for greetings
        text_end = combined[-200:] if len(combined) > 200 else combined  # Check end for closings
        
        has_personal_greeting = any(g in text_start for g in personal_greetings)
        has_personal_closing = any(c in text_end for c in personal_closings)
        has_personal_content = any(p in combined for p in personal_content)
        
        # If 2+ personal indicators, it's personal
        personal_score = sum([has_personal_greeting, has_personal_closing, has_personal_content])
        return personal_score >= 1
    
    def _detect_tone(self, text: str, subject: str = "") -> Tone:
        """Detect tone from email content."""
        combined = (text + " " + subject).lower()
        
        # Professional indicators
        professional_indicators = ['please find attached', 'as discussed', 'per our conversation',
                                  'following up', 'regarding', 'as per', 'kindly']
        if any(ind in combined for ind in professional_indicators):
            return Tone.PROFESSIONAL
        
        # Formal indicators
        formal_indicators = ['dear', 'sincerely', 'respectfully', 'hereby']
        if any(ind in combined for ind in formal_indicators):
            return Tone.FORMAL
        
        # Friendly indicators
        friendly_indicators = ['hope you', 'thanks so much', 'appreciate', 'great to hear']
        if any(ind in combined for ind in friendly_indicators):
            return Tone.FRIENDLY
        
        return Tone.PROFESSIONAL  # Default for email
    
    def _parse_email(self, msg: email.message.Message) -> Optional[Message]:
        """Parse a single email into a Message."""
        from_header = msg.get("From", "")
        
        if not self._is_my_email(from_header):
            return None
        
        subject = msg.get("Subject", "")
        body = self._extract_body(msg)
        
        if not body or len(body) < 20:  # Skip very short emails
            return None
        
        # Get context from quoted reply
        context = self._extract_quoted_context(msg.get_payload(decode=False) or "")
        if not context and subject:
            context = f"Subject: {subject}"
        
        # Detect if personal or professional
        is_personal = self._is_personal_email(body, subject)
        style = Style.EMAIL_DECONTRACTE if is_personal else Style.EMAIL_FORMEL
        
        return Message(
            context=context,
            response=body,
            style=style,
            tags=["email", "personal" if is_personal else "professional"],
        )
    
    def import_mbox(self, mbox_path: Path) -> list[Message]:
        """Import emails from an MBOX file."""
        mbox_path = Path(mbox_path)
        messages = []
        
        mbox = mailbox.mbox(str(mbox_path))
        
        for msg in mbox:
            parsed = self._parse_email(msg)
            if parsed:
                messages.append(parsed)
        
        return messages
    
    def import_eml(self, eml_path: Path) -> Optional[Message]:
        """Import a single EML file."""
        eml_path = Path(eml_path)
        
        with open(eml_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        return self._parse_email(msg)
    
    def import_folder(self, folder: Path) -> list[Message]:
        """Import all emails from a folder (EML files or MBOX)."""
        folder = Path(folder)
        all_messages = []
        
        # Import MBOX files
        for mbox_file in folder.glob("*.mbox"):
            msgs = self.import_mbox(mbox_file)
            all_messages.extend(msgs)
            print(f"  Imported {len(msgs)} emails from {mbox_file.name}")
        
        # Import EML files
        eml_count = 0
        for eml_file in folder.glob("*.eml"):
            msg = self.import_eml(eml_file)
            if msg:
                all_messages.append(msg)
                eml_count += 1
        
        if eml_count > 0:
            print(f"  Imported {eml_count} emails from EML files")
        
        return all_messages
