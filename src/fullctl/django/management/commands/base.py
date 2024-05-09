import logging
import traceback

import reversion
from django.core.management.base import BaseCommand
from django.db import transaction

from fullctl.django.auditlog import auditlog
from fullctl.django.models.concrete.tasks import CallCommand
from fullctl.django.tasks.orm import worker_id


class PretendMode(IOError):
    pass


class CommandInterface(BaseCommand):

    """
    Interface for fullctl commands

    - database transactions
    - auditlog enabled
    - reversion
    - task queueable
    """

    # if set to `False` command will by default run in
    # pretend mode and provide a `--commit` flag to
    # allow it to step into committal mode
    always_commit = False

    # enable auditlogging for command
    auditlog_enabled = True

    # can command be queued?
    queue_allowed = True

    @property
    def log(self):
        if not hasattr(self, "_log"):
            self._log = logging.getLogger(__name__)
        return self._log

    def add_arguments(self, parser):
        if not self.always_commit:
            parser.add_argument("--commit", action="store_true", help="Commit changes")
        if self.queue_allowed:
            parser.add_argument(
                "--queue",
                "-Q",
                action="store_true",
                help="Queue the execution of this command as a task",
            )
            parser.add_argument(
                "--timeout", type=int, help="Max execution time in queue (seconds)"
            )

    def _run(self, *args, **kwargs):
        with reversion.create_revision():
            self.run(*args, **kwargs)
            if not self.commit:
                raise PretendMode()

    @auditlog()
    def handle(self, auditlog=None, *args, **kwargs):
        self.error = None
        self.auditlog_context = auditlog
        self.output = []
        self.queue = kwargs.get("queue")

        if not self.always_commit:
            self.commit = kwargs.get("commit")
        else:
            self.commit = True

        command_kwargs = kwargs.copy()
        command_kwargs.pop("stdout", None)
        command_kwargs.pop("stderr", None)
        command_kwargs.pop("timeout", None)
        command_name = self.__class__.__module__.split(".")[-1]

        if self.queue:
            command_kwargs.pop("commit", None)
            command_kwargs.pop("queue", None)
            CallCommand.create_task(
                timeout=kwargs.get("timeout", None),
                *([command_name] + list(args)),
                **command_kwargs,
            )
            auditlog.log("command:queued")
            self.log_info(f"Command sent to queue: {command_name}")
            return

        auditlog.append_data(
            command_args=args,
            command_kwargs=command_kwargs,
            command_name=command_name,
            clean=True,
        )
        auditlog.set("info", f"{worker_id()}:{command_name}")

        sid = None
        try:
            sid = transaction.savepoint()
            self._run(*args, **kwargs)
        except PretendMode:
            if sid:
                transaction.savepoint_rollback(sid)
            else:
                transaction.rollback()

            self.log_info(
                "Command was executed in pretend mode, all changes have been rolled back. To run command in committal mode set the --commit flag"
            )
        except Exception:
            if sid:
                transaction.savepoint_rollback(sid)
            else:
                transaction.rollback()
            err_txt = traceback.format_exc()
            self.log_error(err_txt)

        if self.auditlog_enabled and self.commit:
            auditlog.append_data(output="\n".join(self.output))
            auditlog.log("command")

    def log_debug(self, msg):
        self.log.debug(msg)
        self.stdout.write(msg)

    def log_info(self, msg):
        self.log.info(msg)
        self.output.append(msg)
        self.stdout.write(msg)

    def log_error(self, msg):
        self.log.error(msg)
        self.auditlog_context.append_data(error=f"{msg}")
        self.error = msg

    def run(self, *args, **kwargs):
        raise NotImplementedError()
