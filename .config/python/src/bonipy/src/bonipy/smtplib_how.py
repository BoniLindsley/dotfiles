#!/usr/bin/env python3

# Standard libraries.
import email.message
import logging
import getpass
import smtplib
import socket
import sys

_logger = logging.getLogger(__name__)


def get_sender() -> str:
    hostname = socket.gethostname()
    if not hostname:
        _logger.error("Unable to determine sender hostname.")
    username = getpass.getuser()
    if not username:
        _logger.error("Unable to determine sender username.")
    sender = username + "@" + hostname
    return sender


def main() -> int:
    _logger.setLevel(level=logging.DEBUG)

    sender = get_sender()

    email_message = email.message.EmailMessage()
    email_message["From"] = sender
    email_message["To"] = sender
    email_message["Subject"] = "Testing email from Python"
    email_message.set_content("No message.")

    with smtplib.SMTP("localhost") as smtp:
        smtp.send_message(email_message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
