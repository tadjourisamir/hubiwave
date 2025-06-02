from flask import Blueprint

scheduler_bp = Blueprint("scheduler", __name__, template_folder="templates", static_folder="static")

from . import routes
