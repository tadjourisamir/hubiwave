from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import os
from concurrent.futures import ThreadPoolExecutor
import datetime
import json

from core.executor import run_task  # Real SSH execution function

scripts_bp = Blueprint("scripts", __name__, template_folder="templates")

# Directories & files
SCRIPTS_DIR = "modules/scripts/scripts_drive"
HOSTS_FILE = "modules/hosts/data/hosts.json"
METADATA_FILE = "modules/scripts/data/metadata.json"
LOG_FILE = "logs/executions.log"
ALLOWED_EXTENSIONS = {".sh", ".py"}


def is_allowed(filename):
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def get_script_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def get_registered_hosts():
    if os.path.exists(HOSTS_FILE):
        with open(HOSTS_FILE) as f:
            return json.load(f)
    return []


def log_execution(entry: str):
    """Append a log line to logs/executions.log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


@scripts_bp.route("/scripts")
def list_scripts():
    metadata = get_script_metadata()
    hosts = get_registered_hosts()
    scripts = []

    if os.path.isdir(SCRIPTS_DIR):
        for fname in os.listdir(SCRIPTS_DIR):
            path = os.path.join(SCRIPTS_DIR, fname)
            if os.path.isfile(path) and is_allowed(fname):
                scripts.append({
                    "filename": fname,
                    "description": metadata.get(fname, {}).get("description", ""),
                    "modified": datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
                })

    return render_template("scripts/list.html", scripts=scripts, hosts=hosts)


@scripts_bp.route("/scripts/upload", methods=["POST"])
def upload_script():
    file = request.files.get("script_file")
    if not file:
        flash("❌ No file uploaded.")
        return redirect(url_for("scripts.list_scripts"))

    filename = file.filename
    if not is_allowed(filename):
        flash("❌ Invalid file type. Only .sh and .py are allowed.")
        return redirect(url_for("scripts.list_scripts"))

    save_path = os.path.join(SCRIPTS_DIR, filename)
    file.save(save_path)
    flash(f"✅ Script {filename} uploaded.")
    return redirect(url_for("scripts.list_scripts"))


@scripts_bp.route("/scripts/delete/<filename>", methods=["POST"])
def delete_script(filename):
    try:
        script_path = os.path.join(SCRIPTS_DIR, filename)
        if os.path.exists(script_path):
            os.remove(script_path)
            return jsonify({"status": "success", "message": f"{filename} deleted"})
        else:
            return jsonify({"status": "not_found", "message": f"{filename} not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@scripts_bp.route("/scripts/run/<filename>", methods=["POST"])
def run_script(filename):
    script_path = os.path.join(SCRIPTS_DIR, filename)
    selected_ips = request.form.getlist("target_ips")
    detach_requested = "detach" in request.form

    if not os.path.exists(script_path):
        flash(f"❌ Script not found: {filename}")
        return redirect(url_for("scripts.list_scripts"))

    if not selected_ips:
        flash("❗ No target machines selected.")
        return redirect(url_for("scripts.list_scripts"))

    all_hosts = get_registered_hosts()
    host_map = {h["ip"]: h for h in all_hosts}

    def run_for_ip(ip):
        host = host_map.get(ip)
        if not host:
            flash(f"⚠️ Machine {ip} not found in hosts.json")
            return

        # Force detach to False for scripts
        task = {
            "id": f"manual-{datetime.datetime.now().timestamp()}",
            "type": "script",
            "filename": filename,
            "remote_name": filename,
            "detach": False,
            "machines": [ip],
            "user": host.get("user", "root"),
            "port": host.get("port", 22)
        }

        print(f"[DEBUG] Running task for: {ip}")
        print(json.dumps(task, indent=2))

        try:
            run_task(task)
            flash(f"✅ {filename} executed on {ip}")
            log_execution(f"{datetime.datetime.now().isoformat()} | {ip} | {filename} | SYNC | SUCCESS")
        except Exception as e:
            flash(f"❌ Failed on {ip}: {e}")
            log_execution(f"{datetime.datetime.now().isoformat()} | {ip} | {filename} | ERROR | {str(e)}")

    # Run in parallel for each selected machine
    with ThreadPoolExecutor(max_workers=len(selected_ips)) as executor:
        executor.map(run_for_ip, selected_ips)

    return redirect(url_for("scripts.list_scripts"))
