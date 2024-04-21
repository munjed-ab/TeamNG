import asyncio
import aiosmtplib
from django.conf import settings
from email.message import EmailMessage
from django.core.mail import EmailMultiAlternatives
import threading

def send_email_async(instance):
    post = instance
    post_email = post.email
    email_subject = 'Email Title'
    email_body = 'Email Body'

    # Use a separate thread to send the email asynchronously
    email_thread = threading.Thread(target=send_email, args=(email_subject, email_body, post_email))
    email_thread.start()

def send_email(subject, message, recipient):
    email = EmailMultiAlternatives(subject, '', to=[recipient])
    email.attach_alternative(message, 'text/html')
    email.send()




async def send_email_async_old(msg):

    # Establish connection to SMTP server
    smtp = aiosmtplib.SMTP(hostname=settings.EMAIL_HOST, port=settings.EMAIL_PORT)
    await smtp.connect()

    # Secure the connection if TLS is supported
    if smtp.supports_tls:
        await smtp.starttls()

    # Login to the SMTP server
    await smtp.login(settings.DEFAULT_FROM_EMAIL, settings.EMAIL_HOST_PASSWORD)

    # Send the email
    await smtp.send_message(msg)

    # Close the connection
    await smtp.quit()

# Example usage
async def signup_email(user):
    msg = EmailMessage()
    msg.set_content(f"Hey {user.username}, your account is ready for you.")
    msg["Subject"] = "Welcome"
    msg["From"] = settings.DEFAULT_FROM_EMAIL
    msg["To"] = user.email
    await send_email_async(msg)



# def send_email(to):
#     msg = EmailMessage()
#     msg.set_content(f"Hey {to.username}, your account is ready for you.")
#     msg["Subject"] = "Wellcome"
#     msg["From"] = settings.DEFAULT_FROM_EMAIL
#     msg["To"] = to.email

#     context = ssl.create_default_context()

#     with smtplib.SMTP(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT) as server:
#         server.set_debuglevel(1)
#         server.starttls(context=context)
#         server.login(settings.DEFAULT_FROM_EMAIL, settings.EMAIL_HOST_PASSWORD)
#         server.send_message(msg)
