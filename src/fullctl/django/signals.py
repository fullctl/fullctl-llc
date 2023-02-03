# from django.contrib.auth.signals import user_logged_in

import reversion
from django.db.models.signals import post_delete
from django.dispatch import receiver
from reversion.signals import post_revision_commit

import fullctl.django.auditlog as auditlog


def auditlog_on_save(**kwargs):
    """
    audit log object changes whenever a new version
    of an object is saved
    """

    versions = kwargs.get("versions")
    for version in versions:
        instance = version.object
        model = instance.__class__

        if not auditlog.is_enabled(model):
            continue

        tag = auditlog.model_tag(model)

        action = f"{tag}:save"

        with auditlog.Context() as ctx:
            ctx.log(action, log_object=instance)


post_revision_commit.connect(auditlog_on_save)


@receiver(post_delete)
def auditlog_on_delete(sender, **kwargs):
    """
    auditlog object deletions
    """

    if not reversion.is_registered(sender):
        return

    if not auditlog.is_enabled(sender):
        return

    tag = auditlog.model_tag(sender)

    action = f"{tag}:delete"
    instance = kwargs.get("instance")

    with auditlog.Context() as ctx:
        ctx.log(action, log_object=instance)
