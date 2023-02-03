from django.core.mail import EmailMessage
from django.utils.html import strip_tags


def send_plain(subject, message, from_addr, recipients, **kwargs):
    message = EmailMessage(
        strip_tags(subject), strip_tags(message), from_addr, recipients, **kwargs
    )

    message.send(fail_silently=False)
