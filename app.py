import os
import traceback
from pathlib import Path

from flask import Flask, request

from blueprints.api import api_bp
from blueprints.auth import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.profile import profile_bp
from config import Config
from utils.logging_config import get_logger
import firebase  # noqa: F401

app = Flask(__name__)
app.config.from_object(Config)

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Initialize logger
logger = get_logger(__name__)
logger.info("Flask app initialized with debug=%s", os.getenv("FLASK_DEBUG", "False"))

app.register_blueprint(dashboard_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(api_bp)


# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint for Docker health checks."""
    return {"status": "ok"}, 200


# Request/Response logging
@app.before_request
def log_request():
    """Log incoming request details."""
    logger.info("REQUEST: %s %s from %s", request.method, request.path, request.remote_addr)


@app.after_request
def log_response(response):
    """Log response status and size."""
    logger.info("RESPONSE: %s %s returned %d (size: %s bytes)", 
                request.method, request.path, response.status_code, 
                response.content_length or 0)
    return response


# Global error handlers
@app.errorhandler(404)
def handle_404(error):
    """Handle 404 Not Found errors."""
    logger.warning("404 - Path not found: %s %s", request.method, request.path)
    return {"error": "Not Found"}, 404


@app.errorhandler(403)
def handle_403(error):
    """Handle 403 Forbidden errors."""
    logger.warning("403 - Access forbidden: %s %s from %s", request.method, request.path, request.remote_addr)
    return {"error": "Forbidden"}, 403


@app.errorhandler(500)
def handle_500(error):
    """Handle 500 Internal Server errors."""
    logger.error("500 - Unhandled exception: %s %s\n%s", request.method, request.path, traceback.format_exc())
    return {"error": "Internal Server Error"}, 500


@app.errorhandler(Exception)
def handle_exception(error):
    """Catch-all error handler for unhandled exceptions."""
    logger.error("Unhandled exception: %s %s - %s\n%s", 
                 request.method, request.path, str(error), traceback.format_exc())
    return {"error": "Internal Server Error"}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)
