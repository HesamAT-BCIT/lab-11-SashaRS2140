from __future__ import annotations

from flask import redirect, render_template, request, url_for

from utils.auth import get_current_user
from utils.profile import get_profile_data, set_profile
from utils.validation import normalize_profile_data, validate_profile_data
from utils.logging_config import get_logger

from . import profile_bp

logger = get_logger(__name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
def profile():
    """HTML form to create/update the current user's profile."""
    current_user = get_current_user()
    if not current_user:
        logger.warning("Profile access denied: user not authenticated")
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        logger.info("Profile form requested by user: %s", current_user)
        profile_data = get_profile_data(current_user)
        return render_template("profile.html", profile=profile_data, error=None)

    logger.info("Profile update attempt by user: %s", current_user)
    first_name = request.form.get("first_name", "")
    last_name = request.form.get("last_name", "")
    student_id = request.form.get("student_id", "")

    error = validate_profile_data(first_name, last_name, student_id)
    if error:
        logger.warning("Profile update failed for user: %s - %s", current_user, error)
        profile_data = {
            "first_name": first_name,
            "last_name": last_name,
            "student_id": student_id,
        }
        return render_template("profile.html", profile=profile_data, error=error)

    normalized = normalize_profile_data(first_name, last_name, student_id)
    set_profile(current_user, normalized, merge=True)
    logger.info("Profile updated successfully for user: %s", current_user)
    return redirect(url_for("dashboard.home"))
