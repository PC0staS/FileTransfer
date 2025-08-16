import os
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import request, g  # type: ignore


def setup_logging(app):
    """
    Configure logging for the Flask application.
    
    Args:
        app: Flask application instance
    
    Returns:
        bool: True if logging setup was successful, False otherwise
    """
    try:
        # Ensure logs directory exists
        logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'app.log')

        # Create file handler with rotation
        file_handler = RotatingFileHandler(
            log_path, 
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        )
        file_handler.setFormatter(formatter)

        # Attach handlers to Flask's logger
        app.logger.setLevel(logging.INFO)
        
        # Only add handler if it doesn't already exist
        if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
            app.logger.addHandler(file_handler)
        
        return True
        
    except Exception as e:
        # If logging setup fails, continue without file logging
        print(f"Warning: Could not set up file logging: {e}")
        return False


def get_logger(name):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Name for the logger
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def attach_request_logging(app):
    """Register request start/end logging handlers on the Flask app.

    Adds two hooks:
      - before_request: stores start time and logs incoming request basics.
      - after_request: computes duration and logs outcome with status code.
    """

    SENSITIVE_KEYS = ("pass", "pwd", "token", "secret", "auth")

    def _scrub(mapping):
        """Return a copy of mapping excluding sensitive keys entirely."""
        try:
            cleaned = {}
            for k, v in mapping.items():
                if any(s in k.lower() for s in SENSITIVE_KEYS):
                    continue  # omit key completely
                cleaned[k] = v
            return cleaned
        except Exception:  # pragma: no cover
            return {}

    @app.before_request  # type: ignore[misc]
    def _log_request_start():  # noqa: D401 (internal helper)
        g._start_time = time.perf_counter()  # type: ignore[attr-defined]
        try:
            params_raw = dict(request.args)
            # Evitar forzar el parse completo de multipart gigantes (ej. uploads de varios GB)
            content_length = request.content_length or 0
            is_multipart = (request.content_type or '').lower().startswith('multipart/form-data')
            # Umbral (5MB) para decidir si se omite parsing; configurable vía env LOGGING_FORM_PARSE_THRESHOLD
            threshold = int(os.environ.get('LOGGING_FORM_PARSE_THRESHOLD', 5 * 1024 * 1024))
            if is_multipart and content_length > threshold:
                form_raw = {
                    '_skipped': f'multipart ~{content_length} bytes (omitido para no bloquear subida)'
                }
            else:
                # Esto puede disparar el parse completo del multipart; sólo se hace si es pequeño
                form_raw = dict(request.form)
        except Exception:  # pragma: no cover - muy raro
            params_raw, form_raw = {}, {}
        params = _scrub(params_raw)
        form = _scrub(form_raw)
        app.logger.info(
            "Incoming request: %s %s from %s params=%s form=%s",
            request.method,
            request.path,
            request.remote_addr,
            params,
            form,
        )

    @app.after_request  # type: ignore[misc]
    def _log_request_end(response):  # noqa: D401
        try:
            start = getattr(g, "_start_time", None)
            duration_ms = (time.perf_counter() - start) * 1000.0 if start else 0.0
        except Exception:  # pragma: no cover
            duration_ms = 0.0
        app.logger.info(
            "Handled request: %s %s -> %s (%.2fms)",
            request.method,
            request.path,
            response.status,
            duration_ms,
        )
        return response

    return app
