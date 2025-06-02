from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import json, os
from datetime import datetime
from core.ssh_service import ensure_ssh_key, auto_copy_key, test_ssh_connection, get_mac_address

hosts_bp = Blueprint("hosts", __name__, template_folder="templates")

HOSTS_FILE = "modules/hosts/data/hosts.json"
PENDING_FILE = "modules/hosts/data/pending_hosts.json"
DEFAULT_KEY = os.path.expanduser("~/.ssh/id_rsa")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@hosts_bp.route("/hosts")
def list_hosts():
    hosts = load_json(HOSTS_FILE)
    for host in hosts:
        host["connected"] = test_ssh_connection(
            host["ip"], host["user"], host.get("port", 22), host.get("key_path", DEFAULT_KEY)
        )
    return render_template("hosts/list.html", hosts=hosts)

@hosts_bp.route("/pending")
def pending_hosts():
    pending = load_json(PENDING_FILE)
    for host in pending:
        host["connected"] = test_ssh_connection(
            host["ip"], host["user"], host.get("port", 22), host.get("key_path", DEFAULT_KEY)
        )
    return render_template("hosts/pending.html", pending_hosts=pending)

@hosts_bp.route("/add_pending", methods=["POST"])
def add_pending_host():
    try:
        data = request.get_json()
        ip = data.get("ip")
        user = data.get("user")
        port = int(data.get("port", 22))

        ensure_ssh_key()
        auto_copy_key(ip, user, port, DEFAULT_KEY)
        mac = get_mac_address(ip, user, port, DEFAULT_KEY)

        if not mac:
            return jsonify({"status": "error", "error": "Unable to retrieve MAC address"}), 400

        new_host = {
            "id": mac,
            "ip": ip,
            "user": user,
            "port": port,
            "key_path": DEFAULT_KEY,
            "added_at": datetime.now().isoformat()
        }

        hosts = load_json(HOSTS_FILE)
        pending = load_json(PENDING_FILE)

        if any(h["id"] == mac for h in hosts + pending):
            return jsonify({"status": "exists", "ip": ip, "mac": mac})

        pending.append(new_host)
        save_json(PENDING_FILE, pending)
        return jsonify({"status": "added", "ip": ip, "mac": mac})

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@hosts_bp.route("/validate_host", methods=["POST"])
def validate_host():
    mac_id = request.form.get("id")
    pending = load_json(PENDING_FILE)
    hosts = load_json(HOSTS_FILE)

    match = next((h for h in pending if h["id"] == mac_id), None)
    if not match:
        flash("❌ Not found.")
        return redirect(url_for("hosts.pending_hosts"))

    if not any(h["id"] == mac_id for h in hosts):
        hosts.append(match)
        save_json(HOSTS_FILE, hosts)

    pending = [h for h in pending if h["id"] != mac_id]
    save_json(PENDING_FILE, pending)

    flash("✅ Machine validated.")
    return redirect(url_for("hosts.pending_hosts"))

@hosts_bp.route("/delete_host", methods=["POST"])
def delete_host():
    mac_id = request.form.get("id")
    modified = False

    for path in [HOSTS_FILE, PENDING_FILE]:
        data = load_json(path)
        new_data = [h for h in data if h["id"] != mac_id]
        if len(new_data) != len(data):
            save_json(path, new_data)
            modified = True

    flash("🗑 Deleted." if modified else "⚠️ Not found.")
    return redirect(request.referrer or url_for("hosts.list_hosts"))

@hosts_bp.route("/settings_data")
def settings_data():
    hosts = load_json(HOSTS_FILE)
    for host in hosts:
        host["connected"] = test_ssh_connection(
            host["ip"], host["user"], host.get("port", 22), host.get("key_path", DEFAULT_KEY)
        )
    return jsonify(hosts)
