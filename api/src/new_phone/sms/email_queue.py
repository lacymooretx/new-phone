import email
import imaplib
import smtplib
import uuid
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from new_phone.sms.provider_base import InboundMessage, SendResult

logger = structlog.get_logger()


@dataclass
class IMAPConfig:
    host: str
    port: int
    username: str
    password: str
    use_ssl: bool = True
    mailbox: str = "INBOX"


@dataclass
class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    from_name: str | None = None
    from_email: str | None = None


class EmailQueueProvider:
    """Email-to-queue provider using IMAP for inbound polling and SMTP for replies."""

    async def poll_inbox(self, imap_config: IMAPConfig) -> list[InboundMessage]:
        """Poll IMAP inbox for unread messages and return them as InboundMessages."""
        messages: list[InboundMessage] = []

        try:
            if imap_config.use_ssl:
                conn = imaplib.IMAP4_SSL(imap_config.host, imap_config.port)
            else:
                conn = imaplib.IMAP4(imap_config.host, imap_config.port)

            conn.login(imap_config.username, imap_config.password)
            conn.select(imap_config.mailbox)

            # Search for unseen messages
            _status, msg_ids = conn.search(None, "UNSEEN")
            if not msg_ids or not msg_ids[0]:
                conn.logout()
                return messages

            for msg_id in msg_ids[0].split():
                try:
                    _status, msg_data = conn.fetch(msg_id, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0]
                    if not isinstance(raw_email, tuple) or len(raw_email) < 2:
                        continue

                    email_body = raw_email[1]
                    if isinstance(email_body, bytes):
                        msg = email.message_from_bytes(email_body)
                    else:
                        msg = email.message_from_string(str(email_body))

                    from_addr = msg.get("From", "")
                    to_addr = msg.get("To", "")
                    subject = msg.get("Subject", "")
                    message_id = msg.get("Message-ID", str(uuid.uuid4()))

                    # Extract plain text body
                    body = self._extract_text_body(msg)
                    if subject:
                        body = f"[{subject}] {body}"

                    media_urls: list[str] = []
                    # Note: attachment handling would require saving to object storage
                    # and generating URLs; left as extension point

                    messages.append(
                        InboundMessage(
                            from_number=from_addr,
                            to_number=to_addr,
                            body=body,
                            provider_message_id=message_id,
                            media_urls=media_urls,
                        )
                    )

                    # Mark as seen
                    conn.store(msg_id, "+FLAGS", "\\Seen")

                except Exception:
                    logger.exception("email_poll_message_error", msg_id=msg_id)

            conn.logout()

        except imaplib.IMAP4.error as exc:
            logger.error("email_poll_imap_error", error=str(exc))
        except Exception:
            logger.exception("email_poll_unexpected_error")

        return messages

    async def send_reply(
        self,
        smtp_config: SMTPConfig,
        to_email: str,
        subject: str,
        body: str,
    ) -> SendResult:
        """Send an email reply via SMTP."""
        from_email = smtp_config.from_email or smtp_config.username
        from_display = smtp_config.from_name or from_email

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{from_display} <{from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            if smtp_config.use_tls:
                server = smtplib.SMTP(smtp_config.host, smtp_config.port)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_config.host, smtp_config.port)

            server.login(smtp_config.username, smtp_config.password)
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()

            return SendResult(
                provider_message_id=msg["Message-ID"] or str(uuid.uuid4()),
                status="sent",
                segments=1,
            )
        except smtplib.SMTPException as exc:
            logger.error(
                "email_send_smtp_error",
                to_email=to_email,
                error=str(exc),
            )
            return SendResult(provider_message_id="", status="failed", segments=1)
        except Exception:
            logger.exception("email_send_unexpected_error", to_email=to_email)
            return SendResult(provider_message_id="", status="failed", segments=1)

    @staticmethod
    def _extract_text_body(msg: email.message.Message) -> str:
        """Extract plain text body from an email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
