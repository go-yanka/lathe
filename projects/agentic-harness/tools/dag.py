# lathe-generated module — do not edit by hand


def ready_tasks(tasks):
    done_ids = {task['id'] for task in tasks if task.get('status') == 'done'}
    ready_ids = []
    for task in tasks:
        if task.get('status') == 'pending':
            deps = task.get('deps', [])
            if all(dep_id in done_ids for dep_id in deps):
                ready_ids.append(task['id'])
    return ready_ids

def has_cycle(tasks):
    def detect(node_id, visiting, visited, adj):
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        
        visiting.add(node_id)
        for neighbor in adj.get(node_id, []):
            if detect(neighbor, visiting, visited, adj):
                return True
        
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    adj = {task['id']: task.get('deps', []) for task in tasks}
    all_task_ids = set(adj.keys())
    
    # Filter dependencies to ignore dangling edges as per requirements
    filtered_adj = {}
    for task_id, deps in adj.items():
        filtered_adj[task_id] = [d for d in deps if d in all_task_ids]
    
    visited = set()
    for task_id in all_task_ids:
        if task_id not in visited:
            if detect(task_id, set(), visited, filtered_adj):
                return True
    return False

