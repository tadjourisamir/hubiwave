import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.triggers.date import DateTrigger
from apscheduler.schedulers.background import BackgroundScheduler

SCHEDULE_FILE = Path("modules/scheduler/data/scheduled_events.json")

def load_tasks():
    if not SCHEDULE_FILE.exists():
        return []
    with SCHEDULE_FILE.open("r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_tasks(tasks):
    with SCHEDULE_FILE.open("w") as f:
        json.dump(tasks, f, indent=2)

def save_task(new_task):
    tasks = load_tasks()
    tasks.append(new_task)
    save_tasks(tasks)

def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task.get("id") != task_id]
    save_tasks(tasks)

def update_task(task_id, updates):
    tasks = load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            task.update(updates)
            break
    save_tasks(tasks)

def find_task_by_id(task_id):
    tasks = load_tasks()
    return next((task for task in tasks if task.get("id") == task_id), None)

def generate_task_id():
    return str(uuid.uuid4())

def convert_to_seconds(value, unit):
    units = {
        "seconds": 1,
        "minutes": 60,
        "hours": 3600,
        "days": 86400
    }
    return value * units.get(unit, 1)

def calculate_schedule_metadata(start, end, total_cycles, executions_per_cycle, spacing, cycle_every, unit, mode):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except Exception:
        return None

    cycle_every_sec = convert_to_seconds(cycle_every, unit)
    raw_duration = (end_dt - start_dt).total_seconds()

    if mode == "sequential" and executions_per_cycle > 1:
        total_spacing = (executions_per_cycle - 1) * spacing
        timeout = max((raw_duration - total_spacing) / executions_per_cycle, 0)
        cycle_duration = timeout * executions_per_cycle + total_spacing
    else:
        timeout = raw_duration
        cycle_duration = raw_duration

    spacing_between_cycles = max((total_cycles - 1), 0) * cycle_every_sec
    total_duration = cycle_duration * total_cycles + spacing_between_cycles
    end_global = start_dt + timedelta(seconds=total_duration)

    return {
        "timeout": round(timeout, 2),
        "cycle_duration": round(cycle_duration, 2),
        "total_duration": round(total_duration, 2),
        "estimated_end": end_global.isoformat()
    }


def generate_execution_plan(task):
    start_time = datetime.fromisoformat(task["start_datetime"])
    executions_per_cycle = int(task.get("executions_per_cycle", 1))
    total_cycles = int(task.get("total_cycles", 1))
    execution_spacing = int(task.get("execution_spacing", 0))
    cycle_every = int(task.get("cycle_every", 0))
    cycle_unit = task.get("cycle_unit", "minutes")
    timeout = int(task.get("timeout", 0))
    execution_mode = task.get("execution_mode", "parallel")
    machines = task.get("machines", [])

    plan = []

    spacing_delta = timedelta(seconds=execution_spacing)
    timeout_delta = timedelta(seconds=timeout)

    if cycle_unit == "seconds":
        cycle_delta = timedelta(seconds=cycle_every)
    elif cycle_unit == "minutes":
        cycle_delta = timedelta(minutes=cycle_every)
    elif cycle_unit == "hours":
        cycle_delta = timedelta(hours=cycle_every)
    else:
        cycle_delta = timedelta(minutes=cycle_every)

    current_time = start_time

    for cycle_index in range(total_cycles):
        if execution_mode == "parallel":
            plan.append({
                "cycle": cycle_index + 1,
                "ips": machines,
                "time": current_time.isoformat()
            })
            current_time += timeout_delta + cycle_delta

        elif execution_mode == "sequential":
            for exec_index in range(executions_per_cycle):
                for ip in machines:
                    plan.append({
                        "cycle": cycle_index + 1,
                        "execution": exec_index + 1,
                        "ip": ip,
                        "time": current_time.isoformat()
                    })
                
                if exec_index < executions_per_cycle - 1:
                    current_time += timeout_delta + spacing_delta
                else:
                    current_time += timeout_delta
            current_time += cycle_delta

    return plan


def schedule_task(task, scheduler, run_callback):
    try:
        plan = generate_execution_plan(task)
    except Exception as e:
        print(f"❌ Task planning failed: {e}")
        return

    existing_job_ids = {job.id for job in scheduler.get_jobs()}
    newly_scheduled = set()

    execution_mode = task.get("execution_mode", "parallel")

    for item in plan:
        if execution_mode == "parallel":
            job_id = f"{task['id']}_cycle{item['cycle']}"
            run_at = datetime.fromisoformat(item["time"])

            if job_id in existing_job_ids or job_id in newly_scheduled:
                print(f"⚠️ Job already scheduled: {job_id} — skipping.")
                continue

            scheduler.add_job(
                func=run_callback,
                trigger=DateTrigger(run_date=run_at),
                args=[task, item["ips"], item["cycle"]],
                id=job_id,
                name=f"{task.get('name')} — Cycle {item['cycle']}",
                replace_existing=False
            )

        else:  # sequential
            job_id = f"{task['id']}_{item['ip'].replace('.', '-')}_c{item['cycle']}_e{item['execution']}"
            run_at = datetime.fromisoformat(item["time"])

            if job_id in existing_job_ids or job_id in newly_scheduled:
                print(f"⚠️ Job already scheduled: {job_id} — skipping.")
                continue

            scheduler.add_job(
                func=run_callback,
                trigger=DateTrigger(run_date=run_at),
                args=[
                    task,
                    item["ip"],
                    item["execution"] - 1,
                    task.get("executions_per_cycle", 1),
                    task.get("execution_spacing", 0)
                ],
                id=job_id,
                name=f"{task.get('name')} @ {item['ip']} [C{item['cycle']} E{item['execution']}]",
                replace_existing=False
            )

        newly_scheduled.add(job_id)
        print(f"📆 Scheduled: {job_id} at {run_at.isoformat()}")


def validate_and_schedule_tasks(scheduler, run_callback, hosts):
    tasks = load_tasks()
    now = datetime.utcnow()
    valid_tasks = []

    for task in tasks:
        print(f"🔍 Validating task: {task.get('name')} — ID: {task.get('id')}")

        if not task.get("active", True):
            print(f"⛔ Task is inactive: {task['name']}")
            continue

        task_macs = task.get("macs", {})
        valid_machines = []

        for host in hosts:
            ip = host.get("ip")
            mac = host.get("id")
            print(f"🔧 Checking: IP={ip}, MAC={mac}")
            if ip in task["machines"]:
                expected_mac = task_macs.get(ip)
                if expected_mac == mac:
                    print(f"✅ Machine OK: {ip}")
                    valid_machines.append(ip)
                else:
                    print(f"❌ MAC mismatch for {ip}: expected {expected_mac}, got {mac}")
            else:
                print(f"🚫 {ip} not in the task machine list")

        if not valid_machines:
            print(f"❌ No valid machine found for task {task['name']}")
            continue

        end = task.get("end_event_datetime") or task.get("end_datetime")
        if end and datetime.fromisoformat(end) < now:
            print(f"🕒 Task expired: {task['name']}")
            task["status"] = "expired"
            continue

        task["machines"] = valid_machines
        valid_tasks.append(task)

    print(f"🔁 Re-scheduling {len(valid_tasks)} task(s)...")
    scheduler.remove_all_jobs()

    for task in valid_tasks:
        schedule_task(task, scheduler, run_callback)

def start_scheduler(run_callback, hosts):
    scheduler = BackgroundScheduler()
    validate_and_schedule_tasks(scheduler, run_callback, hosts)
    scheduler.start()
    return scheduler
