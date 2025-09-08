from email.message import EmailMessage

import aiosmtplib

from app.core.settings import settings

GMAIL_USER = settings.GMAIL_USER
GMAIL_PASS = settings.GMAIL_PASS
SUPPORT_EMAIL_TO = getattr(settings, "SUPPORT_EMAIL_TO", "")


async def send_verification_email(to_email: str, verify_url: str):
    if not GMAIL_USER or not GMAIL_PASS:
        return  # Not configured; skip sending in dev
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "Verify your email for EPU"
    msg.set_content(f"Please verify your email by clicking the following link: {verify_url}")

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_PASS,
    )


async def send_support_email(
    name: str,
    from_email: str,
    message: str,
    topic: str | None = None,
    order_number: str | None = None,
    event_url: str | None = None,
):
    """Send a contact/support email to SUPPORT_EMAIL_TO. No-op if not configured."""
    if not GMAIL_USER or not GMAIL_PASS or not SUPPORT_EMAIL_TO:
        return
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = SUPPORT_EMAIL_TO
    topic_str = f" [{topic}]" if topic else ""
    msg["Subject"] = f"[EPU Support{topic_str}] Message from {name} <{from_email}>"
    body = (
        "A new support message was submitted via /contact.\n\n"
        f"From: {name} <{from_email}>\n"
        f"Topic: {topic or 'N/A'}\n"
        "\n--- Message ---\n"
        f"{message}\n"
    )
    if order_number:
        body += f"\nOrder number: {order_number}\n"
    if event_url:
        body += f"Event URL: {event_url}\n"
    msg.set_content(body)
    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_PASS,
    )


async def send_account_deletion_email(to_email: str):
    if not GMAIL_USER or not GMAIL_PASS:
        return
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "Account Deletion Requested - EPU"
    msg.set_content(
        """
Your account deletion request has been received. Your data will be removed within 30 days.

If this was a mistake or you wish to cancel, please contact us immediately: https://epu.com/contact

If you have any questions, reply to this email.
        """
    )
    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_PASS,
    )


async def send_event_date_locked_email(
    to_email: str, event_name: str, event_date: str, dashboard_url: str
):
    """Notify the user their event date has been locked.
    event_date should be preformatted for human display (e.g., DD-MM-YYYY).
    """
    if not GMAIL_USER or not GMAIL_PASS:
        return
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = f"Your event date was locked – {event_name}"
    body = (
        f"Hello,\n\n"
        f"This is a confirmation that your event '{event_name}' has been finalised.\n"
        f"Locked date: {event_date}.\n\n"
        f"You can view your event details here: {dashboard_url}\n\n"
        f"If you did not perform this action, please contact support immediately.\n"
    )
    msg.set_content(body)
    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_PASS,
    )


async def send_billing_email(to_email: str, subject: str, body: str):
    """Generic billing email notification; no-op if mail not configured."""
    if not GMAIL_USER or not GMAIL_PASS or not to_email:
        return
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=GMAIL_USER,
        password=GMAIL_PASS,
    )
