from __future__ import annotations

import requests
from flask import jsonify, redirect, render_template, request, session, url_for
from firebase_admin import auth

from config import Config
from firebase import db
from utils.logging_config import get_logger

from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Signup page for creating new user accounts."""
    if request.method == "GET":
        return render_template("signup.html")

    if request.content_type and "application/json" in request.content_type:
        return api_signup()

    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    logger.info("Signup attempt for email: %s", email)

    if password != confirm_password:
        logger.warning("Signup failed for %s: passwords do not match", email)
        return render_template("signup.html", error="Passwords do not match")

    if not email or not password:
        logger.warning("Signup failed: email and password are required")
        return render_template("signup.html", error="Email and password are required")

    try:
        user = auth.create_user(email=email, password=password)
        db.collection("profiles").document(user.uid).set({"email": email, "role": "user"})
        logger.info("User signup successful: %s (uid: %s)", email, user.uid)
        return redirect(url_for("auth.login"))
    except Exception as e:
        error_message = str(e)
        if "email-already-exists" in error_message:
            error_message = "An account with this email already exists"
            logger.warning("Signup failed for %s: email already exists", email)
        elif "invalid-email" in error_message:
            error_message = "Invalid email address"
            logger.warning("Signup failed for %s: invalid email format", email)
        elif "weak-password" in error_message:
            error_message = "Password is too weak. Please use a stronger password"
            logger.warning("Signup failed for %s: weak password", email)
        else:
            logger.error("Signup failed for %s: %s", email, str(e), exc_info=True)
        return render_template("signup.html", error=error_message)


def api_signup():
    """JSON API helper for user registration."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    logger.info("API signup attempt for email: %s", email)

    if not email or not password:
        logger.warning("API signup failed: email and password are required")
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user = auth.create_user(email=email, password=password)
        db.collection("profiles").document(user.uid).set({"email": email, "role": "user"})
        logger.info("API signup successful: %s (uid: %s)", email, user.uid)
        return jsonify({"message": "User created successfully", "uid": user.uid}), 201
    except Exception as e:
        error_message = str(e)
        if "email-already-exists" in error_message:
            logger.warning("API signup failed for %s: email already exists", email)
            return jsonify({"error": "An account with this email already exists"}), 400
        if "invalid-email" in error_message:
            logger.warning("API signup failed for %s: invalid email format", email)
            return jsonify({"error": "Invalid email address"}), 400
        if "weak-password" in error_message:
            logger.warning("API signup failed for %s: weak password", email)
            return jsonify({"error": "Password is too weak"}), 400
        logger.error("API signup failed for %s: %s", email, str(e), exc_info=True)
        return jsonify({"error": "Failed to create user"}), 400


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page. Supports both web form and JSON API login."""
    if request.method == "GET":
        return render_template("login.html")

    if request.is_json:
        return api_login()

    email = request.form.get("email")
    password = request.form.get("password")

    logger.info("Login attempt for email: %s", email)

    if not email or not password:
        logger.warning("Login failed: email and password are required")
        return render_template("login.html", error="Email and password are required")

    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={Config.WEB_API_KEY}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            token_data = res.json()
            uid = token_data.get("localId")
            session["logged_in"] = True
            session["username"] = uid
            session["email"] = email
            session["jwt_token"] = token_data.get("idToken")
            logger.info("Login successful for email: %s (uid: %s)", email, uid)
            return redirect(url_for("dashboard.home"))

        error_data = res.json().get("error", {})
        error_message = error_data.get("message", "Invalid credentials")
        if "INVALID_LOGIN_CREDENTIALS" in error_message:
            error_message = "Invalid email or password"
        logger.warning("Login failed for %s: invalid credentials", email)
        return render_template("login.html", error=error_message)
    except requests.RequestException as e:
        logger.error("Login failed for %s: authentication service unavailable - %s", email, str(e))
        return render_template("login.html", error="Authentication service unavailable")


def api_login():
    """JSON API helper for login. Returns a JWT token."""
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    logger.info("API login attempt for email: %s", email)

    if not email or not password:
        logger.warning("API login failed: email and password are required")
        return jsonify({"error": "Email and password are required"}), 400

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={Config.WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    try:
        res = requests.post(url, json=payload, timeout=10)

        if res.status_code == 200:
            logger.info("API login successful for email: %s", email)
            return jsonify({"token": res.json()["idToken"]}), 200

        logger.warning("API login failed for %s: invalid credentials", email)
        return jsonify({"error": "Invalid credentials"}), 401
    except requests.RequestException as e:
        logger.error("API login failed for %s: authentication service unavailable - %s", email, str(e))
        return jsonify({"error": "Authentication service unavailable"}), 503


@auth_bp.route("/logout")
def logout():
    """Clear the session and return to login."""
    logger.info("User logged out")
    session.clear()
    return redirect(url_for("auth.login"))
