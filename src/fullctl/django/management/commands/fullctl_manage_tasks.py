from datetime import timedelta

from django.utils import timezone

from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.models import Task


class Command(CommandInterface):
    help = "Remove all tasks with status 'completed', 'failed' or 'cancelled'"

    always_commit = True

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "age", default="30", help="Number of days to consider for pruning"
        )

    def run(self, *args, **kwargs):
        age = int(kwargs.get("age"))

        self.log_info(f"Pruning tasks older than {age} days")

        Task.objects.filter(
            status__in=["completed", "failed", "cancelled"],
            updated__lt=timezone.now() - timedelta(days=age),
        ).delete()

        self.log_info("Pruning complete")
