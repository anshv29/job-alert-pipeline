import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


class EmailConfigError(Exception):
    pass


def email_settings():
    sender = os.getenv("EMAIL_ADDRESS", "").strip()
    password = os.getenv("EMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    recipient = os.getenv("RECIPIENT_EMAIL", "").strip() or sender
    missing = [name for name, v in (("EMAIL_ADDRESS", sender), ("EMAIL_APP_PASSWORD", password)) if not v]
    if missing:
        raise EmailConfigError(
            "Missing secret(s): " + ", ".join(missing) + ". Add them in your repository under "
            "Settings, Secrets and variables, Actions (see the README, step 5)."
        )
    return sender, password, recipient


def send_email(subject, html_body):
    sender, password, recipient = email_settings()
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise EmailConfigError(
            "Gmail rejected the login. Use a 16 letter App Password (not your normal Gmail password) "
            "and check that EMAIL_ADDRESS is the same Gmail account that made it."
        )
    return recipient


def send_html_email_with_image(subject, html_body, image_bytes, image_cid):
    sender, password, recipient = email_settings()
    msg = MIMEMultipart("related")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)
    image = MIMEImage(image_bytes)
    image.add_header("Content-ID", f"<{image_cid}>")
    image.add_header("Content-Disposition", "inline", filename=f"{image_cid}.png")
    msg.attach(image)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
