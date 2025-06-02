from flask import Blueprint, jsonify
from datetime import datetime
from core import scheduler_service as sched
from core.scheduler_service import (
    generate_execution_plan,
    calculate_schedule_metadata
)

scheduled_api_bp = Blueprint("scheduled_api", __name__)

@scheduled_api_bp.route("/api/scheduled_events")
def get_scheduled_events():
    tasks = sched.load_tasks()
    events = []

    for task in tasks:
        if not task.get("active", True):
            continue

        start = task.get("start_datetime")
        end = task.get("end_datetime")
        end_event = task.get("end_event_datetime")

        if not start or not end:
            continue

        meta = calculate_schedule_metadata(
            start,
            end,
            task.get("total_cycles", 1),
            task.get("executions_per_cycle", 1),
            task.get("execution_spacing", 0),
            task.get("cycle_every", 0),
            task.get("cycle_unit", "minutes"),
            task.get("execution_mode", "parallel")
        ) or {}

        raw_plan = generate_execution_plan(task)
        flat_plan = [e for e in raw_plan]

        events.append({
            "id": task.get("id"),
            "title": task.get("name", "Unnamed"),
            "start": start,
            "end": end_event or meta.get("estimated_end"),
            "extendedProps": {
                "description": task.get("description"),
                "execution_mode": task.get("execution_mode"),
                "total_cycles": task.get("total_cycles"),
                "executions_per_cycle": task.get("executions_per_cycle"),
                "timeout": meta.get("timeout"),
                "cycle_duration": meta.get("cycle_duration"),
                "total_duration": meta.get("total_duration"),
                "command": task.get("command"),
                "filename": task.get("filename"),
                "detach": task.get("detach"),
                "type": task.get("type"),
                "macs": task.get("macs", {}),
                "machines": task.get("machines", []),
                "execution_plan": flat_plan
            }
        })

    return jsonify(events)
