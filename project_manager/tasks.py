from celery import shared_task, chain, group
from django.contrib.auth import get_user_model
from email.message import EmailMessage
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.templatetags.static import static
from django.conf import settings
import base64
import os

@shared_task(bind=True, max_retries=2)
def send_signup_email(self, email_to):
    try:
        user = get_user_model().objects.get(email=email_to)
        subject = 'Welcome to Team Information'
        user_name = user.username
        domain = 'www.teaminformation.com'
        html_template = 'project_manager/emails/sign_up_email.html'
        
        # Encode the image file
        image_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'email_logo.jpg')
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        # Add encoded image to context
        context = {
            'username' : user_name,
            'domain' : domain,
            'logo_base64': encoded_image
        }

        # Render email template with provided context
        html_content = render_to_string(html_template, context)
        text_content = strip_tags(html_content)

        # Send email
        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email_to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    except Exception as exc:
        # Retry the task twice in case of failure
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def send_notification_email(self, email_to, respond, producer):
    try:
        user = get_user_model().objects.get(email=email_to)
        subject = 'You have notifications'
        user_name = user.username
        domain = 'www.teaminformation.com'
        html_template = 'project_manager/emails/notification_email.html'
        
        image_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'email_logo.jpg')
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        context = {
            'username' : user_name,
            'respond': respond,
            'producer': producer,
            "domain" : domain,
            'logo_base64': encoded_image
        }

        html_content = render_to_string(html_template, context)
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email_to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    except Exception as exc:
        raise self.retry(exc=exc)
