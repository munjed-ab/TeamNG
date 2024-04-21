from django.db.models.signals import post_save
from .models import CustomUser, Profile
from django.dispatch import receiver


@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, profile_img='user_def.png')

@receiver(post_save, sender=CustomUser)
def create_profile(sender, instance, **kwargs):
    instance.profile.save()


# from django.dispatch import receiver
# from django.db.models.signals import post_save
# from django.core.mail import EmailMultiAlternatives
# import threading


# this way not good:
# check: https://discord.com/channels/856567261900832808/1227697668424204338
# @receiver(post_save, sender=CustomUser)
# def send_email_async(sender, instance, created, **kwargs):
#     if created:
#         post = instance
#         post_author = post.username
#         post_email = post.email
#         email_subject = 'Email Title'
#         email_body = 'Email Body'

#         # Use a separate thread to send the email asynchronously
#         email_thread = threading.Thread(target=send_email, args=(email_subject, email_body, post_email))
#         email_thread.start()

# def send_email(subject, message, recipient):
#     email = EmailMultiAlternatives(subject, '', to=[recipient])
#     email.attach_alternative(message, 'text/html')
#     email.send()

