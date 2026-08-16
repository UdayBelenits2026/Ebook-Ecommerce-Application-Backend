import os

import resend
from dotenv import load_dotenv


# Load variables from local .env file
load_dotenv()


# ============================================================
# RESEND CONFIGURATION
# ============================================================

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL",
    "onboarding@resend.dev"
)


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(
    to_email: str,
    otp: str
) -> bool:

    # Check API key
    if not RESEND_API_KEY:

        print(
            "RESEND EMAIL ERROR: "
            "RESEND_API_KEY is not configured."
        )

        return False

    try:

        # Configure Resend API key
        resend.api_key = RESEND_API_KEY

        # Email configuration
        params: resend.Emails.SendParams = {

            "from": RESEND_FROM_EMAIL,

            "to": [
                to_email
            ],

            "subject": "BookStore - Email Verification OTP",

            "html": f"""
                <!DOCTYPE html>

                <html>

                <head>

                    <meta charset="UTF-8">

                    <title>
                        BookStore Email Verification
                    </title>

                </head>

                <body style="
                    margin: 0;
                    padding: 0;
                    background-color: #f4f6f8;
                    font-family: Arial, Helvetica, sans-serif;
                ">

                    <div style="
                        max-width: 500px;
                        margin: 40px auto;
                        background: #ffffff;
                        border-radius: 12px;
                        padding: 35px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                    ">

                        <div style="
                            text-align: center;
                            margin-bottom: 25px;
                        ">

                            <h1 style="
                                margin: 0;
                                color: #111827;
                                font-size: 28px;
                            ">
                                📚 BookStore
                            </h1>

                            <p style="
                                color: #6b7280;
                                margin-top: 8px;
                            ">
                                Email Verification
                            </p>

                        </div>


                        <p style="
                            color: #333333;
                            font-size: 16px;
                        ">

                            Hello,

                        </p>


                        <p style="
                            color: #555555;
                            font-size: 15px;
                            line-height: 1.6;
                        ">

                            Thank you for registering with
                            <strong>BookStore</strong>.

                            Please use the verification code below
                            to verify your email address.

                        </p>


                        <div style="
                            text-align: center;
                            margin: 30px 0;
                        ">

                            <div style="
                                display: inline-block;
                                background-color: #111827;
                                color: #ffffff;
                                padding: 18px 30px;
                                border-radius: 10px;
                                font-size: 32px;
                                font-weight: bold;
                                letter-spacing: 8px;
                            ">

                                {otp}

                            </div>

                        </div>


                        <p style="
                            color: #555555;
                            font-size: 15px;
                            line-height: 1.6;
                        ">

                            This verification code is valid for
                            <strong>10 minutes</strong>.

                        </p>


                        <p style="
                            color: #777777;
                            font-size: 14px;
                            line-height: 1.6;
                        ">

                            If you did not create an account with
                            BookStore, you can safely ignore this email.

                        </p>


                        <hr style="
                            border: none;
                            border-top: 1px solid #eeeeee;
                            margin: 30px 0;
                        ">


                        <p style="
                            text-align: center;
                            color: #999999;
                            font-size: 12px;
                            margin: 0;
                        ">

                            © 2026 BookStore

                        </p>

                    </div>

                </body>

                </html>
            """
        }


        # ====================================================
        # SEND THROUGH RESEND
        # ====================================================

        response = resend.Emails.send(
            params
        )


        # Log response without exposing API key
        print(
            f"OTP email accepted by Resend "
            f"for {to_email}"
        )

        print(
            f"Resend response: {response}"
        )


        return True


    except Exception as e:

        print(
            f"RESEND EMAIL ERROR: {type(e).__name__}: {e}"
        )

        return False