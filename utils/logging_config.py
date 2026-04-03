import json
import logging
import logging.handlers
import os
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger instance with file and console handlers.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        # Determine log level based on environment or default to INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Console handler (StreamHandler)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        json_format = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(json_format)
        
        # File handler (RotatingFileHandler)
        file_path = log_dir / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(json_format)
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger
