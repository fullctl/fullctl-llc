TASK_MODELS = {}


def register(cls):
    TASK_MODELS[cls.HandleRef.tag] = cls
    return cls


def specify_task(task):
    return TASK_MODELS[task.op].objects.get(id=task.id)


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
