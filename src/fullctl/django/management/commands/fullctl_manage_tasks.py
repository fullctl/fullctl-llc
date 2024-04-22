from datetime import timedelta

from django.conf import settings
from django.core.management.base import CommandParser
from django.utils import timezone

from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.models import Task


class Command(CommandInterface):
    help = "Remove all tasks with status 'completed', 'failed' or 'cancelled'"

    def add_arguments(self, parser: CommandParser):
        """Add arguments to the command."""
        super().add_arguments(parser)
        subparsers = parser.add_subparsers(dest="subcommand")
        prune_parser = subparsers.add_parser("prune")
        prune_parser.add_argument(
            "--age",
            default=settings.TASK_DEFAULT_PRUNE_AGE,
            help="Number of seconds to consider for pruning",
            type=float,
        )
        prune_parser.add_argument(
            "--exclude",
            nargs="+",
            default=settings.TASK_DEFAULT_PRUNE_EXCLUDE,
            help="List of task op types to exclude from pruning",
        )
        prune_parser.add_argument(
            "--status",
            nargs="+",
            default=settings.TASK_DEFAULT_PRUNE_STATUS,
            help="List of task statuses to prune",
        )

    def run(self, *args, **options):
        """Handle the command."""
        if options["subcommand"] == "prune":
            self.prune_tasks(**options)

    def prune_tasks(self, age: int, exclude: list[str], status: list[str], **kwargs):
        """Prune tasks older than a certain age."""
        age = float(age)
        self.log_info(f"Pruning {', '.join(status)} tasks older than {age} days ...")
        qset = Task.objects.filter(
            status__in=status,
            updated__lt=timezone.now() - timedelta(days=age),
        )

        if exclude:
            self.log_info(f"Excluding tasks with op types: {exclude}")
            qset = qset.exclude(op__in=exclude)

        self.log_info(f"Pruning {qset.count()} tasks ...")

        qset.delete()
        self.log_info("Pruning complete")
