from __future__ import annotations

import os
from functools import wraps

from flask import jsonify, request
from firebase_admin import auth

from utils.logging_config import get_logger

logger = get_logger(__name__)


def require_api_key(f):
    """Decorator to require API key authentication for device/iot endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        expected_key = os.environ.get("SENSOR_API_KEY")

        if not expected_key:
            logger.error("API key auth failed: SENSOR_API_KEY not configured on server")
            return jsonify({"error": "API key not configured on server"}), 500

        provided_key = request.headers.get("X-API-Key")

        if not provided_key:
            logger.warning("API key auth failed: missing X-API-Key header from %s", request.remote_addr)
            return jsonify({"error": "Missing X-API-Key header"}), 401

        if provided_key != expected_key:
            logger.warning("API key auth failed: invalid key from %s", request.remote_addr)
            return jsonify({"error": "Unauthorized"}), 401

        logger.info("API key auth succeeded from %s", request.remote_addr)
        return f(*args, **kwargs)

    return decorated_function


def require_jwt(f):
    """Decorator to require JWT authentication for API endpoints."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning("JWT auth failed: missing Authorization header from %s", request.remote_addr)
            return jsonify({"error": "Missing Authorization header"}), 401

        if not auth_header.startswith("Bearer "):
            logger.warning("JWT auth failed: invalid Bearer format from %s", request.remote_addr)
            return jsonify({"error": "Invalid Authorization header format"}), 401

        token = auth_header.split(" ")[1]

        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token["uid"]
            logger.info("JWT authenticated user: %s from %s", uid, request.remote_addr)
            return f(*args, uid=uid, **kwargs)
        except Exception as e:
            logger.warning("JWT auth failed: invalid token from %s - %s", request.remote_addr, str(e))
            return jsonify({"error": "Invalid or expired token"}), 401

    return decorated_function
