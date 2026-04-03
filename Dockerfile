FROM python:3.11-slim as base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Development stage
FROM base as development

ENV FLASK_DEBUG=1
ENV FLASK_APP=app.py

EXPOSE 5000

CMD ["python", "app.py"]

# Production stage
FROM base as production

# Create non-root user
RUN useradd -m -u 1000 flask && chown -R flask:flask /app

USER flask

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=2)" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]