FROM python:3.12-slim

# Create a non-root user so the container does not run as root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy requirements first so Docker caches this layer independently of source changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create runtime directories and hand ownership to the non-root user
RUN mkdir -p logs instance && chown -R appuser:appuser /app

# FLASK_APP lets `flask db upgrade` find the application when run inside the container
ENV FLASK_APP=app

USER appuser

EXPOSE 8000

# 2 workers is appropriate for SQLite; raise only after switching to PostgreSQL
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "app:create_app()"]
