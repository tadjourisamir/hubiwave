from core.scheduler_service import (
    load_tasks, save_task, generate_task_id,
    calculate_schedule_metadata
)

def create_task_from_form(form_data):
    """Convert Flask form data into a task dictionary ready for saving."""    
    task_type = form_data.get("type", "command")

    task = {
        "id": form_data.get("edit_id") or generate_task_id(),
        "name": form_data.get("name"),
        "description": form_data.get("description"),
        "start_datetime": form_data.get("start_datetime"),
        "end_datetime": form_data.get("end_datetime"),
        "end_event_datetime": form_data.get("end_event_datetime"),
        "total_cycles": int(form_data.get("total_cycles", 1)),
        "cycle_every": int(form_data.get("cycle_every", 5)),
        "cycle_unit": form_data.get("cycle_unit", "seconds"),
        "execution_mode": form_data.get("execution_mode", "sequential"),
        "executions_per_cycle": int(form_data.get("executions_per_cycle", 1)),
        "execution_spacing": int(form_data.get("execution_spacing", 5)),
        "duration": int(form_data.get("duration", 5)),
        "type": task_type,
        "machines": form_data.getlist("target_ips"),
        "detach": "detach" in form_data,
        "active": "active_checkbox" in form_data
    }

    if task_type == "command":
        task["command"] = form_data.get("command_text")
    elif task_type == "script":
        task["filename"] = form_data.get("script_name")
        task["remote_name"] = form_data.get("remote_name", "script.sh")
    else:
        raise ValueError(f"Unsupported task type: {task_type}")

    return task
