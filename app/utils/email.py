import smtplib
from email.message import EmailMessage
from app.config.settings import settings

def send_otp_email(to_email: str, otp: str):
    msg = EmailMessage()
    msg.set_content(f"Your Book Store verification code is: {otp}. It expires in 10 minutes.")
    msg['Subject'], msg['From'], msg['To'] = 'Account Verification', settings.SMTP_USERNAME, to_email
    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")