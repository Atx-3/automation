"""
messaging.py — Automated messaging module for the AI Assistant.

Supports sending messages on behalf of the user via email (SMTP).
Uses credentials from environment variables.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


async def send_email(
    to: str,
    subject: str,
    body: str,
    smtp_server: Optional[str] = None,
    smtp_port: Optional[int] = None,
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None,
) -> str:
    """
    Send an email on behalf of the user.

    Reads SMTP credentials from environment variables if not provided.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body text.
        smtp_server: SMTP server address (default from env).
        smtp_port: SMTP port (default from env).
        sender_email: Sender email address (default from env).
        sender_password: Sender app password (default from env).

    Returns:
        Success or error message.
    """
    try:
        # Load from environment if not provided
        smtp_server = smtp_server or os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        sender_email = sender_email or os.getenv("SENDER_EMAIL", "")
        sender_password = sender_password or os.getenv("SENDER_PASSWORD", "")

        if not sender_email or not sender_password:
            return (
                "❌ Email not configured. Add these to your .env file:\n"
                "SENDER_EMAIL=your_email@gmail.com\n"
                "SENDER_PASSWORD=your_app_password\n"
                "SMTP_SERVER=smtp.gmail.com\n"
                "SMTP_PORT=587\n\n"
                "💡 For Gmail, use an App Password: "
                "https://myaccount.google.com/apppasswords"
            )

        # Validate inputs
        if not to or "@" not in to:
            return f"❌ Invalid recipient email: {to}"

        # Build email
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to
        msg["Subject"] = subject or "(No Subject)"
        msg.attach(MIMEText(body or "", "plain", "utf-8"))

        # Send
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
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
