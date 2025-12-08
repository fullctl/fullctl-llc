import asyncio
import uuid

import django.db
import psycopg
import reversion
import structlog
import time
from django.conf import settings
from asgiref.sync import sync_to_async

from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.tasks.orm import (
    TaskClaimed,
    claim_task,
    cleanup_orphaned_running_tasks,
    fetch_task,
    progress_schedules,
    tasks_max_time_reached,
)

log = structlog.get_logger("django")


class Worker:
    """
    Async task processor.

    Will run fullctl_work_task command async through asyncio.subprocess
    """

    def __init__(
        self,
        self_selecting: bool = False,
        poll_interval: float = 3.0,
        max_tasks: int = 0,
    ):
        self.id = f"{uuid.uuid4()}"[:8]
        self.task = None
        self.process = None
        self.self_selecting = self_selecting
        self.poll_interval = poll_interval
        self.max_tasks = max_tasks

    def set_task(self, task):
        if task and self.task:
            raise OSError("Worker has already been assiged a task")
        self.task = task
        self.process = None

    async def work(self):
        """
        Starts the worker on the tasks or waits for the currently
        assigned task to complete.

        Task is assigned through set_task
        """

        if not self.task and not self.self_selecting:
            return
        if not self.process:
            # no process has been spawned yet, run the command
            await self._run_command()
        else:
            # process has been spawned, check if it is done
            if self.process.returncode is not None:
                # its done, set task to None, indicating
                # that the worker is ready for more work
                self.set_task(None)

    async def _run_command(self):
        task = self.task
        cmd = [
            "python",
            "manage.py",
            "fullctl_work_task",
        ]

        if task:
            cmd.append(str(task.id))

        if self.self_selecting:
            cmd.extend(["--poll-interval", str(self.poll_interval)])

            # Add max-tasks parameter if configured
            if self.max_tasks > 0:
                cmd.extend(["--max-tasks", str(self.max_tasks)])

        p = await asyncio.create_subprocess_shell(
            " ".join(cmd),
        )
        self.process = p
        # print("Worker", self.id, p.pid, "subprocess spawned")


class Command(CommandInterface):
    help = "Process task queue"

    always_commit = True

    @property
    def worker_available(self):
        for worker in self.workers:
            if not worker.task:
                return True
        return False

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "-w", "--workers", help="number of concurrent  workers", type=int, default=1
        )
        parser.add_argument(
            "-i",
            "--poll-interval",
            help="delay between polling for tasks (seconds)",
            type=float,
            default=3.0,
        )
        parser.add_argument(
            "-p",
            "--processes",
            help="will spawn self selecting workers as subprocesses",
            type=int,
            default=0,
        )
        parser.add_argument(
            "-t",
            "--max-tasks-per-process",
            help="respawn self-selecting workers after processing this many tasks",
            type=int,
            # 0 means unlimited
            default=1000,
        )

    def _run(self, *args, **kwargs):
        self.sleep_interval = 0.5
        self.poll_interval = float(kwargs.get("poll_interval")) or 3.0
        self.all_workers_busy = False
        self.workers_num = int(kwargs.get("workers"))
        self.processes = int(kwargs.get("processes"))
        self.max_tasks_per_process = int(kwargs.get("max_tasks_per_process") or 0)

        # if processes are > 0, force workers to 0
        if self.processes > 0:
            self.workers_num = 0

        self.log_info(
            f"Starting task queue poller, {self.workers_num} workers, {self.processes} self-selecting workers, "
            f"poll interval {self.poll_interval} seconds, sleep interval {self.sleep_interval} seconds, "
            f"respawning self-selecting workers after {self.max_tasks_per_process} tasks"
            if self.max_tasks_per_process > 0
            else ""
        )

        self.workers = [Worker() for i in range(0, self.workers_num)]

        # instanctatie self selecting workers
        self.self_selecting_workers = [
            Worker(
                self_selecting=True,
                poll_interval=self.poll_interval,
                max_tasks=self.max_tasks_per_process,
            )
            for i in range(0, self.processes)
        ]

        async def _main():
            # spawn self selecting workers as subprocesses
            if self.self_selecting_workers:
                self.log_info(
                    f"Spawning {len(self.self_selecting_workers)} self selecting workers"
                )
                await asyncio.gather(
                    *[
                        asyncio.create_task(worker.work())
                        for worker in self.self_selecting_workers
                    ]
                )

            await asyncio.gather(
                asyncio.create_task(self._poll_tasks()),
                asyncio.create_task(self._process_workers()),
                asyncio.create_task(self._progress_schedules()),
                asyncio.create_task(self._monitor_self_selecting_workers()),
            )

        asyncio.run(_main())

    async def perform_cleanup(self):
        """
        Performs cleanup of tasks that have reached their max time or are orphaned.

        This is rate limited to prevent excessive database queries. 

        The period can be configured with the `TASK_CLEANUP_INTERVAL_SECONDS` setting.
        """
        period = settings.TASK_CLEANUP_INTERVAL_SECONDS
        last_check = getattr(self, "last_cleanup_check", 0)
        if time.time() - last_check < period:
            return
        self.last_cleanup_check = time.time()
        await sync_to_async(tasks_max_time_reached)()
        await sync_to_async(cleanup_orphaned_running_tasks)()

    async def _monitor_self_selecting_workers(self):
        """Monitor self-selecting workers and respawn them when they exit"""
        while True:
            try:
                await asyncio.sleep(self.sleep_interval)

                await self.perform_cleanup()

                for i, worker in enumerate(self.self_selecting_workers):
                    # Check if the worker process has exited
                    if worker.process and worker.process.returncode is not None:
                        self.log_info(
                            f"Self-selecting worker {worker.id} exited, respawning"
                        )
                        # Create a new worker
                        self.self_selecting_workers[i] = Worker(
                            self_selecting=True,
                            poll_interval=self.poll_interval,
                            max_tasks=self.max_tasks_per_process,
                        )
                        # Start the new worker
                        await self.self_selecting_workers[i].work()
            except Exception as exc:
                log.exception("Error monitoring self-selecting workers", exc=exc)

    async def _process_workers(self):
        while True:
            try:
                await asyncio.sleep(self.sleep_interval)

                for worker in self.workers:
                    await worker.work()
            except Exception as exc:
                log.exception("Error processing workers", exc=exc)

    async def _poll_tasks(self):
        if not self.workers:
            self.log_info(
                "Since workers are configured to 0, will not poll for tasks, but idle instead."
            )

        while True:
            task = None
            try:
                await asyncio.sleep(self.poll_interval)

                if not self.workers:
                    continue

                if not self.worker_available:
                    if not self.all_workers_busy:
                        self.log_info("All workers busy")
                        self.all_workers_busy = True
                    continue
                else:
                    if self.all_workers_busy:
                        self.log_info("Worker available")
                    self.all_workers_busy = False

                await self.perform_cleanup()
                
                task = await sync_to_async(fetch_task)()

                if not task or task.queue_id:
                    continue

                self.log_info(f"New task {task}")

                # django call needs to be wrapped in sync_to_async

                await sync_to_async(self.claim_task)(task)

                await self.delegate_task(task)
            except (psycopg.OperationalError, django.db.utils.OperationalError) as exc:
                log.exception("Error polling tasks (db error)", exc=exc)
                # Close and reestablish connections
                await sync_to_async(django.db.close_old_connections)()
                self.log_info("Closed old DB connections, will retry after delay")
                await asyncio.sleep(3)
            except Exception as exc:
                log.exception("Error polling tasks", exc=exc)

    async def _progress_schedules(self):
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await sync_to_async(progress_schedules)()
            except (psycopg.OperationalError, django.db.utils.OperationalError) as exc:
                log.exception("Error progressing schedules (db error)", exc=exc)
                # Close and reestablish connections
                await sync_to_async(django.db.close_old_connections)()
                self.log_info("Closed old DB connections, will retry after delay")
                await asyncio.sleep(3)  # Give some time before retrying
            except Exception as exc:
                log.exception("Error progressing schedules", exc=exc)
                await asyncio.sleep(1)  # Brief delay on general errors

    def claim_task(self, task):
        try:
            with reversion.create_revision():
                self.log_info(f"Claiming task {task}")
                return claim_task(task)
        except TaskClaimed:
            if not task.queue_id:
                err = "Task has a claim, but no queue id - likely in the middle of being claimed by other worker"
                self.log_debug(err)
            self.log_debug("Task already claimed, skipping")

    async def delegate_task(self, task):
        self.log_info(f"Delegating task {task}")
        while True:
            await asyncio.sleep(0.5)
            for worker in self.workers:
                if not worker.task:
                    worker.set_task(task)
                    return
