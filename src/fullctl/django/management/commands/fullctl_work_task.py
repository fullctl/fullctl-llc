import os
import threading
import time
import traceback

import django.db
import psycopg
import structlog
from django.conf import settings
from django.utils import timezone

from fullctl.django.management.commands.base import CommandError, CommandInterface
from fullctl.django.models import Task, TaskHeartbeat
from fullctl.django.tasks.orm import (
    TaskAlreadyStarted,
    TaskClaimed,
    claim_task,
    fetch_task,
    set_task_as_failed,
    specify_task,
    work_task,
)
from fullctl.django.util import log_db_connection_stats

TASK_TRACK_INTERVAL_SECONDS = getattr(settings, "TASK_TRACK_INTERVAL_SECONDS", 10)
TASK_TRACK_CHECK_INTERVAL = getattr(settings, "TASK_TRACK_CHECK_INTERVAL", 0.01)
DB_STATS_INTERVAL_SECONDS = getattr(settings, "TASK_DB_STATS_INTERVAL_SECONDS", 60)
log = structlog.get_logger("django")


class Command(CommandInterface):
    help = "Process the specified task"

    always_commit = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = threading.Event()
        self.heartbeat_task_id = None
        self.heartbeat_cleanup = False
        self.thread = None
        self.thread_running = False

    @property
    def worker_id(self) -> str:
        # process id
        return str(os.getpid())

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("task_id", nargs="?")

        # interval argument
        parser.add_argument(
            "-i",
            "--poll-interval",
            help="delay between polling for tasks (seconds) when self selecting.",
            type=float,
            default=3.0,
        )

        # option to only self-select once
        parser.add_argument(
            "--once",
            help="Only self-select once, do not poll for additional tasks.",
            action="store_true",
        )

        parser.add_argument(
            "-t",
            "--max-tasks",
            help="Exit after processing this many tasks (to allow respawning). This is only used when self-selecting.",
            type=int,
            # 0 means unlimited
            default=1000,
        )

    def handle(self, *args, **kwargs):
        self.task_id = kwargs.get("task_id")
        self.poll_interval = float(kwargs.get("poll_interval")) or 3.0
        self.once = kwargs.get("once")
        self.max_tasks = int(kwargs.get("max_tasks") or 0)
        try:
            # Start the heartbeat thread once at the beginning
            self.start_heartbeat_thread()

            # this will run the normal command handler
            # and also execute the task if the task_id is
            # specified in the arguments.
            #
            # it sets up some instance properties, so poll_tasks
            # is decoupled from the main handler
            super().handle(*args, **kwargs)

            # if task_id was not specified, it means the worker
            # is "self-selecting" and will poll for tasks
            # based on the poll_interval
            if not self.task_id:
                self.poll_tasks()
            else:
                self.finalize_task_processing(int(self.task_id))

        except KeyboardInterrupt:
            log.info("Keyboard interrupt received, stopping worker")
            self.stop_heartbeat_thread()
            # Re-raise to allow the command to exit
            raise
        except Exception as exc:
            log.exception("Error in task run", exc=exc)
            self.stop_heartbeat_thread()
            self.handle_outer_error(exc)

    def finalize_task_processing(self, task: int | Task):
        """
        Handles the finalization of the task processing
        Setting the task as failed if an error occurred

        Will also transport the error to the task if it the
        error occurred outside of the task execution logic
        """

        if isinstance(task, int):
            task = Task.objects.get(id=task)

        if getattr(self, "error", None) and not task.error:
            # failure, but wasn't within the context
            # of the task execution logic, transfer error
            # to task
            set_task_as_failed(task, self.error)

        if task.error:
            self.log_info("Task failed")
            self.log_error(task.error)
        else:
            self.log_info("Task finished")

        task.save()

        # Instead of stopping the thread, just clear the task ID
        self.clear_heartbeat_task(cleanup=True)

        # wait for the heartbeat to clear
        # this is to avoid race conditions
        max_wait = 10
        while self.heartbeat_task_id:
            time.sleep(0.1)
            max_wait -= 0.1
            if max_wait <= 0:
                # TODO: This should never happen. Do we just exit the command here?
                log.warning(
                    "Heartbeat tracker object not cleared after 10 seconds, continuing anyway"
                )
                break

    def track_task_processing(self):
        """
        Track the task processing by continuously updating the task heartbeat.

        This function runs in a separate thread and periodically updates the
        `TaskHeartbeat` record for the current task to indicate it's still running.
        The heartbeat is used to detect "zombie" tasks that may have died without
        proper cleanup.

        The update frequency is controlled by TASK_TRACK_INTERVAL_SECONDS (default: 10s),
        while the thread checks for the stop signal at TASK_TRACK_CHECK_INTERVAL (default: 0.01s)
        intervals to ensure responsive shutdown.

        The function will run until the stop_event is set by stop_heartbeat_thread().
        """
        last_update = 0
        last_task_id = None
        heartbeat = None
        last_db_stats_update = 0

        self.thread_running = True

        while not self.stop_event.is_set():
            current_time = time.time()
            current_task_id = self.heartbeat_task_id

            # Only update the heartbeat when there's an active task and the interval has passed
            if (
                current_task_id
                and current_time - last_update >= TASK_TRACK_INTERVAL_SECONDS
            ):
                try:
                    # Close old connections before creating a new one
                    # This helps prevent DB connection leaks
                    django.db.close_old_connections()

                    # If task has changed or there's a cleanup flag, handle the old one first
                    if last_task_id and last_task_id != current_task_id and heartbeat:
                        if self.heartbeat_cleanup:
                            heartbeat.delete()
                            self.heartbeat_cleanup = False
                        heartbeat = None

                    # Create or update the heartbeat for the current task
                    heartbeat, _ = TaskHeartbeat.objects.update_or_create(
                        task_id=current_task_id,
                        defaults={
                            "timestamp": timezone.now(),
                        },
                    )

                    last_update = current_time
                    last_task_id = current_task_id
                except Exception as exc:
                    log.exception("Error in heartbeat loop", exc=exc)

            # If there's a cleanup request but no active task, clean up the last heartbeat
            elif (
                not current_task_id
                and self.heartbeat_cleanup
                and heartbeat
                and last_task_id
            ):
                try:
                    django.db.close_old_connections()
                    heartbeat.delete()
                    heartbeat = None
                    last_task_id = None
                    self.heartbeat_cleanup = False
                except Exception as exc:
                    log.exception("Error cleaning up heartbeat", exc=exc)
            
            # Log database connection statistics once per minute
            if current_time - last_db_stats_update >= DB_STATS_INTERVAL_SECONDS:
                try:
                    context = {}
                    if current_task_id:
                        context = {"task_id": current_task_id}
                    
                    log_db_connection_stats(context)
                    last_db_stats_update = current_time
                except Exception as exc:
                    log.exception("Error logging database stats", exc=exc)

            # Short sleep to check for stop event more frequently
            time.sleep(TASK_TRACK_CHECK_INTERVAL)

        # Clean up any remaining heartbeat when thread is stopping
        if heartbeat and self.heartbeat_cleanup:
            try:
                django.db.close_old_connections()
                heartbeat.delete()
            except Exception as exc:
                log.exception("Error cleaning up heartbeat on thread stop", exc=exc)

        self.thread_running = False

    def start_heartbeat_thread(self):
        """
        Start the heartbeat tracking thread if it's not already running.

        This thread will run for the lifetime of the command and handle
        heartbeats for all tasks.
        """
        # Only start if not already running
        if not self.thread_running:
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.track_task_processing)
            # Make thread exit when main thread exits
            self.thread.daemon = True
            self.thread.start()

    def stop_heartbeat_thread(self):
        """
        Stop the heartbeat tracking thread completely.
        Should only be called when the command is completely done.
        """
        if self.thread_running:
            self.stop_event.set()
            if self.thread and self.thread.is_alive():
                self.thread.join()

    def start_heartbeat(self, task_id: int | None = None):
        """
        Set the active task for the heartbeat thread.

        Args:
            task_id: The ID of the task to track. If None, uses self.task_id.
        """
        self.heartbeat_task_id = task_id or self.task_id
        self.heartbeat_cleanup = False

    def clear_heartbeat_task(self, cleanup: bool = False):
        """
        Clear the current task ID from the heartbeat thread.
        If cleanup is True, will delete the heartbeat record.
        """
        self.heartbeat_cleanup = cleanup
        self.heartbeat_task_id = None

    def stop_heartbeat(self, cleanup: bool = False):
        """
        Legacy method, now just clears the task ID.
        Maintained for backwards compatibility.
        """
        self.clear_heartbeat_task(cleanup)

    def before_run(self):
        """
        Hooks into the before_run method to set the active task
        when a specific task is being processed
        """
        super().before_run()
        if self.task_id:
            self.start_heartbeat()

    def after_run(self):
        """
        Hooks into the after_run method to clear the active task
        when a specific task is finished
        """
        super().after_run()
        if self.task_id:
            self.clear_heartbeat_task()

    def run(self, *args, **kwargs):
        """
        Execute the specified task
        """
        if not self.task_id:
            return

        task = specify_task(Task.objects.get(id=self.task_id))
        self.log_info(f"Processing {task}")

        try:
            work_task(task)
        except (TaskClaimed, TaskAlreadyStarted):
            log.debug("Task already claimed or started by another worker", task=task)
            return
        finally:
            self.finalize_task_processing(task)

    def poll_tasks(self):
        """
        Polls for tasks and processes them
        """
        self.log_info("Worker " + self.worker_id + " polling for tasks.")
        tasks_processed = 0

        while True:
            self.error = None
            task = None
            try:
                task = fetch_task()
                if task and not task.queue_id:
                    claim_task(task)
                    task = specify_task(task)
                    self.log_info(f"Processing {task}")

                    # Set the current task ID for heartbeat
                    self.start_heartbeat(task.id)

                    work_task(task)
                    self.finalize_task_processing(task)
                    tasks_processed += 1

                    # Exit if we've reached the max tasks limit
                    if self.max_tasks > 0 and tasks_processed >= self.max_tasks:
                        self.log_info(
                            f"Worker {self.worker_id} reached task limit ({self.max_tasks}), exiting"
                        )
                        break

                    if self.once:
                        break
                else:
                    time.sleep(self.poll_interval)
            except (TaskClaimed, TaskAlreadyStarted):
                log.debug(
                    "Task already claimed or started by another worker", task=task
                )
            except Exception as exc:
                log.exception("Error polling tasks", exc=exc, typ=type(exc))
                try:
                    self.handle_outer_error(exc, task=task)
                except Exception as exc:
                    log.exception("Error in task run", exc=exc)
                    raise CommandError("Error in task run")

    def handle_outer_error(self, exc: Exception, retries: int = 5, task: Task = None):
        """
        Handles errors that happen when setting up the task for processing

        This catches issues such as temporary database failures.
        """

        try:
            if isinstance(
                exc, (psycopg.OperationalError, django.db.utils.OperationalError)
            ):
                # Close old connections to force reconnection on next DB operation
                django.db.close_old_connections()
                log.info("Closed old DB connections due to database error")

                # db issue, give time to recover
                if self.task_id:
                    time.sleep(3)
                else:
                    # just kill the worker, it'll respawn and reconnect
                    retries = 0
                    raise exc

            if task:
                # set task as failed
                set_task_as_failed(task, traceback.format_exc())
            elif self.task_id:
                task = specify_task(Task.objects.get(id=self.task_id))
                # set task as failed
                set_task_as_failed(task, traceback.format_exc())

        except Exception as exc:
            log.exception(
                f"Error in task run (error cleanup, retries={retries})", exc=exc
            )
            if retries > 0:
                self.handle_outer_error(exc, retries - 1)
                # if error is never recovered during retries
                # task will end up orphaned as `pending` and will be eventually
                # re-queued by the poller whenever the max age limit is hit.
            else:
                raise exc
