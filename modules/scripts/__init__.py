from flask import Blueprint

scripts_bp = Blueprint("scripts", __name__, template_folder="templates")

from .routes import scripts_bp

