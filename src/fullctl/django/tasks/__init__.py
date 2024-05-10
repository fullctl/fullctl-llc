import structlog

log = structlog.get_logger("django")


TASK_MODELS = {}


def register(cls):
    TASK_MODELS[cls.HandleRef.tag] = cls
    return cls


def specify_task(task):
    try:
        task_model = TASK_MODELS[task.op]
        return task_model.objects.get(id=task.id)
    except KeyError:
        log.error("Task operation not found", task_op=task.op)


def create_tasks_from_json(config, parent=None, user=None, org=None, tasks=None):
    """
    Creates tasks from JSON config
    """

    if not tasks:
        tasks = []

    task_configs = config.get("tasks", [])

    for task_config in task_configs:
        op = task_config.get("op")

        model = TASK_MODELS.get(op)
        if not model:
            log.error("Task operation not found", task_op=op)
            continue

        param = task_config.get("param", {})
        args = param.get("args", [])
        kwargs = param.get("kwargs", {})
        timeout = task_config.get("timeout", 0)

        task = model.create_task(timeout=timeout, user=user, org=org, *args, **kwargs)

        tasks.append(task)

        create_tasks_from_json(
            task_config, parent=task, user=user, org=org, tasks=tasks
        )

    return tasks


def requeue(generic_task):
    """
    Method to re-queue a task. This will create a new task with the same arguments.
    """
    task = specify_task(generic_task)
    param = task.param
    new_task = task.__class__.create_task(
        *param["args"], **param["kwargs"], user=task.user, org=task.org, requeued=True
    )
    return new_task
