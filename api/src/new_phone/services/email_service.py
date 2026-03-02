"""SMTP email service for voicemail-to-email notifications."""

import smtplib
from email.message import EmailMessage
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

from new_phone.config import settings

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "emails"
SUPPORTED_LANGUAGES = {"en", "es", "fr"}

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,
)


def _get_template(name: str, language: str) -> str:
    lang = language if language in SUPPORTED_LANGUAGES else "en"
    filename = f"{name}.{lang}.txt"
    try:
        template = _jinja_env.get_template(filename)
    except Exception:
        template = _jinja_env.get_template(f"{name}.en.txt")
    return template


class EmailService:
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_address = settings.smtp_from_address
        self.attach_audio = settings.smtp_attach_audio

    def send_voicemail_notification(
        self,
        to_email: str,
        mailbox_number: str,
        caller_number: str,
        caller_name: str,
        duration_seconds: int,
        audio_data: bytes | None = None,
        audio_filename: str = "voicemail.wav",
        language: str = "en",
    ) -> bool:
        try:
            msg = EmailMessage()
            msg["Subject"] = f"New Voicemail from {caller_name or caller_number}"
            msg["From"] = self.from_address
            msg["To"] = to_email

            template = _get_template("voicemail_notification", language)
            body = template.render(
                mailbox_number=mailbox_number,
                caller_name=caller_name,
                caller_number=caller_number,
                duration_seconds=duration_seconds,
            )
            msg.set_content(body)

            if self.attach_audio and audio_data:
                msg.add_attachment(
                    audio_data,
                    maintype="audio",
                    subtype="wav",
                    filename=audio_filename,
                )

            with smtplib.SMTP(self.host, self.port) as smtp:
                if self.user and self.password:
                    smtp.login(self.user, self.password)
                smtp.send_message(msg)

            logger.info(
                "voicemail_email_sent",
                to=to_email,
                mailbox=mailbox_number,
                caller=caller_number,
                language=language,
            )
            return True
        except Exception as e:
            logger.error(
                "voicemail_email_failed",
                to=to_email,
                error=str(e),
            )
            return False
