import os
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

STORE_NAME = os.getenv("STORE_NAME", "BookStore")
STORE_EMAIL = os.getenv("STORE_EMAIL", SMTP_USERNAME)


class EmailService:

    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = ""
    ) -> bool:

        try:

            message = MIMEMultipart("alternative")

            message["Subject"] = subject
            message["From"] = f"{STORE_NAME} <{STORE_EMAIL}>"
            message["To"] = to_email

            if text_body:

                message.attach(
                    MIMEText(
                        text_body,
                        "plain"
                    )
                )

            message.attach(
                MIMEText(
                    html_body,
                    "html"
                )
            )

            server = smtplib.SMTP(
                SMTP_SERVER,
                SMTP_PORT
            )

            server.starttls()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD
            )

            server.sendmail(
                STORE_EMAIL,
                to_email,
                message.as_string()
            )

            server.quit()

            print(
                f"Email sent successfully to {to_email}"
            )

            return True

        except Exception as e:

            print(
                "EMAIL ERROR:",
                e
            )

            return False