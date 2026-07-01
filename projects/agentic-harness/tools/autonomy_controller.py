# lathe-generated module — do not edit by hand


def decide_next_action(tasks):
    if not isinstance(tasks, list):
        tasks = []

    for i, task in enumerate(tasks):
        status = task.get('status', '')
        if status == 'pending':
            return {'action': 'run', 'task': task, 'reason': 'run next pending task'}

    for i, task in enumerate(tasks):
        status = task.get('status', '')
        if status == 'in_progress':
            return {'action': 'run', 'task': task, 'reason': 'resume in-progress task'}

    for i, task in enumerate(tasks):
        status = task.get('status', '')
        if status == 'blocked':
            return {'action': 'halt', 'task': task, 'reason': 'blocked task needs attention'}

    return {'action': 'plan', 'task': None, 'reason': 'board empty - request next spec'}

