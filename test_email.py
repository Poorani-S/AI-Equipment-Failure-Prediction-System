import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def test_smtp():
    server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    port = int(os.getenv("MAIL_PORT", "587"))
    user = os.getenv("MAIL_USERNAME", "poorani0307@gmail.com")
    # Clean password like the app does
    pwd = (os.getenv("MAIL_PASSWORD") or "").strip().replace(" ", "")
    sender = os.getenv("MAIL_DEFAULT_SENDER") or user
    recipient = "poorani0307@gmail.com" # Send to self for test

    print(f"Connecting to {server}:{port}...")
    try:
        smtp = smtplib.SMTP(server, port, timeout=10)
        print("Connected. Starting TLS...")
        smtp.starttls()
        print(f"Logging in as {user}...")
        smtp.login(user, pwd)
        print("Login successful!")

        msg = MIMEText("This is a direct SMTP test from the AI Equipment Failure Prediction System.")
        msg['Subject'] = "SMTP Test"
        msg['From'] = sender
        msg['To'] = recipient

        print(f"Sending test email to {recipient}...")
        smtp.send_message(msg)
        smtp.quit()
        print("SUCCESS: Email sent!")
    except Exception as e:
        print(f"FAILURE: {str(e)}")

if __name__ == "__main__":
    test_smtp()
