from flask import render_template
from . import calendar_bp
from core import scheduler_service as sched

@calendar_bp.route("/calendar")
def calendar_view():
    tasks = sched.load_tasks()
    return render_template("calendar/calendar.html", tasks=tasks)
