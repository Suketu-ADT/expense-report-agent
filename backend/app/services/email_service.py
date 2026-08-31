import os
import smtplib
from email.message import EmailMessage
import time
import shutil

def send_email(to_email: str, subject: str, body: str, attachment_path: str = None) -> bool:
    dev_mode = os.getenv("DEVELOPMENT_MODE", "true").lower() == "true"
    
    if dev_mode:
        print(f"Simulating email to {to_email}...")
        # Save simulated email
        out_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'simulated_emails')
        os.makedirs(out_dir, exist_ok=True)
        timestamp = int(time.time())
        file_path = os.path.join(out_dir, f"email_{timestamp}.txt")
        
        with open(file_path, "w") as f:
            f.write(f"To: {to_email}\n")
            f.write(f"Subject: {subject}\n\n")
            f.write(body)
            if attachment_path:
                f.write(f"\n[Attachment]: {os.path.basename(attachment_path)}")
                # Copy attachment for simulation
                shutil.copy2(attachment_path, os.path.join(out_dir, f"attached_{os.path.basename(attachment_path)}"))
        return True
    
    # Real SMTP
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM")
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)
    
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=os.path.basename(attachment_path))
            
    # Retry logic (exponential backoff)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Email failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return False
