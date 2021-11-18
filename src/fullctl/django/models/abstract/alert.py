from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from fullctl.django.mail import send_plain
from fullctl.django.models.abstract.base import HandleRefModel

ALERT_RECIPIENT_TYPE = (("email", _("Email")),)

# XXX this needs to be adapted to the new task system


class AlertGroup(HandleRefModel):

    """
    Describes a group of recipients for alert notifications
    """

    name = models.CharField(max_length=255, help_text=_("Group name"))

    class Meta:
        abstract = True

    class HandleRef:
        tag = "alertgrp"

    @property
    def recipients(self):
        raise NotImplementedError("Should return recipient set")

    @property
    def log_class(self):
        raise NotImplementedError("Should return AlertLog type model")

    @property
    def log_recipient_class(self):
        raise NotImplementedError("Should return AlertRecipient type model")

    def create_log(self, subject, message):
        return self.log_class.objects.create(
            alertgrp=self, subject=subject, message=message
        )

    def notify(self, subject, message):
        """
        Notifies all recipients in this alert group

        Arguments:
            - subject (str): message subject
            - message (str): plain message text
        """

        log = self.create_log(subject, message)

        for recipient in self.recipients:
            recipient.notify(subject, message)
            log.alertlogrcp_set.add(
                self.log_recipient_class(
                    typ=recipient.typ,
                    recipient=recipient.recipient,
                ),
                bulk=False,
            )
        return log


class AlertRecipient(HandleRefModel):

    """
    Describes a recipient for an alert notification.

    The extended model needs to specify a ForeignKey called
    `alertgrp` that describes a realtion ship to an AlertGroup type
    model
    """

    typ = models.CharField(max_length=255, choices=ALERT_RECIPIENT_TYPE)
    recipient = models.CharField(
        max_length=255, help_text=_("Recipient address (e-mail address for example)")
    )

    class Meta:
        abstract = True

    class HandleRef:
        tag = "alertrcp"

    def notify(self, subject, message):
        """
        Sends a notification to the recipient

        Arguments:
            - subject (str): message subject
            - message (str): plain message text
        """

        fn_notify = getattr(self, f"notify_{self.typ}")
        fn_notify(subject, message)
        return (self.typ, self.recipient)

    def notify_email(self, subject, message):
        send_plain(
            subject,
            message,
            settings.EMAIL_DEFAULT_FROM,
            [self.recipient],
            reply_to=[settings.EMAIL_NOREPLY],
        )


class AlertLog(HandleRefModel):
    """
    Describes a an alert log that should log subject and message
    as well as a set of recipients
    """

    subject = models.CharField(max_length=255)
    message = models.TextField()

    class Meta:
        abstract = True

    class HandleRef:
        tag = "alertlog"

    @property
    def recipients(self):
        raise NotImplementedError("Should return recipient set")
