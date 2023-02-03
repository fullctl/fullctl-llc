from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.models import Task
from fullctl.django.tasks.orm import specify_task, work_task


class Command(CommandInterface):
    help = "Process the specified task"

    always_commit = True

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("task_id", nargs="?")

    def run(self, *args, **kwargs):
        task_id = kwargs.get("task_id")

        task = specify_task(Task.objects.get(id=task_id))

        self.log_info(f"Processing {task}")

        work_task(task)

        if task.error:
            self.log_info("Task failed")
            self.log_error(task.error)
        else:
            self.log_info("Task finished")
