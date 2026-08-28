from flask import Blueprint, redirect, render_template, url_for

from ..security.auth import login_required

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    return redirect(url_for("pages.monthly"))


@bp.route("/monthly")
@login_required
def monthly():
    return render_template("pages/monthly.html", active_page="monthly")


@bp.route("/graphs")
@login_required
def graphs():
    return render_template("pages/graphs.html", active_page="graphs")


@bp.route("/manage")
@login_required
def manage():
    return render_template("pages/manage.html", active_page="manage")
