from flask import render_template, request, redirect, url_for
from . import scheduler_bp
import os
import json
from datetime import datetime
from core import scheduler_service as sched
from modules.scheduler.services import create_task_from_form  # Make sure this import path is correct

# Paths
HOSTS_FILE = "modules/hosts/data/hosts.json"
SCRIPTS_DIR = "modules/scripts/scripts_drive"

@scheduler_bp.route("/scheduler", methods=["GET", "POST"])
def scheduler():
    if request.method == "POST":
        form_data = request.form
        print("📥 Received Scheduled Task:", dict(form_data))

        try:
            # Create task from form
            new_task = create_task_from_form(form_data)

            # Attach MAC addresses
            new_task["macs"] = {
                ip: form_data.get(f"mac_for_{ip}")
                for ip in new_task["machines"]
                if form_data.get(f"mac_for_{ip}")
            }

            # Compute metadata (timeout, duration, end)
            metadata = sched.calculate_schedule_metadata(
                new_task["start_datetime"],
                new_task["end_datetime"],
                new_task["total_cycles"],
                new_task["executions_per_cycle"],
                new_task["execution_spacing"],
                new_task["cycle_every"],
                new_task["cycle_unit"],
                new_task["execution_mode"]
            )
            if metadata:
                new_task.update(metadata)

            # Save task: new or update
            if form_data.get("edit_id"):
                new_task["id"] = form_data["edit_id"]
                sched.update_task(new_task["id"], new_task)
            else:
                sched.save_task(new_task)

            print("✅ Task saved successfully.")

        except Exception as e:
            print("❌ Error while saving task:", e)

        return redirect(url_for("scheduler.scheduler"))

    # GET → Render the form
    scripts = []
    if os.path.isdir(SCRIPTS_DIR):
        scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith((".sh", ".py"))]

    hosts = []
    if os.path.exists(HOSTS_FILE):
        with open(HOSTS_FILE, "r") as f:
            hosts = json.load(f)

    return render_template("scheduler/scheduler.html",
                           edit_task=None,
                           scripts=scripts,
                           hosts=hosts)
