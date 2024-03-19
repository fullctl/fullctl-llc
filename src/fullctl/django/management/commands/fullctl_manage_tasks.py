from datetime import timedelta

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from fullctl.django.models import Task


class Command(BaseCommand):
    help = "Remove all tasks with status 'completed', 'failed' or 'cancelled'"

    always_commit = True

    def add_arguments(self, parser: CommandParser):
        subparsers = parser.add_subparsers(dest="subcommand")
        prune_parser = subparsers.add_parser("prune")
        prune_parser.add_argument(
            "age", default="30", help="Number of days to consider for pruning"
        )

    def handle(self, *args, **options):
        if options["subcommand"] == "prune":
            self.prune_tasks(options["age"])

    def prune_tasks(self, age: int):
        age = int(age)
        self.stdout.write(f"Pruning tasks older than {age} days")
        Task.objects.filter(
            status__in=["completed", "failed", "cancelled"],
            updated__lt=timezone.now() - timedelta(days=age),
        ).delete()
        self.stdout.write("Pruning complete")
