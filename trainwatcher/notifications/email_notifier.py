"""SMTP email notifier."""

from dataclasses import dataclass
import smtplib
from email.message import EmailMessage
from typing import Optional


@dataclass
class EmailNotifier:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    sender: str
    recipient: str
    use_tls: bool = True
    subject: str = "TrainWatcher Notification"

    def send(self, message: str) -> None:
        if not message:
            raise ValueError("message must be a non-empty string")

        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg["Subject"] = self.subject
        msg.set_content(message)

        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password or "")
            smtp.send_message(msg)
