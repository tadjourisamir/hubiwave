from flask import Flask, render_template
from modules.hosts.routes import hosts_bp
from modules.scheduler import scheduler_bp
from modules.scripts import scripts_bp
from modules.calendar import calendar_bp

from core.scheduler_service import start_scheduler
from core.executor import run_task
from core.utils import load_hosts
from core.file_watcher import start_file_watcher

from pathlib import Path
import os
import logging

from api.scheduled_events import scheduled_api_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def create_app():
    app = Flask(__name__)
    app.secret_key = "super-secret"

    app.register_blueprint(hosts_bp)
    app.register_blueprint(scheduler_bp)
    app.register_blueprint(scripts_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(scheduled_api_bp)

    @app.route("/")
    def index():
        from config.version import APP_VERSION
        return render_template("index.html", app_version=APP_VERSION)

    return app

if __name__ == "__main__":
    Path("modules/scheduler/data").mkdir(parents=True, exist_ok=True)
    schedule_path = "modules/scheduler/data/scheduled_events.json"
    if not os.path.exists(schedule_path):
        with open(schedule_path, "w") as f:
            f.write("[]")

    app = create_app()

    hosts = load_hosts()
    scheduler = start_scheduler(run_task, hosts)
    start_file_watcher(scheduler, run_task)

    app.run(debug=False, use_reloader=False)
