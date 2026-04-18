from email.message import EmailMessage
from smtplib import SMTP, SMTP_SSL

from app.core.config import settings


def send_verification_email(to_email: str, name: str, verification_code: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"Verify your {settings.APP_NAME} account"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message.set_content(
        "\n".join(
            [
                f"Hi {name},",
                "",
                "Use this code to verify your email address:",
                verification_code,
                "",
                "This code expires in 24 hours.",
            ]
        )
    )
    message.add_alternative(
        f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6">
          <h2>Verify your email</h2>
          <p>Hi {name},</p>
          <p>Use this code to verify your email address:</p>
          <p style="font-size: 28px; font-weight: 700; letter-spacing: 6px">{verification_code}</p>
          <p>This code expires in 24 hours.</p>
        </div>
        """,
        subtype="html",
    )

    smtp_class = SMTP_SSL if settings.SMTP_SECURE else SMTP
    with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if not settings.SMTP_SECURE:
            smtp.starttls()
        smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)
