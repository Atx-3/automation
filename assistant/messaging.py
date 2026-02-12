"""
messaging.py — Automated messaging module for Chapna AI Assistant.

Supports sending messages on behalf of the user via email (SMTP).
Uses credentials from environment variables.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import config
from security import validate_email


async def send_email(
    to: str,
    subject: str,
    body: str,
) -> str:
    """
    Send an email on behalf of the user.

    Uses SMTP credentials from config.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.

    Returns:
        Success or error message.
    """
    try:
        if not config.SENDER_EMAIL or not config.SENDER_PASSWORD:
            return (
                "❌ Email not configured. Add these to your .env file:\n"
                "SENDER_EMAIL=your_email@gmail.com\n"
                "SENDER_PASSWORD=your_app_password\n"
                "SMTP_SERVER=smtp.gmail.com\n"
                "SMTP_PORT=587\n\n"
                "💡 For Gmail, use an App Password: "
                "https://myaccount.google.com/apppasswords"
            )

        # Validate recipient
        if not to or not validate_email(to):
            return f"❌ Invalid recipient email: {to}"

        # Build email
        msg = MIMEMultipart()
        msg["From"] = config.SENDER_EMAIL
        msg["To"] = to
        msg["Subject"] = subject or "(No Subject)"
        msg.attach(MIMEText(body or "", "plain", "utf-8"))

        # Send
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
            server.send_message(msg)

        return f"✅ Email sent successfully to {to}\n📧 Subject: {subject}"

    except smtplib.SMTPAuthenticationError:
        return (
            "❌ Email authentication failed. Check your credentials.\n"
            "💡 For Gmail, make sure you're using an App Password."
        )
    except smtplib.SMTPRecipientsRefused:
        return f"❌ Recipient refused: {to}"
    except Exception as e:
        return f"❌ Error sending email: {str(e)}"


async def send_message(platform: str, **kwargs) -> str:
    """
    Route a message-sending request to the appropriate handler.

    Args:
        platform: The messaging platform (currently: "email").
        **kwargs: Platform-specific parameters.

    Returns:
        Result message.
    """
    platform = platform.lower().strip()

    if platform == "email":
        return await send_email(
            to=kwargs.get("to", ""),
            subject=kwargs.get("subject", ""),
            body=kwargs.get("body", ""),
        )
    else:
        return (
            f"❌ Messaging platform '{platform}' is not yet supported.\n"
            f"✅ Supported platforms: email\n\n"
            f"💡 To add more platforms, configure them in messaging.py"
        )
